# app.py
import os
import werkzeug.exceptions as ex
import json
import requests
from web3 import Web3
from pathlib import Path
from auth0 import AuthError, requires_auth, requires_scope
from functools import wraps
from flask import Flask, request, jsonify, abort
from flask_cors import cross_origin
from exceptions import AuthError, LogicError
from logging import DEBUG

#contract : 0x855539e32608298cF253dC5bFb25043D19692f6a

app = Flask(__name__)
app.logger.setLevel(DEBUG)
w3 = Web3(Web3.HTTPProvider(os.environ['INFURA_NODE_URL']))
CONTRACT_ADDRESS = os.environ['CONTRACT_ADDRESS']
with open('EnitiumNFT.json', 'r') as f:
    json_contract = json.load(f)
CONTRACT_ABI = json_contract["abi"]
OWNER_ACCOUNT = os.environ['OWNER_ACCOUNT']
OWNER_PRIVATE_KEY = os.environ['OWNER_PRIVATE_KEY']
IPFS_PROJECT_ID = os.environ['IPFS_PROJECT_ID']
IPFS_PROJECT_SECRET = os.environ['IPFS_PROJECT_SECRET']

@app.route('/')
def index():
    response = {}
    response['callresponse'] = 'ok home'
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
def mint():
    if requires_scope("access:gateway"):
        if w3.isConnected():
            if "recipient_address" in request.form and "token_hash" in request.form:
                app.logger.info('recipient_adress : %s', request.form['recipient_address']);
                app.logger.info('token_hash : %s', request.form['token_hash']);
                if w3.isAddress(request.form['recipient_address']):
                    recipient_address = request.form['recipient_address']
                    token_hash = request.form['token_hash']
                    if w3.eth.get_balance(recipient_address):
                        params = {'arg': token_hash}
                        ipfs_response = requests.post(
                            os.environ['INFURA_IPFS_URL'] + '/api/v0/block/get', 
                            params=params,
                            auth=(IPFS_PROJECT_ID, IPFS_PROJECT_SECRET)
                        )
                        if ipfs_response.status_code == 200:
                            enitiumcontract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)
                            nonce = w3.eth.get_transaction_count(OWNER_ACCOUNT)
                            app.logger.info('before sending transaction')
                            enfty_tx = enitiumcontract.functions.mintNFT(
                                OWNER_ACCOUNT, 
                                ipfs_response.text
                            ).buildTransaction({
                                'chainId': 3,
                                'gas': 100000,
                                'maxFeePerGas': w3.toWei('2', 'gwei'),
                                'maxPriorityFeePerGas': w3.toWei('1', 'gwei'),
                                'nonce': nonce
                            })
                            signed_enfty_tx = w3.eth.account.sign_transaction(enfty_tx, OWNER_PRIVATE_KEY)
                            tx_receipt = w3.eth.send_raw_transaction(signed_enfty_tx.rawTransaction)
                            app.logger.info(tx_receipt)
                            response = {'tx_hash' : tx_receipt.hex()}
                            return response
                        raise LogicError({"code": "Request Error", "description": "Token not found on IPFS host"}, 400)
                    raise LogicError({"code": "Request Error", "description": "The recipient account does not exist"}, 400)
                raise LogicError({"code": "Request Error", "description": "Bad request, input not a valid address"}, 400)
            raise LogicError({"code": "Request Error", "description": "Bad request, key input not supplied"}, 400)
        raise LogicError({"code": "Code Error", "description": "W3 not initialized"}, 500)
    raise AuthError({"code": "Unauthorized", "description": "You don't have access to this resource"}, 403)

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