import json
import logging
import os
import re
from exceptions import LogicError
from web3 import Web3, exceptions
from web3.gas_strategies.time_based import medium_gas_price_strategy

logging.basicConfig(format = '%(asctime)s %(message)s', handlers=[logging.StreamHandler()])
log = logging.getLogger('EnftyContract')
PYTHON_LOG_LEVEL = os.environ.get('PYTHON_LOG_LEVEL', 'INFO')
log.setLevel(logging.DEBUG)

INFURA_NODE_URL = os.environ.get('INFURA_NODE_URL', '')
CONTRACT_ADDRESS = os.environ.get('CONTRACT_ADDRESS', '')
OWNER_ACCOUNT = os.environ.get('OWNER_ACCOUNT', 'owner_account')
OWNER_PRIVATE_KEY = os.environ.get('OWNER_PRIVATE_KEY', 'owner_private_key')
MAX_FEE_PER_GAS = os.environ.get('MAX_FEE_PER_GAS_GWEI', '')
MAX_PRIORITY_FEE_PER_GAS = os.environ.get('MAX_PRIORITY_FEE_PER_GAS_GWEI', 'max_priority_fee_per_gas_gwei')

class EnftyContract(object):

    __singleton = None
    __w3 = None
    __contract_abi = None
    __contract = None
    __create_key = object()

    @classmethod
    def get_enfty_contract(cls):
        if cls.__singleton == None:
            cls.__singleton = EnftyContract(cls.__create_key)
            cls.__w3 = Web3(Web3.HTTPProvider(INFURA_NODE_URL))
            cls.__w3.eth.set_gas_price_strategy(medium_gas_price_strategy)
            with open('EnitiumNFT.json', 'r') as f:
                json_contract = json.load(f)
            cls.__contract_abi = json_contract["abi"]
            cls.__contract = cls.__w3.eth.contract(address=CONTRACT_ADDRESS, abi=cls.__contract_abi)
        return cls.__singleton

    def __init__(self, create_key):
        assert(create_key == EnftyContract.__create_key), "Can't craete enftycontract directly, use static getter"
        pass

    def __build_tx(self, from_address, provided_nonce=-1):
        if provided_nonce != -1 and provided_nonce >= 0:
            committed_txs = EnftyContract.__w3.eth.get_transaction_count(from_address)
            pending_txs = EnftyContract.__w3.eth.get_transaction_count(from_address, 'pending')
            log.debug('transaction count confirmed : {0}, transaction count with pending : {1}'.format(committed_txs, pending_txs))
            if(pending_txs > committed_txs):
                nonce = pending_txs
            else:
                nonce = committed_txs
        else:
            nonce = provided_nonce
        return {
            'from': from_address,
            'chainId': 3,
            #'gas': 2000000,
            'maxFeePerGas': EnftyContract.__w3.toWei(MAX_FEE_PER_GAS, 'gwei'),
            'maxPriorityFeePerGas': EnftyContract.__w3.toWei(MAX_PRIORITY_FEE_PER_GAS, 'gwei'),
            'nonce': int(nonce)
        }

    def mint(self, recipient_address, token_uri, nonce=-1):
        tx = self.__build_tx(OWNER_ACCOUNT, nonce)
        return self.__mint(recipient_address, token_uri, tx)

    def __mint(self, recipient_address, token_uri, tx):
        try:
            enfty_tx = EnftyContract.__contract.functions.mintNFT(recipient_address, token_uri).buildTransaction(tx)
            signed_transaction = EnftyContract.__w3.eth.account.sign_transaction(enfty_tx, OWNER_PRIVATE_KEY)
            tx_hash = EnftyContract.__w3.eth.send_raw_transaction(signed_transaction.rawTransaction)
            return {'tx_hash':tx_hash, 'tx':tx}
        except ValueError as ve:
            raise ValueError(ve)
        except exceptions.TimeExhausted as te:
            raise exceptions.TimeExhausted(te)

    def transfer(self, tx):
        pass

    def get_token_uri(self, token_id):
        if not EnftyContract.__w3.isConnected(): raise LogicError({"code": "Code Error", "description": "W3 not initialized"}, 500)
        try:
            tokenURI = EnftyContract.__contract.functions.tokenURI(int(token_id)).call()
            m = re.search(r'{.+}', tokenURI)
            log.debug('tokenURI : {0}; m : {0}'.format(tokenURI, m.group(0)))
            return m.group(0)
        except exceptions.ContractLogicError as e:
            log.debug('exception : {0}'.format(e))
            raise LogicError({"code": "Blockchain Error", "description": "Smart contract returned exception: {0}".format(e)}, 500)

    def wait_for_tx_receipt(self, tx_hash):
        try:
            tx_receipt = EnftyContract.__w3.eth.wait_for_transaction_receipt(tx_hash, poll_latency=0.5)
            decoded_tx_receipt = EnftyContract.__contract.events.Transfer().processReceipt(tx_receipt)
            log.debug('tx_receipt : %s', tx_receipt)
            log.debug('tx_receipt decoded : %s', decoded_tx_receipt)
            return decoded_tx_receipt
        except exceptions.TimeExhausted as te:
            raise exceptions.TimeExhausted(te)
        except ValueError as ve:
            raise ValueError(ve)