from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import base64
import os
import json
from flask import Flask, jsonify
from logging import DEBUG
from web3 import Web3, exceptions
from sqlalchemy import MetaData, Table, create_engine, and_, func
from sqlalchemy.sql import select
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone

app = Flask(__name__)
app.logger.setLevel(DEBUG)
w3 = Web3(Web3.HTTPProvider(os.environ['INFURA_NODE_URL']))
CONTRACT_ADDRESS = os.environ['CONTRACT_ADDRESS']
with open('EnitiumNFT.json', 'r') as f:
    json_contract = json.load(f)
CONTRACT_ABI = json_contract["abi"]
DATABASE_URL=os.environ['DATABASE_URL']
OWNER_ACCOUNT = os.environ['OWNER_ACCOUNT']
OWNER_PRIVATE_KEY = os.environ['OWNER_PRIVATE_KEY']
FORCE_GAS_MULTIPLIER = int(os.environ['FORCE_GAS_MULTIPLIER'])
sqlengine = create_engine(DATABASE_URL.replace('postgres://', 'postgresql://', 1), logging_name='gatewayengine')
Session = sessionmaker(sqlengine)
metadata_obj = MetaData(schema='salesforce')
metadata_obj.reflect(bind=sqlengine)
app.logger.info('table keys : %s', metadata_obj.tables.keys())
enfty_tx_table = metadata_obj.tables['salesforce.enfty_bol_transfer_data__c']

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

def sign_and_send_w3_transaction_transfer_type(w3, contract, builtTransaction, signer):
    signed_transaction = w3.eth.account.sign_transaction(builtTransaction, signer)
    tx_hash = w3.eth.send_raw_transaction(signed_transaction.rawTransaction)
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, poll_latency=0.5)
    decoded_tx_receipt = contract.events.Transfer().processReceipt(tx_receipt)
    app.logger.info('tx_receipt : %s', tx_receipt)
    app.logger.info('tx_receipt decoded : %s', decoded_tx_receipt)
    response = {
        'tx_hash' : decoded_tx_receipt[0]['transactionHash'].hex(), 
        'tx_from' : decoded_tx_receipt[0]['args']['from'], 
        'tx_recipient' : decoded_tx_receipt[0]['args']['to'], 
        'tx_token_id': decoded_tx_receipt[0]['args']['tokenId']
    }
    return response

