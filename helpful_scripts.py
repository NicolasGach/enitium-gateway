from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import base64
from flask import Flask
from logging import DEBUG
from web3 import Web3
import os
import json
from sqlalchemy import MetaData, Table, create_engine, and_
from sqlalchemy.sql import select

app = Flask(__name__)
app.logger.setLevel(DEBUG)
w3 = Web3(Web3.HTTPProvider(os.environ['INFURA_NODE_URL']))
CONTRACT_ADDRESS = os.environ['CONTRACT_ADDRESS']
with open('EnitiumNFT.json', 'r') as f:
    json_contract = json.load(f)
CONTRACT_ABI = json_contract["abi"]
DATABASE_URL=os.environ['DATABASE_URL']
sqlengine = create_engine(DATABASE_URL.replace('postgres://', 'postgresql://', 1), logging_name='gatewayengine')
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

global wait_and_process_receipt
def wait_and_process_receipt(tx_hash, bol_id):
    enitiumcontract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)
    conn = sqlengine.connect()
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, poll_latency=0.5)
    decoded_tx_receipt = enitiumcontract.events.Transfer().processReceipt(tx_receipt)
    app.logger.info('tx_receipt : %s', tx_receipt)
    app.logger.info('tx_receipt decoded : %s', decoded_tx_receipt)
    u = enfty_tx_table.update().values(
        tx_hash__c = decoded_tx_receipt[0]['transactionHash'].hex(), 
        from_address__c = decoded_tx_receipt[0]['args']['from'], 
        to_address__c = decoded_tx_receipt[0]['args']['to'], 
        token_id__c = decoded_tx_receipt[0]['args']['tokenId']
    ).where(and_(
        enfty_tx_table.c.tx_hash__c == tx_hash.hex(), 
        enfty_tx_table.c.bill_of_lading__c == bol_id)
    )
    conn.execute(u)
    conn.close()

def sanitize_dict(dict):
    sane_form = {}
    for key in dict: sane_form[key] = dict[key].strip()
    return sane_form