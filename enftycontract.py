"""Class controlling interaction with the Enfty smart contract.

    .. moduleAuthor:: Nicolas Gach <nicolas@e-nitium.com>

"""
import g
import json
import re
from exceptions import LogicError
from web3 import Web3, exceptions

log = g.log

class EnftyContract(object):
    """Singleton class controlling interaction with the Enfty smart contract.
    """

    __singleton = None
    __w3 = None
    __contract_abi = None
    __contract = None
    __create_key = object()

    @classmethod
    def get_enfty_contract(cls):
        """Singleton getter method, initializes class private variables if the singleton is not set.

        :return: The single instance of the EnftyContract class
        :rtype: EnftyContract

        |

        """
        if cls.__singleton == None:
            cls.__singleton = EnftyContract(cls.__create_key)
            cls.__w3 = Web3(Web3.HTTPProvider(g.INFURA_NODE_URL))
            with open('EnitiumNFT.json', 'r') as f:
                json_contract = json.load(f)
            cls.__contract_abi = json_contract["abi"]
            cls.__contract = cls.__w3.eth.contract(address=g.CONTRACT_ADDRESS, abi=cls.__contract_abi)
        return cls.__singleton

    def __init__(self, create_key):
        assert(create_key == EnftyContract.__create_key), "Can't craete enftycontract directly, use static getter"
        pass

    def __build_tx(self, from_address, provided_nonce=-1):
        if provided_nonce == -1:
            committed_txs = EnftyContract.__w3.eth.get_transaction_count(from_address)
            pending_txs = EnftyContract.__w3.eth.get_transaction_count(from_address, 'pending')
            log.debug('transaction count confirmed : {0}, transaction count with pending : {1}'.format(committed_txs, pending_txs))
            if(pending_txs > committed_txs):
                nonce = pending_txs
            else:
                nonce = committed_txs
        elif provided_nonce != -1 and provided_nonce >= 0:
            nonce = provided_nonce
        else:
            raise ValueError('Provided nonce can\'t have a strictly negative value')
        return {
            'from': from_address,
            'chainId': 3,
            'maxFeePerGas': EnftyContract.__w3.toWei(g.MAX_FEE_PER_GAS, 'gwei'),
            'maxPriorityFeePerGas': EnftyContract.__w3.toWei(g.MAX_PRIORITY_FEE_PER_GAS, 'gwei'),
            'nonce': int(nonce)
        }

    def mint(self, recipient_address, token_uri, nonce=-1):
        """Handles call to the contract mintNFT function.

        :param recipient_address: The on-chain address for which the token should be minted.
        :type recipient_address: String
        :param token_uri: Metadata file for the soon-to-be-minted token.
        :type token_uri: String
        :param nonce: Optional parameter, allows to override the nonce to be used in the transaction if necessary, defaults to -1
        :type nonce: int, optional
        :raises LogicError: 500 exception, if the w3 instance is not initialized
        :raises ValueError: If the nonce is overriden and has a <0 value (impossible value)
        :raises w3.exceptions.TimeExhausted: If the interaction with the chain timed out.
        :return: Transaction information retrieved from its submission to the chain.
        :rtype: JSON
        
        | Example of return :

        .. code-block:: javascript

            {
                'tx_hash': Hexadecimal('0x000...') /*Hexadecimal tx hash*/, 
                'tx': { /*Transaction as a Dictionnary*/
                    'from': '0x000...' /*obtained from from_address parameter*/,
                    'chainId': 3,
                    'maxFeePerGas': 700000000000 /*int generated from EnftyContract.__w3.toWei(g.MAX_FEE_PER_GAS, 'gwei')*/,
                    'maxPriorityFeePerGas': 2000000000 /*int generated from EnftyContract.__w3.toWei(g.MAX_PRIORITY_FEE_PER_GAS, 'gwei')*/,
                    'nonce': 72 /*int(nonce), with a nonce value either provided by the override or computed from pending transactions / committed transactions number for the sender account.*/
                }
            }

        |

        """
        if not EnftyContract.__w3.isConnected(): raise LogicError({"code": "Code Error", "description": "W3 not initialized"}, 500)
        tx = self.__build_tx(g.OWNER_ACCOUNT, nonce)
        return self.__mint(recipient_address, token_uri, tx)

    def __mint(self, recipient_address, token_uri, tx):
        try:
            enfty_tx = EnftyContract.__contract.functions.mintNFT(recipient_address, token_uri).buildTransaction(tx)
            signed_transaction = EnftyContract.__w3.eth.account.sign_transaction(enfty_tx, g.OWNER_PRIVATE_KEY)
            tx_hash = EnftyContract.__w3.eth.send_raw_transaction(signed_transaction.rawTransaction)
            return {'tx_hash':tx_hash, 'tx':tx}
        except ValueError as ve:
            if isinstance(ve.args[0], str):
                raise ValueError(ve.args[0]) from ve
            else:
                raise ValueError() from ve
        except exceptions.TimeExhausted as te:
            if isinstance(te.args[0], str):
                raise exceptions.TimeExhausted(te.args[0])
            else:
                raise exceptions.TimeExhausted()

    def transfer(self, from_address, from_pk, to_address, token_id, nonce=-1):
        """Handles call to the contract transferFrom function.

        :param from_address: The on-chain address of the current owner of the token (transaction signer)
        :type from_address: String
        :param from_pk: The decrypted private key of the signer, used for signing
        :type from_pk: String
        :param to_address: The on-chain address of the token receiver
        :type to_address: String
        :param token_id: The contract-generated ID of the token to be transfered
        :type token_id: String
        :param nonce: Optional parameter, allows to override the nonce to be used in the transaction if necessary, defaults to -1
        :type nonce: int, optional
        :raises LogicError: 500 exception, if the w3 instance is not initialized
        :raises ValueError: If the nonce is overriden and has a <0 value (impossible value)
        :raises w3.exceptions.TimeExhausted: If the interaction with the chain timed out.
        :return: Transaction information retrieved from its submission to the chain.
        :rtype: JSON
        
        | Example of return :

        .. code-block:: javascript

            {
                'tx_hash': Hexadecimal('0x000...') /*Hexadecimal tx hash*/, 
                'tx': { /*Transaction as a Dictionnary*/
                    'from': '0x000...' /*obtained from from_address parameter*/,
                    'chainId': 3,
                    'maxFeePerGas': 700000000000 /*int generated from EnftyContract.__w3.toWei(g.MAX_FEE_PER_GAS, 'gwei')*/,
                    'maxPriorityFeePerGas': 2000000000 /*int generated from EnftyContract.__w3.toWei(g.MAX_PRIORITY_FEE_PER_GAS, 'gwei')*/,
                    'nonce': 72 /*int(nonce), with a nonce value either provided by the override or computed from pending transactions / committed transactions number for the sender account.*/
                }
            }

        |

        """
        if not EnftyContract.__w3.isConnected(): raise LogicError({"code": "Code Error", "description": "W3 not initialized"}, 500)
        tx = self.__build_tx(from_address, nonce)
        return self.__transfer(from_address, from_pk, to_address, token_id, tx)

    def __transfer(self, from_address, from_pk, to_address, token_id, tx):
        try:
            enfty_tx = EnftyContract.__contract.functions.transferFrom(from_address, to_address, int(token_id)).buildTransaction(tx)
            signed_transaction = EnftyContract.__w3.eth.account.sign_transaction(enfty_tx, from_pk)
            tx_hash = EnftyContract.__w3.eth.send_raw_transaction(signed_transaction.rawTransaction)
            return {'tx_hash':tx_hash, 'tx':tx}
        except ValueError as ve:
            if isinstance(ve.args[0], str):
                raise ValueError(ve.args[0]) from ve
            else:
                raise ValueError() from ve
        except exceptions.TimeExhausted as te:
            if isinstance(te.args[0], str):
                raise exceptions.TimeExhausted(te.args[0])
            else:
                raise exceptions.TimeExhausted()

    def burn(self, from_address, from_pk, token_id, nonce=-1):
        """Handles call to the contract burn function.

        :param from_address: The on-chain address of the current owner of the token (transaction signer)
        :type from_address: String
        :param from_pk: The decrypted private key of the signer, used for signing
        :type from_pk: String
        :param token_id: The contract-generated ID of the token to be burned
        :type token_id: String
        :param nonce: Optional parameter, allows to override the nonce to be used in the transaction if necessary, defaults to -1
        :type nonce: int, optional
        :raises LogicError: 500 exception, if the w3 instance is not initialized
        :raises ValueError: If the nonce is overriden and has a <0 value (impossible value)
        :raises w3.exceptions.TimeExhausted: If the interaction with the chain timed out.
        :return: Transaction information retrieved from its submission to the chain.
        :rtype: JSON
        
        | Example of return :

        .. code-block:: javascript

            {
                'tx_hash': Hexadecimal('0x000...') /*Hexadecimal tx hash*/, 
                'tx': { /*Transaction as a Dictionnary*/
                    'from': '0x000...' /*obtained from from_address parameter*/,
                    'chainId': 3,
                    'maxFeePerGas': 700000000000 /*int generated from EnftyContract.__w3.toWei(g.MAX_FEE_PER_GAS, 'gwei')*/,
                    'maxPriorityFeePerGas': 2000000000 /*int generated from EnftyContract.__w3.toWei(g.MAX_PRIORITY_FEE_PER_GAS, 'gwei')*/,
                    'nonce': 72 /*int(nonce), with a nonce value either provided by the override or computed from pending transactions / committed transactions number for the sender account.*/
                }
            }

        |

        """
        if not EnftyContract.__w3.isConnected(): raise LogicError({"code": "Code Error", "description": "W3 not initialized"}, 500)
        tx = self.__build_tx(from_address, nonce)
        return self.__burn(from_pk, token_id, tx)

    def __burn(self, from_pk, token_id, tx):
        try:
            enfty_tx = EnftyContract.__contract.functions.burn(int(token_id)).buildTransaction(tx)
            signed_transaction = EnftyContract.__w3.eth.account.sign_transaction(enfty_tx, from_pk)
            tx_hash = EnftyContract.__w3.eth.send_raw_transaction(signed_transaction.rawTransaction)
            return {'tx_hash':tx_hash, 'tx':tx}
        except ValueError as ve:
            if isinstance(ve.args[0], str):
                raise ValueError(ve.args[0]) from ve
            else:
                raise ValueError() from ve
        except exceptions.TimeExhausted as te:
            if isinstance(te.args[0], str):
                raise exceptions.TimeExhausted(te.args[0])
            else:
                raise exceptions.TimeExhausted()

    def get_token_uri(self, token_id):
        """Retrieves the token metadata based on its contract-generated ID

        :param token_id: Contract-generated ID of the token which metadata is to be retrieved
        :type token_id: String
        :raises LogicError: 500 exception, if the w3 instance is not initialized
        :raises LogicError: 500 exception, exception returned by the smart contract
        :return: Token metadata content as String. The returned content is very close to a JSON value, only prefixed & suffixed by a few bytes which should be removed client-side.
        :rtype: String

        | Example of return value:

        .. code-block:: javascript

            // As explained above, the content of the return would be this but surrounded by bytes to be removed, i.e. the JSON content has to be parsed client-side
            {
                "bill_of_lading_title":"BoL extraction json",
                "bill_of_lading_sf_id":"a017Q00000JvZN7QAN",
                "bill_of_lading_n":"QSKJHD982","vessel":"MV Enitium",
                "port_of_loading":"Dunkerque",
                "port_of_discharge":"New York Harbor",
                "name":"BOL-0000008"
            }
        
        |

        """
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
        """Method polling the chain for the transaction receipt every 0.5 seconds. \
            The polling rate is important to manage carefully to avoid going above the node manager's request thresholds. \
            Timeout occurs after 120 seconds. Adjust the priorityFee to avoid timeout issues.

        :param tx_hash: Hexadecimal hash of the transaction to be retrieved
        :type tx_hash: HexBytes
        :raises w3.exceptions.TimeExhausted: Thrown when the polling times out.
        :raises ValueError: Thrown in case of incorrect input, e.g. incorrect tx_hash
        :return: The decoded transaction receipt
        :rtype: Dictionnary

        | Example of return value

        .. code-block:: python

            AttributeDict({
                'blockHash': HexBytes('0x9950bd2750308eb0ce683ec5bf6df0f7b675b1a8c42943397ee693f0cf24c724'), 
                'blockNumber': 12230942, 
                'contractAddress': None, 
                'cumulativeGasUsed': 74691, 
                'effectiveGasPrice': 56414542820, 
                'from': '0xCb763Fb9804774B87A54659bd32Cdb89c5153C12', 
                'gasUsed': 74691, 
                'logs': [
                    AttributeDict({
                        'address': '0xdE2b51ba8888e401725Df10328EE5063fdaF1a3E', 
                        'blockHash': HexBytes('0x9950bd2750308eb0ce683ec5bf6df0f7b675b1a8c42943397ee693f0cf24c724'), 
                        'blockNumber': 12230942, 
                        'data': '0x', 
                        'logIndex': 0, 
                        'removed': False, 
                        'topics': [
                            HexBytes('0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'), 
                            HexBytes('0x000000000000000000000000cb763fb9804774b87a54659bd32cdb89c5153c12'), 
                            HexBytes('0x0000000000000000000000000000000000000000000000000000000000000000'), 
                            HexBytes('0x000000000000000000000000000000000000000000000000000000000000002b')
                        ], 
                        'transactionHash': HexBytes('0x3b42a3339781f6cab5c08f2bb943b9e9e90c8340fbed2d477ba7bf56962e5696'), 
                        'transactionIndex': 0
                    }), 
                    AttributeDict({
                        'address': '0xdE2b51ba8888e401725Df10328EE5063fdaF1a3E', 
                        'blockHash': HexBytes('0x9950bd2750308eb0ce683ec5bf6df0f7b675b1a8c42943397ee693f0cf24c724'), 
                        'blockNumber': 12230942, 
                        'data': '0x', 
                        'logIndex': 1, 
                        'removed': False, 
                        'topics': [
                            HexBytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'), 
                            HexBytes('0x000000000000000000000000cb763fb9804774b87a54659bd32cdb89c5153c12'), 
                            HexBytes('0x0000000000000000000000000000000000000000000000000000000000000000'), 
                            HexBytes('0x000000000000000000000000000000000000000000000000000000000000002b')
                        ], 
                        'transactionHash': HexBytes('0x3b42a3339781f6cab5c08f2bb943b9e9e90c8340fbed2d477ba7bf56962e5696'), 
                        'transactionIndex': 0
                    })
                ], 
                'logsBloom': HexBytes('0x00000000000800000000000000000000000000000000000000000000000000000000000000000000000040000000000000000000000001000000000000200000000000000000000000800008000000000000000000000000000000000000000000000000020000000000000000000800000000000000000000000010000000000000000000000000000000000000000000000000000000000000000000000000028000000000000000000000000000000000000000000000000000000000000000000002000000100000000000000000000000000000000000000000000020000010000000000000000000000000000020000000000001010000000000000000'), 
                'status': 1, 
                'to': '0xdE2b51ba8888e401725Df10328EE5063fdaF1a3E', 
                'transactionHash': HexBytes('0x3b42a3339781f6cab5c08f2bb943b9e9e90c8340fbed2d477ba7bf56962e5696'), 
                'transactionIndex': 0, 
                'type': '0x2'
            })
        
        |

        """
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

    def check_addresses(*addresses):
        """Static method, checks whether the provided addresses are on-chain addresses

        :raises LogicError: 400 exception, raised if one of the address is not an on-chain address

        | This method works in the following way: raises an exception if an address is not an on-chain address, otherwise nothing happens.
        |

        """
        contract = EnftyContract.get_enfty_contract()
        for address in addresses:
            if not contract.__w3.isAddress(address) :
                raise LogicError({"code": "Request Error", "description": "Bad request, input not a valid address"}, 400)

    def check_minimum_balances(*addresses):
        """Static method, checks whether the provided addresses have a network token balance above the minimum threshold (currently 200000 gwei)

        :raises LogicError: 400 exception, raised if one of the address doesn't have the minimum minimum required balance, or if it doesn't exist

        | This method works in the following way: raises an exception if an address is not an on-chain address, otherwise nothing happens.
        |

        """
        contract = EnftyContract.get_enfty_contract()
        for address in addresses:
            if not contract.__w3.eth.get_balance(address) > 200000:
                raise LogicError({"code": "Request Error", "description": "The sender account has no funds or does not exist"}, 400)