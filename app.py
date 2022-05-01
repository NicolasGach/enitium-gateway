# app.py
import g
import requests
import werkzeug.exceptions as ex
from auth0 import AuthError, requires_auth, requires_scope
from decorators import requires_post_params
from exceptions import AuthError, LogicError
from flask import Flask, request, jsonify
from worker_scripts import process_mint, process_transfer
from logging import DEBUG
from rq import Queue
from crypto import Crypto
from txmanager import TxDbManager
from enftycontract import EnftyContract
from worker import conn

#contract : 0x855539e32608298cF253dC5bFb25043D19692f6a
#upgradeable : 0xdE2b51ba8888e401725Df10328EE5063fdaF1a3E

app = Flask(__name__)
app.logger.setLevel(DEBUG)

q_high = Queue('high', connection = conn)
q_low = Queue('low', connection = conn)

"""Main module for the Enitium Gateway app

:raises LogicError: _description_
:raises AuthError: _description_
:raises AuthError: _description_
:raises LogicError: _description_
:raises LogicError: _description_
:raises LogicError: _description_
:raises LogicError: _description_
:raises AuthError: _description_
:raises LogicError: _description_
:raises LogicError: _description_
:raises LogicError: _description_
:raises AuthError: _description_
:raises LogicError: _description_
:raises LogicError: _description_
:raises LogicError: _description_
:raises LogicError: _description_
:raises AuthError: _description_
:raises LogicError: _description_
:raises LogicError: _description_
:return: _description_
:rtype: _type_
"""

@app.route('/')
def index():
    response = {}
    response['callresponse'] = 'ok home'
    return jsonify(response)

@app.route('/test_nonce/<testAddress>', methods=['GET'])
def test_nonce(testAddress):
    tx_db_manager = TxDbManager.get_tx_db_manager(g.DATABASE_URL, 'gatewayengine')
    db_nonce = tx_db_manager.get_highest_nonce(testAddress)
    response = {"nonce": db_nonce}
    return jsonify(response)

@app.route('/post_ipfs', methods=['POST'])
@requires_auth
def post_ipfs():
    if not requires_scope("access:gateway"): raise AuthError({"code": "Unauthorized", "description": "You don't have access to this resource"}, 403)
    if not "file" in request.files: raise LogicError({"code": "Bad Request", "description": "No file input in request"}, 400)
    app.logger.debug('File content %s',request.files['file'].read())
    params = {'file': request.files['file'].read()}
    response = requests.post(g.INFURA_IPFS_URL + '/api/v0/add', files=params, auth=(g.IPFS_PROJECT_ID, g.IPFS_PROJECT_SECRET))
    app.logger.debug('Response %s', response)
    return response.text

@app.route('/mint', methods=['POST'])
@requires_auth
@requires_post_params(['recipient_address', 'token_hash', 'bol_id'])
def mint():
    if not requires_scope("access:gateway"): raise AuthError({"code": "Unauthorized", "description": "You don't have access to this resource"}, 403)
    
    sane_form = sanitize_dict(request.form)
    app.logger.debug('sane_form : %s', sane_form)
    
    EnftyContract.check_addresses(sane_form['recipient_address'])
    EnftyContract.check_minimum_balances(g.OWNER_ACCOUNT)
    
    ipfs_response = requests.post(g.INFURA_IPFS_URL + '/api/v0/block/get', params={'arg': sane_form['token_hash']}, auth=(g.IPFS_PROJECT_ID, g.IPFS_PROJECT_SECRET))
    if not ipfs_response.status_code == 200: raise LogicError({"code": "Request Error", "description": "Token not found on IPFS host"}, 400)

    tx_db_manager = TxDbManager.get_tx_db_manager(g.DATABASE_URL, 'gatewayengine')
    tx_db = tx_db_manager.create_tx_in_db(
        sent_from=g.OWNER_ACCOUNT, 
        to_address=g.OWNER_ACCOUNT,
        bill_of_lading_id=sane_form['bol_id'],
        tx_type='Minting')
    
    nonce = -1
    if 'nonce' in sane_form and int(sane_form['nonce'])>=0:
        app.logger.debug('Nonce forced in transaction with value : {0}'.format(nonce))
        nonce = sane_form['nonce']
    q_high.enqueue(process_mint, args=(tx_db['uuid'], sane_form['recipient_address'], ipfs_response.text, nonce))

    return { 'tx_uuid': tx_db['uuid'], 'job_enqueued' : 'ok', 'postgre_id': tx_db['id']}

