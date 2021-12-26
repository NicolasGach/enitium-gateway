from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import base64
from flask import Flask
from logging import DEBUG
from web3 import Web3
import os

app = Flask(__name__)
app.logger.setLevel(DEBUG)
w3 = Web3(Web3.HTTPProvider(os.environ['INFURA_NODE_URL']))
CONTRACT_ADDRESS = os.environ['CONTRACT_ADDRESS']
with open('EnitiumNFT.json', 'r') as f:
    json_contract = json.load(f)
CONTRACT_ABI = json_contract["abi"]

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
def wait_and_process_receipt(tx_hash):
    enitiumcontract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, poll_latency=0.5)
    decoded_tx_receipt = enitiumcontract.events.Transfer().processReceipt(tx_receipt)
    app.logger.info('tx_receipt : %s', tx_receipt)
    app.logger.info('tx_receipt decoded : %s', decoded_tx_receipt)
    response = {
        'tx_hash' : decoded_tx_receipt[0]['transactionHash'].hex(), 
        'tx_from' : decoded_tx_receipt[0]['args']['from'], 
        'tx_recipient' : decoded_tx_receipt[0]['args']['to'], 
        'tx_token_id': decoded_tx_receipt[0]['args']['tokenId']
    }
    return response


def sanitize_dict(dict):
    sane_form = {}
    for key in dict: sane_form[key] = dict[key].strip()
    return sane_form