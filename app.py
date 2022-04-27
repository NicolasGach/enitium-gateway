# app.py
import os
import werkzeug.exceptions as ex
import json
import re
import requests
from web3 import Web3, exceptions
from web3.gas_strategies.time_based import medium_gas_price_strategy
from eth_abi import decode_single
from pathlib import Path
from auth0 import AuthError, requires_auth, requires_scope
from flask import Flask, request, jsonify, abort
from flask_cors import cross_origin
from exceptions import AuthError, LogicError
from logging import DEBUG
from helpful_scripts import decrypt_sf_aes, sign_and_send_w3_transaction_transfer_type, sanitize_dict, process_mint, process_transfer
from decorators import requires_post_params, requires_w3_access
from classes import W3EnitiumContract
from rq import Queue
from worker import conn
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy import MetaData, Table, create_engine, and_, func
from sqlalchemy.sql import select
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone
import uuid

#contract : 0x855539e32608298cF253dC5bFb25043D19692f6a
#upgradeable : 0xdE2b51ba8888e401725Df10328EE5063fdaF1a3E

app = Flask(__name__)
app.logger.setLevel(DEBUG)
w3 = Web3(Web3.HTTPProvider(os.environ['INFURA_NODE_URL']))
w3.eth.set_gas_price_strategy(medium_gas_price_strategy)
CONTRACT_ADDRESS = os.environ['CONTRACT_ADDRESS']
with open('EnitiumNFT.json', 'r') as f:
    json_contract = json.load(f)
CONTRACT_ABI = json_contract["abi"]
OWNER_ACCOUNT = os.environ['OWNER_ACCOUNT']
OWNER_PRIVATE_KEY = os.environ['OWNER_PRIVATE_KEY']
IPFS_PROJECT_ID = os.environ['IPFS_PROJECT_ID']
IPFS_PROJECT_SECRET = os.environ['IPFS_PROJECT_SECRET']
MAX_FEE_PER_GAS = os.environ['MAX_FEE_PER_GAS_GWEI']
MAX_PRIORITY_FEE_PER_GAS = os.environ['MAX_PRIORITY_FEE_PER_GAS_GWEI']
q_high = Queue('high', connection = conn)
q_low = Queue('low', connection = conn)
DATABASE_URL=os.environ['DATABASE_URL']
sqlengine = create_engine(DATABASE_URL.replace('postgres://', 'postgresql://', 1), logging_name='gatewayengine')
metadata_obj = MetaData(schema='salesforce')
metadata_obj.reflect(bind=sqlengine)
app.logger.info('table keys : %s', metadata_obj.tables.keys())
enfty_tx_table = metadata_obj.tables['salesforce.enfty_bol_transfer_data__c']

@app.route('/')
def index():
    response = {}
    response['callresponse'] = 'ok home'
    return jsonify(response)

@app.route('/test_nonce/<testAddress>', methods=['GET'])
def test_nonce(testAddress):
    conn = sqlengine.connect()
    from_address = testAddress
    db_nonce = conn.execute(select([func.max(enfty_tx_table.c.nonce__c)]).where(enfty_tx_table.c.from_address__c == from_address)).scalar()
    app.logger.info('nonce user : %s', db_nonce)
    nonce = (int(db_nonce) + 1) if not db_nonce is None else 1
    response = {"nonce": nonce}
    return jsonify(response)

@app.route('/post_ipfs', methods=['POST'])
@requires_auth
def post_ipfs():
    if requires_scope("access:gateway"):
        if "file" in request.files:
            app.logger.info('File content %s',request.files['file'].read())
            params = {'file': request.files['file'].read()}
            response = requests.post(
                os.environ['INFURA_IPFS_URL'] + '/api/v0/add', 
                files=params,
                auth=(IPFS_PROJECT_ID, IPFS_PROJECT_SECRET)
            )
            app.logger.info('Reponse %s', response)
            return response.text
        raise LogicError({"code": "Bad Request", "description": "No file input in request"}, 400)
    raise AuthError({"code": "Unauthorized", "description": "You don't have access to this resource"}, 403)

