import logging
import os

AES_KEY = os.environ.get('AES_KEY', '')
ALGORITHMS = os.environ.get('ALGORITHMS', '')
API_AUDIENCE = os.environ.get('API_AUDIENCE', '')
AUTH0_DOMAIN = os.environ.get('AUTH0_DOMAIN', '')
CONTRACT_ADDRESS = os.environ.get('CONTRACT_ADDRESS', '')
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgres://urifrxjjebgkrj:e007f6cad0a82178bd8cc058e25ea4e318c36f93a7401ebb83506061773c2054@ec2-52-215-22-82.eu-west-1.compute.amazonaws.com:5432/d921f851m84mkn')
FORCE_GAS_MULTIPLIER = int(os.environ.get('FORCE_GAS_MULTIPLIER', '0'))
INFURA_IPFS_URL = os.environ.get('INFURA_IPFS_URL', '')
INFURA_NODE_URL = os.environ.get('INFURA_NODE_URL', '')
IPFS_PROJECT_ID = os.environ.get('IPFS_PROJECT_ID', 'ipfs_project_id')
IPFS_PROJECT_SECRET = os.environ.get('IPFS_PROJECT_SECRET', 'ipfs_project_secret')
MAX_FEE_PER_GAS = os.environ.get('MAX_FEE_PER_GAS_GWEI', '')
MAX_PRIORITY_FEE_PER_GAS = os.environ.get('MAX_PRIORITY_FEE_PER_GAS_GWEI', 'max_priority_fee_per_gas_gwei')
OWNER_ACCOUNT = os.environ.get('OWNER_ACCOUNT', '')
OWNER_PRIVATE_KEY = os.environ.get('OWNER_PRIVATE_KEY', '')
PYTHON_LOG_LEVEL = os.environ.get('PYTHON_LOG_LEVEL', 'INFO')
REDISTOGO_URL = os.environ.get('REDISTOGO_URL', '')

logging.basicConfig(format = '%(asctime)s %(message)s', handlers=[logging.StreamHandler()])
log = logging.getLogger('EnftyContract')
log.setLevel(logging.DEBUG)