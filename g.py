"""Module containing global constants used throughout the gateway. Usage practice: import g, then use constants as g.[Constant]

.. moduleAuthor:: Nicolas Gach <nicolas@e-nitium.com>

"""
import logging
import os

AES_KEY = os.environ.get('AES_KEY', '')
"""String: AES key to be used in decryption."""

ALGORITHMS = os.environ.get('ALGORITHMS', '').split(' ')
"""String: Available algorithms for bearer token decryption, used in authentication procedure."""

API_AUDIENCE = os.environ.get('API_AUDIENCE', '')
"""String: Audience of the api, used in authentication procedure."""

AUTH0_DOMAIN = os.environ.get('AUTH0_DOMAIN', '')
"""String: Endpoint for Auth0 requests."""

CONTRACT_ADDRESS = os.environ.get('CONTRACT_ADDRESS', '')
"""String: On-chain address of the Enfty smart contract."""

DATABASE_URL = os.environ.get('DATABASE_URL', 'postgres://urifrxjjebgkrj:e007f6cad0a82178bd8cc058e25ea4e318c36f93a7401ebb83506061773c2054@ec2-52-215-22-82.eu-west-1.compute.amazonaws.com:5432/d921f851m84mkn')
"""String: Database URL for the Postgre database on Heroku."""

FORCE_GAS_MULTIPLIER = int(os.environ.get('FORCE_GAS_MULTIPLIER', '0'))
"""(Deprecated) String: multiplier to be used to amp up gas price in the event of a forced transaction."""

INFURA_IPFS_URL = os.environ.get('INFURA_IPFS_URL', '')
"""String: Endpoint for the Infura project used to interact with the Infura-managed IPFS network."""

INFURA_NODE_URL = os.environ.get('INFURA_NODE_URL', '')
"""String: Endpoint for the Infura project used to interact with the node managed by Infura"""

IPFS_PROJECT_ID = os.environ.get('IPFS_PROJECT_ID', 'ipfs_project_id')
"""String: Authentication element used in Basic Authentication for the Infura IPFS project."""

IPFS_PROJECT_SECRET = os.environ.get('IPFS_PROJECT_SECRET', 'ipfs_project_secret')
"""String: Authentication element used in Basic Authentication for the Infura IPFS project."""

MAX_FEE_PER_GAS = os.environ.get('MAX_FEE_PER_GAS_GWEI', '')
"""String: Max Fee per Gas as used in EIP-1559 specifications transactions."""

MAX_PRIORITY_FEE_PER_GAS = os.environ.get('MAX_PRIORITY_FEE_PER_GAS_GWEI', 'max_priority_fee_per_gas_gwei')
"""String: Max priority Fee per Gas as used in EIP-1559 specifications transactions."""

OWNER_ACCOUNT = os.environ.get('OWNER_ACCOUNT', '')
"""String: On-chain address of the owner account for the enfty smart contract."""

OWNER_PRIVATE_KEY = os.environ.get('OWNER_PRIVATE_KEY', '')
"""String: Private key of the owner account for the enfty smart contract."""

PYTHON_LOG_LEVEL = os.environ.get('PYTHON_LOG_LEVEL', 'INFO')
"""String: Debug level to be used in Python logging."""

REDISTOGO_URL = os.environ.get('REDISTOGO_URL', '')
"""String: Endpoint for the Redistogo instance used for worker queues."""

logging.basicConfig(format = '%(asctime)s %(message)s', handlers=[logging.StreamHandler()])
log = logging.getLogger('EnftyContract')
"""logging.Logger used throughout the gateway as a global constant"""
log.setLevel(logging.DEBUG)