@app.route('/mint', methods=['POST'])
@requires_auth
@requires_post_params(['recipient_address', 'token_hash', 'bol_id'])
@requires_w3_access
def mint():
    if not requires_scope("access:gateway"):
        raise AuthError({"code": "Unauthorized", "description": "You don't have access to this resource"}, 403)
    if not w3.isConnected():
        raise LogicError({"code": "Code Error", "description": "W3 not initialized"}, 500)
    sane_form = sanitize_dict(request.form)
    app.logger.info('sane_form : %s', sane_form)
    if not w3.isAddress(sane_form['recipient_address']):
        raise LogicError({"code": "Request Error", "description": "Bad request, input not a valid address"}, 400)
    if not w3.eth.get_balance(sane_form['recipient_address']):
        raise LogicError({"code": "Request Error", "description": "The sender account has no funds or does not exist"}, 400)
    ipfs_response = requests.post(
        os.environ['INFURA_IPFS_URL'] + '/api/v0/block/get', 
        params={'arg': sane_form['token_hash']},
        auth=(IPFS_PROJECT_ID, IPFS_PROJECT_SECRET)
    )
    if not ipfs_response.status_code == 200:
        raise LogicError({"code": "Request Error", "description": "Token not found on IPFS host"}, 400)
    nonce = -1
    if 'nonce' in sane_form:
        app.logger.info('Nonce forced in transaction with value : {0}'.format(nonce))
        nonce = sane_form['nonce']
    tx = {
        'from': OWNER_ACCOUNT,
        'chainId': 3,
        #'gas': 2000000,
        'maxFeePerGas': w3.toWei(MAX_FEE_PER_GAS, 'gwei'),
        'maxPriorityFeePerGas': w3.toWei(MAX_PRIORITY_FEE_PER_GAS, 'gwei'),
        'nonce': int(nonce)
    }
    tx_uuid = uuid.uuid4()
    ins = enfty_tx_table.insert().values(
        sent_from__c = OWNER_ACCOUNT,
        to_address__c = OWNER_ACCOUNT,
        gateway_id__c =  tx_uuid,
        bill_of_lading__c = sane_form['bol_id'],
        status__c = 'Processing',
        last_status_change_date__c = datetime.now(timezone.utc),
        type__c = 'Minting')
    conn = sqlengine.connect()
    result = conn.execute(ins)
    conn.close()
    q_high.enqueue(process_mint, args=(tx_uuid, tx, sane_form['recipient_address'], ipfs_response.text, sane_form['bol_id']))
    return { 'tx_uuid': tx_uuid, 'job_enqueued' : 'ok', 'postgre_id': result.inserted_primary_key[0] }

@app.route('/transfer', methods=['POST'])
@requires_auth
@requires_post_params(['from_address', 'from_pk', 'to_address', 'token_id', 'vector', 'bol_id'])
def transfer():
    if not requires_scope('access:gateway'):
        raise AuthError({"code": "Unauthorized", "description": "You don't have access to this resource"}, 403)
    if not w3.isConnected():
        raise LogicError({"code": "Code Error", "description": "W3 not initialized"}, 500)
    sane_form = sanitize_dict(request.form)
    app.logger.info('sane_form : %s', sane_form)
    from_pk = decrypt_sf_aes(sane_form['from_pk'], os.environ['AES_KEY'], sane_form['vector'])
    if not w3.isAddress(sane_form['from_address']) or not w3.isAddress(sane_form['to_address']):
        raise LogicError({"code": "Request Error", "description": "Bad request, input not a valid address"}, 400)
    app.logger.info('Before get balance ...')
    if not w3.eth.get_balance(sane_form['from_address']) > 200000:
        raise LogicError({"code": "Request Error", "description": "The sender account has no funds for transfer"}, 400)
    nonce = -1
    if 'nonce' in sane_form:
        app.logger.info('Nonce forced in transaction with value : {0}'.format(nonce))
        nonce = sane_form['nonce']
    tx = {
        'from': sane_form['from_address'],
        'chainId': 3,
        'gas': 2000000,
        'maxFeePerGas': w3.toWei(MAX_FEE_PER_GAS, 'gwei'),
        'maxPriorityFeePerGas': w3.toWei(MAX_PRIORITY_FEE_PER_GAS, 'gwei'),
        'nonce': int(nonce)
    }
    tx_uuid = uuid.uuid4()
    ins = enfty_tx_table.insert().values(
        sent_from__c = sane_form['from_address'],
        from_address__c = sane_form['from_address'],
        to_address__c = sane_form['to_address'],
        token_id__c = sane_form['token_id'],
        gateway_id__c =  tx_uuid,
        bill_of_lading__c = sane_form['bol_id'],
        status__c = 'Processing',
        last_status_change_date__c = datetime.now(timezone.utc),
        type__c = 'Transfer')
    conn = sqlengine.connect()
    result = conn.execute(ins)
    conn.close()
    q_high.enqueue(process_transfer, args=(
        tx_uuid, 
        tx, 
        sane_form['from_address'],
        from_pk,
        sane_form['to_address'], 
        sane_form['token_id'],
        sane_form['bol_id']
    ))
    return { 'tx_uuid': tx_uuid, 'job_enqueued' : 'ok', 'postgre_id': result.inserted_primary_key[0] }

