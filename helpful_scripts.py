import base64
import json
import logging
import os
from txmanager import TxDbManager
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from datetime import datetime, timezone
from enftycontract import EnftyContract
from exceptions import LogicError
from flask import Flask, jsonify
from logging import DEBUG
from sqlalchemy import MetaData, Table, create_engine, and_, func
from sqlalchemy.sql import select
from sqlalchemy.orm import sessionmaker
from web3 import Web3, exceptions

app = Flask(__name__)
app.logger.setLevel(DEBUG)
logging.basicConfig(format = '%(asctime)s %(message)s', handlers=[logging.StreamHandler()])
log = logging.getLogger('EnftyContract')
PYTHON_LOG_LEVEL = os.environ.get('PYTHON_LOG_LEVEL', 'INFO')
log.setLevel(logging.DEBUG)

CONTRACT_ADDRESS = os.environ.get('CONTRACT_ADDRESS', '')
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgres://urifrxjjebgkrj:e007f6cad0a82178bd8cc058e25ea4e318c36f93a7401ebb83506061773c2054@ec2-52-215-22-82.eu-west-1.compute.amazonaws.com:5432/d921f851m84mkn')
FORCE_GAS_MULTIPLIER = int(os.environ.get('FORCE_GAS_MULTIPLIER', '0'))
INFURA_NODE_URL = os.environ.get('INFURA_NODE_URL', '')
OWNER_ACCOUNT = os.environ.get('OWNER_ACCOUNT', '')
OWNER_PRIVATE_KEY = os.environ.get('OWNER_PRIVATE_KEY', '')

w3 = Web3(Web3.HTTPProvider(INFURA_NODE_URL))
try:
    if os.path.isfile('EnitiumNFT.json'):
        with open('EnitiumNFT.json', 'r') as f:
            json_contract = json.load(f)
            CONTRACT_ABI = json_contract["abi"]
    else:
        json_contract = {'abi': ''}
        raise LogicError({"code": "server error", "message": "contract abi not found"}, 500)
except LogicError as le:
    pass
try:
    sqlengine = create_engine(DATABASE_URL.replace('postgres://', 'postgresql://', 1), logging_name='gatewayengine')
    Session = sessionmaker(sqlengine)
    metadata_obj = MetaData(schema='salesforce')
    metadata_obj.reflect(bind=sqlengine)
    app.logger.info('table keys : %s', metadata_obj.tables.keys())
    enfty_tx_table = metadata_obj.tables['salesforce.enfty_bol_transfer_data__c']
except (TypeError, NameError):
    Session = sessionmaker()
    metadata_obj = MetaData()
    enfty_tx_table = metadata_obj.tables['salesforce.enfty_bol_transfer_data__c']
    pass

def decrypt_sf_aes(content, key, vector):
    app.logger.info('vector : %s | content : %s', vector, content)
    bvector = vector.encode('utf-8')
    bkey = base64.b64decode(key)
    app.logger.info('decoded vector : %s | decoded key : %s', bvector, bkey)
    cipher = AES.new(bkey, AES.MODE_CBC, bvector)
    app.logger.info('after cipher')
    bcontent = base64.b64decode(content)
    result = unpad(cipher.decrypt(bcontent), AES.block_size)
    result_text = result.decode('utf-8')
    return result_text.strip()

global process_mint
def process_mint(tx_uuid, recipient_address, token_uri, nonce=-1):
    tx_db_manager = TxDbManager.get_tx_db_manager(DATABASE_URL, 'gatewayengine')
    try:
        contract = EnftyContract.get_enfty_contract()
        if nonce != -1 and nonce >= 0:
            tx_result = contract.mint(recipient_address, token_uri, nonce)
        else :
            tx_result = contract.mint(recipient_address, token_uri)
        log.debug('tx sent with hash : %s and nonce : %s', tx_result['tx_hash'].hex(), tx_result['tx']['nonce'])
        tx_db_manager.update_tx_as_sent(tx_uuid, tx_result['tx_hash'], tx_result['tx'])
        log.debug('Waiting for receipt')
        tx_receipt = contract.wait_for_tx_receipt(tx_result['tx_hash'])
        tx_db_manager.update_tx_with_receipt(tx_uuid, tx_receipt)
    except ValueError as ve:
        log.error('ValueError thrown with value : {0}'.format(ve))
        if not isinstance(ve.args[0], str):
            tx_db_manager.update_tx_as_failed(tx_uuid, str(ve.args[0]['code']), str(ve.args[0]['message']))
        else:
            tx_db_manager.update_tx_as_failed(tx_uuid, "0", str(ve.args[0]))
    except exceptions.TimeExhausted as te:
        log.error('TimeExhausted error thrown with value : {0}'.format(te))
        tx_db_manager.update_tx_as_failed(tx_uuid, "0", str(te.args[0]))