@app.route('/transfer', methods=['POST'])
@requires_auth
@requires_post_params(['from_address', 'from_pk', 'to_address', 'token_id', 'vector', 'bol_id'])
def transfer():
    if not requires_scope('access:gateway'): raise AuthError({"code": "Unauthorized", "description": "You don't have access to this resource"}, 403)
    
    sane_form = sanitize_dict(request.form)
    app.logger.debug('sane_form : %s', sane_form)
    from_pk = Crypto.get_crypto().decrypt_sf_aes(sane_form['from_pk'], g.AES_KEY, sane_form['vector'])
    
    EnftyContract.check_addresses(sane_form['from_address'], sane_form['to_address'])
    EnftyContract.check_minimum_balances(sane_form['from_address'])
    
    tx_db_manager = TxDbManager.get_tx_db_manager(g.DATABASE_URL, 'gatewayengine')
    tx_db = tx_db_manager.create_tx_in_db(
        sent_from=sane_form['from_address'], 
        to_address=sane_form['to_address'],
        bill_of_lading_id=sane_form['bol_id'],
        tx_type='Transfer',
        from_address=sane_form['from_address'],
        token_id=sane_form['token_id'])
    nonce = -1
    if 'nonce' in sane_form and int(sane_form['nonce']) >=0:
        app.logger.debug('Nonce forced in transaction with value : {0}'.format(nonce))
        nonce = sane_form['nonce']
    q_high.enqueue(process_transfer, args=(tx_db['uuid'], sane_form['from_address'], from_pk, sane_form['to_address'], sane_form['token_id'], nonce))
    return { 'tx_uuid': tx_db['uuid'], 'job_enqueued' : 'ok', 'postgre_id': tx_db['id'] }

@app.route('/burn', methods=['POST'])
@requires_auth
@requires_post_params(['token_id', 'from_address', 'from_pk', 'vector'])
def burn():
    # if not requires_scope('access:gateway'):
    #     raise AuthError({"code": "Unauthorized", "description": "You don't have access to this resource"}, 403)
    # if not w3.isConnected():
    #     raise LogicError({"code": "Code Error", "description": "W3 not initialized"}, 500)
    # sane_form = sanitize_dict(request.form)
    # app.logger.debug('sane_form : %s', sane_form)
    # from_pk = Crypto.get_crypto().decrypt_sf_aes(sane_form['from_pk'], g.AES_KEY, sane_form['vector'])
    # if w3.isAddress(sane_form['from_address']):
    #     app.logger.debug('Before get balance ...')
    #     if w3.eth.get_balance(sane_form['from_address']) > 200000:
    #         enitiumcontract = w3.eth.contract(address=g.CONTRACT_ADDRESS, abi=g.CONTRACT_ABI)
    #         try:
    #             enitiumcontract.functions.tokenURI(int(sane_form['token_id'])).call()
    #         except exceptions.ContractLogicError as e:
    #             app.logger.debug('exception : {0}'.format(e))
    #             raise LogicError({"code": "Blockchain Error", "description": "Smart contract returned exception, possibly trying to burn a non-existing token : {0}".format(e)}, 500)
    #         nonce = w3.eth.get_transaction_count(sane_form['from_address'])
    #         app.logger.debug('before sending transaction')
    #         enfty_tx = enitiumcontract.functions.burn(int(sane_form['token_id'])
    #         ).buildTransaction({
    #             'from': sane_form['from_address'],
    #             'chainId': 3,
    #             'gas': 200000,
    #             'maxFeePerGas': w3.toWei('2', 'gwei'),
    #             'maxPriorityFeePerGas': w3.toWei('1', 'gwei'),
    #             'nonce': nonce
    #         })
    #         #response = sign_and_send_w3_transaction_transfer_type(w3, enitiumcontract, enfty_tx, from_pk)
    #         #return response
            return ''
    #     raise LogicError({"code": "Request Error", "description": "The sender account has no funds for transfer"}, 400)
    # raise LogicError({"code": "Request Error", "description": "Bad request, input not a valid address"}, 400)

@app.route('/tokenURI/<tokenId>', methods=['GET'])
@requires_auth
def getTokenURI(tokenId):
    if not requires_scope('access:gateway'): raise AuthError({"code": "Unauthorized", "description": "You don't have access to this resource"}, 403)
    contract = EnftyContract.get_enfty_contract()
    token_uri = contract.get_token_uri(tokenId)
    return token_uri

@app.route('/receipt')
@requires_auth
@requires_post_params(['tx_hash'])
def getReceipt():
    pass

@app.route('/decrypt_test', methods=['POST'])
@requires_auth
def decrypt_test():
    key = g.AES_KEY
    return Crypto.get_crypto().decrypt_sf_aes(request.form['content'], key, request.form['vector'])

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

def sanitize_dict(dict):
    sane_form = {}
    for key in dict: sane_form[key] = dict[key].strip()
    return sane_form

if __name__ == '__main__':
    # Threaded option to enable multiple instances for multiple user access support
    app.run(threaded=True, debug=True, port=5000)