@app.route('/burn', methods=['POST'])
@requires_auth
@requires_post_params(['token_id', 'from_address', 'from_pk', 'vector'])
def burn():
    if not requires_scope('access:gateway'):
        raise AuthError({"code": "Unauthorized", "description": "You don't have access to this resource"}, 403)
    if not w3.isConnected():
        raise LogicError({"code": "Code Error", "description": "W3 not initialized"}, 500)
    sane_form = sanitize_dict(request.form)
    app.logger.info('sane_form : %s', sane_form)
    from_pk = decrypt_sf_aes(sane_form['from_pk'], os.environ['AES_KEY'], sane_form['vector'])
    if w3.isAddress(sane_form['from_address']):
        app.logger.info('Before get balance ...')
        if w3.eth.get_balance(sane_form['from_address']) > 200000:
            enitiumcontract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)
            try:
                enitiumcontract.functions.tokenURI(int(sane_form['token_id'])).call()
            except exceptions.ContractLogicError as e:
                app.logger.info('exception : {0}'.format(e))
                raise LogicError({"code": "Blockchain Error", "description": "Smart contract returned exception, possibly trying to burn a non-existing token : {0}".format(e)}, 500)
            nonce = w3.eth.get_transaction_count(sane_form['from_address'])
            app.logger.info('before sending transaction')
            enfty_tx = enitiumcontract.functions.burn(int(sane_form['token_id'])
            ).buildTransaction({
                'from': sane_form['from_address'],
                'chainId': 3,
                'gas': 200000,
                'maxFeePerGas': w3.toWei('2', 'gwei'),
                'maxPriorityFeePerGas': w3.toWei('1', 'gwei'),
                'nonce': nonce
            })
            response = sign_and_send_w3_transaction_transfer_type(w3, enitiumcontract, enfty_tx, from_pk)
            return response
        raise LogicError({"code": "Request Error", "description": "The sender account has no funds for transfer"}, 400)
    raise LogicError({"code": "Request Error", "description": "Bad request, input not a valid address"}, 400)

@app.route('/tokenURI/<tokenId>', methods=['GET'])
@requires_auth
def getTokenURI(tokenId):
    if not requires_scope('access:gateway'):
        raise AuthError({"code": "Unauthorized", "description": "You don't have access to this resource"}, 403)
    if not w3.isConnected():
        raise LogicError({"code": "Code Error", "description": "W3 not initialized"}, 500)
    try:
        enitiumcontract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)
        tokenURI = enitiumcontract.functions.tokenURI(int(tokenId)).call()
        m = re.search(r'{.+}', tokenURI)
        app.logger.info('tokenURI : {0}'.format(tokenURI))
        app.logger.info('m : {0}'.format(m.group(0)))
        return m.group(0)
    except exceptions.ContractLogicError as e:
        app.logger.info('exception : {0}'.format(e))
        raise LogicError({"code": "Blockchain Error", "description": "Smart contract returned exception: {0}".format(e)}, 500)

@app.route('/receipt')
@requires_auth
@requires_post_params(['tx_hash'])
def getReceipt():
    pass

@app.route('/decrypt_test', methods=['POST'])
@requires_auth
def decrypt_test():
    key = os.environ['AES_KEY']
    return decrypt_sf_aes(request.form['content'], key, request.form['vector'])

@app.errorhandler(500)
def internal_error(e):
    return '<p>Internal Error occurred'

@app.errorhandler(LogicError)
def handle_logic_error(ex):
    response = jsonify(ex.error)
    response.status_code = ex.status_code
    return response

@app.errorhandler(AuthError)
def handle_auth_error(ex):
    response = jsonify(ex.error)
    response.status_code = ex.status_code
    return response

if __name__ == '__main__':
    # Threaded option to enable multiple instances for multiple user access support
    app.run(threaded=True, debug=True, port=5000)