global process_mint
def process_mint(tx_uuid, tx, recipient_address, token_uri, bol_id):
    conn = sqlengine.connect()
    enitiumcontract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)
    latest_block = w3.eth.get_block('latest')
    committed_txs = w3.eth.get_transaction_count(OWNER_ACCOUNT)
    pending_txs = w3.eth.get_transaction_count(OWNER_ACCOUNT, 'pending')
    app.logger.info('transaction count confirmed : {0}, transaction count with pending : {1}'.format(committed_txs, pending_txs))
    if tx['nonce'] == -1:
        db_nonce = get_db_nonce(conn, enfty_tx_table, OWNER_ACCOUNT)
        db_highest_failed_nonce = get_db_highest_failed_nonce(conn, enfty_tx_table, OWNER_ACCOUNT)
        app.logger.info('nonce user : {0}, highest failed nonce user : {1}'.format(db_nonce, db_highest_failed_nonce))
        computed_nonce = (int(db_nonce) + 1) if not db_nonce is None else 1
        tx['nonce'] = computed_nonce
        if computed_nonce < pending_txs: 
            tx['nonce'] = pending_txs + 1
        if db_highest_failed_nonce == pending_txs:
            tx['nonce'] = db_highest_failed_nonce
            tx['gas'] = tx['gas'] * FORCE_GAS_MULTIPLIER
        if tx['gas'] > latest_block.gasLimit: tx['gas'] = latest_block.gasLimit - 1
    else:
        tx['gas'] = tx['gas'] * FORCE_GAS_MULTIPLIER
        if tx['gas'] > latest_block.gasLimit: tx['gas'] = latest_block.gasLimit - 1
    enfty_tx = enitiumcontract.functions.mintNFT(recipient_address, token_uri).buildTransaction(tx)
    signed_transaction = w3.eth.account.sign_transaction(enfty_tx, OWNER_PRIVATE_KEY)
    try:
        app.logger.info('about to send transaction with gas : {0}'.format(tx['gas']))
        tx_hash = w3.eth.send_raw_transaction(signed_transaction.rawTransaction)
        app.logger.info('tx sent with hash : %s and nonce : %s', tx_hash.hex(), tx['nonce'])
        u = enfty_tx_table.update().values(
            status__c = 'Sent',
            last_status_change_date__c = datetime.now(timezone.utc),
            tx_hash__c = tx_hash.hex(),
            nonce__c = tx['nonce']
        ).where(and_(
            enfty_tx_table.c.gateway_id__c == str(tx_uuid), 
            enfty_tx_table.c.bill_of_lading__c == bol_id)
        )
        conn.execute(u)
        app.logger.info('Waiting for receipt')
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, poll_latency=0.5)
        decoded_tx_receipt = enitiumcontract.events.Transfer().processReceipt(tx_receipt)
        app.logger.info('tx_receipt : %s', tx_receipt)
        app.logger.info('tx_receipt decoded : %s', decoded_tx_receipt)
        u = enfty_tx_table.update().values(
            tx_hash__c = decoded_tx_receipt[0]['transactionHash'].hex(),
            from_address__c = decoded_tx_receipt[0]['args']['from'], 
            to_address__c = decoded_tx_receipt[0]['args']['to'], 
            token_id__c = decoded_tx_receipt[0]['args']['tokenId'],
            status__c = 'Cleared',
            last_status_change_date__c = datetime.now(timezone.utc),
        ).where(and_(
            enfty_tx_table.c.tx_hash__c == tx_hash.hex(), 
            enfty_tx_table.c.bill_of_lading__c == bol_id)
        )
        conn.execute(u)
        conn.close()
    except ValueError as ve:
        app.logger.info('ValueError thrown with value : {0}'.format(ve))
        u = enfty_tx_table.update().values(
            status__c = 'Failed',
            last_status_change_date__c = datetime.now(timezone.utc),
            error_code__c = str(ve.args[0]['code']),
            error_message__c = str(ve.args[0]['message'])
        ).where(
           enfty_tx_table.c.gateway_id__c == str(tx_uuid)
        )
        conn.execute(u)
        conn.close()
    except exceptions.TimeExhausted as te:
        app.logger.info('TimeExhausted error thrown with value : {0}'.format(te))
        u = enfty_tx_table.update().values(
            status__c = 'Failed',
            last_status_change_date__c = datetime.now(timezone.utc),
            error_code__c = "0",
            error_message__c = str(te.args[0])
        ).where(
            enfty_tx_table.c.gateway_id__c == str(tx_uuid)
        )
        conn.execute(u)
        conn.close()