global process_transfer
def process_transfer(tx_uuid, from_address, from_pk, recipient_address, token_id, nonce=-1):
    tx_db_manager = TxDbManager.get_tx_db_manager(DATABASE_URL, 'gatewayengine')
    try:
        contract = EnftyContract.get_enfty_contract()
        if nonce != -1 and nonce >= 0:
            tx_result = contract.transfer(from_address, from_pk, recipient_address, int(token_id), nonce)
        else:
            tx_result = contract.transfer(from_address, from_pk, recipient_address, int(token_id))
        log.debug('tx sent with hash : %s and nonce : %s', tx_result['tx_hash'].hex(), tx_result['tx']['nonce'])
        tx_db_manager.update_tx_as_sent(tx_uuid, tx_result['tx_hash'], tx_result['tx'])
        log.debug('Waiting for receipt')
        tx_receipt = contract.wait_for_tx_receipt(tx_result['tx_hash'])
        tx_db_manager.update_tx_with_receipt(tx_uuid, tx_receipt)
    except ValueError as ve:
        log.error('ValueError thrown with value : {0}'.format(ve))
        if not isinstance(ve.args[0], str):
            tx_db_manager.update_tx_as_failed(tx_uuid, str(ve.args[0]['code']), str(ve.args[0]['message']))
        else:
            tx_db_manager.update_tx_as_failed(tx_uuid, "0", str(ve.args[0]))
    except exceptions.TimeExhausted as te:
        log.error('TimeExhausted error thrown with value : {0}'.format(te))
        tx_db_manager.update_tx_as_failed(tx_uuid, "0", str(te.args[0]))

def sanitize_dict(dict):
    sane_form = {}
    for key in dict: sane_form[key] = dict[key].strip()
    return sane_form

def get_db_nonce(conn, tx_table, from_address):
    db_nonce = conn.execute(
        select(
            [func.max(tx_table.c.nonce__c)]
        ).where(
            and_(
                tx_table.c.sent_from__c == from_address,
                tx_table.c.status__c == 'Cleared'
            )
        )
    ).scalar()
    return db_nonce

def get_db_highest_failed_nonce(conn, tx_table, from_address):
    db_highest_failed = conn.execute(
        select(
            [func.max(tx_table.c.nonce__c)]
        ).where(
            and_(
                tx_table.c.sent_from__c == from_address,
                tx_table.c.status__c == 'Failed'
            )
        )
    ).scalar()
    return db_highest_failed

'''db_nonce = get_db_nonce(conn, enfty_tx_table, OWNER_ACCOUNT)
db_highest_failed_nonce = get_db_highest_failed_nonce(conn, enfty_tx_table, OWNER_ACCOUNT)
app.logger.info('nonce user : {0}, highest failed nonce user : {1}'.format(db_nonce, db_highest_failed_nonce))
computed_nonce = (int(db_nonce) + 1) if not db_nonce is None else 1
tx['nonce'] = computed_nonce
if computed_nonce < pending_txs: 
tx['nonce'] = pending_txs + 1
if db_highest_failed_nonce == pending_txs:
tx['nonce'] = db_highest_failed_nonce'''
#tx['gas'] = tx['gas'] * FORCE_GAS_MULTIPLIER
#if tx['gas'] > latest_block.gasLimit: tx['gas'] = latest_block.gasLimit
#else:
#tx['gas'] = tx['gas'] * FORCE_GAS_MULTIPLIER
#if tx['gas'] > latest_block.gasLimit: tx['gas'] = latest_block.gasLimit