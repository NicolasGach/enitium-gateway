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

    def mint(self, tx):
        pass

    def transfer(self, tx):
        pass

    def get_token_uri(self, token_id):
        try:
            tokenURI = EnftyContract.__contract.functions.tokenURI(int(token_id)).call()
            m = re.search(r'{.+}', tokenURI)
            log.debug('tokenURI : {0}; m : {0}'.format(tokenURI, m.group(0)))
            return m.group(0)
        except exceptions.ContractLogicError as e:
            log.debug('exception : {0}'.format(e))
            raise LogicError({"code": "Blockchain Error", "description": "Smart contract returned exception: {0}".format(e)}, 500)