global process_transfer
def process_transfer(tx_uuid, tx, from_address, from_pk, recipient_address, token_id, bol_id):
    conn = sqlengine.connect()
    enitiumcontract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)
    latest_block = w3.eth.get_block('latest')
    committed_transactions = w3.eth.get_transaction_count(from_address)
    pending_transactions = w3.eth.get_transaction_count(from_address, 'pending')
    app.logger.info('transaction count confirmed : {0}, transaction count with pending : {1}'.format(committed_transactions, pending_transactions))
    if tx['nonce'] == -1:
        db_nonce = get_db_nonce(conn, enfty_tx_table, OWNER_ACCOUNT)
        db_highest_failed_nonce = get_db_highest_failed_nonce(conn, enfty_tx_table, OWNER_ACCOUNT)
        app.logger.info('nonce user in db: {0}, highest failed nonce user : {1}'.format(db_nonce, db_highest_failed_nonce))
        computed_nonce = (int(db_nonce) + 1) if not db_nonce is None else 1
        tx['nonce'] = computed_nonce
        if computed_nonce < pending_transactions: 
            tx['nonce'] = pending_transactions + 1
        if db_highest_failed_nonce == pending_transactions:
            tx['nonce'] = db_highest_failed_nonce
            tx['gas'] = tx['gas'] * FORCE_GAS_MULTIPLIER
            if tx['gas'] > latest_block.gasLimit: tx['gas'] = latest_block.gasLimit - 1
    else:
        tx['gas'] = tx['gas'] * FORCE_GAS_MULTIPLIER
        if tx['gas'] > latest_block.gasLimit: tx['gas'] = latest_block.gasLimit - 1
    enfty_tx = enitiumcontract.functions.transferFrom(
        from_address,
        recipient_address,
        int(token_id)
    ).buildTransaction(tx)
    signed_transaction = w3.eth.account.sign_transaction(enfty_tx, from_pk)
    try:
        tx_hash = w3.eth.send_raw_transaction(signed_transaction.rawTransaction)
        app.logger.info('tx transfer sent with has : %s', tx_hash.hex())
        u = enfty_tx_table.update().values(
            status__c = 'Sent',
            last_status_change_date__c = datetime.now(timezone.utc),
            tx_hash__c = tx_hash.hex(),
            nonce__c = tx['nonce']
        ).where(and_(
            enfty_tx_table.c.gateway_id__c == str(tx_uuid),
            enfty_tx_table.c.bill_of_lading__c == bol_id)
        )
        conn.execute(u)
        app.logger.info('Waiting for receipt')
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, poll_latency=0.5)
        decoded_tx_receipt = enitiumcontract.events.Transfer().processReceipt(tx_receipt)
        app.logger.info('tx_receipt : %s', tx_receipt)
        app.logger.info('tx_deceipt decoded : %s', decoded_tx_receipt)
        u = enfty_tx_table.update().values(
            tx_hash__c = decoded_tx_receipt[0]['transactionHash'].hex(),
            from_address__c = decoded_tx_receipt[0]['args']['from'],
            to_address__c = decoded_tx_receipt[0]['args']['to'],
            token_id__c = decoded_tx_receipt[0]['args']['tokenId'],
            status__c = 'Cleared',
            last_status_change_date__c = datetime.now(timezone.utc)
        ).where(and_(
            enfty_tx_table.c.tx_hash__c == tx_hash.hex(),
            enfty_tx_table.c.bill_of_lading__c == bol_id
        ))
        conn.execute(u)
        conn.close()
    except ValueError as ve:
        app.logger.info('ValueError thrown with value : {0}'.format(ve))
        u = enfty_tx_table.update().values(
            status__c = 'Failed',
            last_status_change_date__c = datetime.now(),
            error_code__c = str(ve.args[0]['code']),
            error_message__c = str(ve.args[0]['message'])
        ).where(
           enfty_tx_table.c.gateway_id__c == str(tx_uuid)
        )
        conn.execute(u)
        conn.close()
    except exceptions.TimeExhausted as te:
        app.logger.info('TimeExhausted error thrown with value : {0}'.format(te))
        u = enfty_tx_table.update().values(
            status__c = 'Failed',
            last_status_change_date__c = datetime.now(timezone.utc),
            error_code__c = "0",
            error_message__c = str(te.args[0])
        ).where(
            enfty_tx_table.c.gateway_id__c == str(tx_uuid)
        )
        conn.execute(u)
        conn.close()

def sanitize_dict(dict):
    sane_form = {}
    for key in dict: sane_form[key] = dict[key].strip()
    return sane_form

def get_db_nonce(conn, tx_table, from_address):
    db_nonce = conn.execute(
        select(
            [func.max(tx_table.c.nonce__c)]
        ).where(
            tx_table.c.sent_from__c == from_address
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