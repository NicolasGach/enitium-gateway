"""Script library containing methods which can be passed to the worker's queues for execution.

    .. moduleAuthor:: Nicolas Gach <nicolas@e-nitium.com>

"""
import g
from txmanager import TxDbManager
from enftycontract import EnftyContract
from web3 import exceptions

log = g.log

global process_mint
def process_mint(tx_uuid, recipient_address, token_uri, nonce=-1):
    """Processes 'Minting' transactions in the worker

    :param tx_uuid: UUID of the transaction in the postgre database
    :type tx_uuid: String
    :param recipient_address: On-chain address targeted by the transaction (newly minted token recipient)
    :type recipient_address: String
    :param token_uri: Token metadata (retrieved from IPFS)
    :type token_uri: String
    :param nonce: If provided, overrides the computed nonce value for the transaction, defaults to -1
    :type nonce: int, optional

    | The method captures exceptions thrown by txmanager's or enftycontract's methods called during its execution, and consequently updates the transactions as failed. \
        Those exceptions can be ValueError or w3.exceptions.TimeExhausted.
    |

    """
    tx_db_manager = TxDbManager.get_tx_db_manager(g.DATABASE_URL, 'gatewayengine')
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
    """Processes 'Transfer' transactions in the worker

    :param tx_uuid: UUID of the transaction in the postgre database
    :type tx_uuid: String
    :param from_address: On-chain address signing the transaction (current owner of the token)
    :type from_address: String
    :param from_pk: Private key of the signing account
    :type from_pk: String
    :param recipient_address: On-chain address targeted by the transaction (new token owner)
    :type recipient_address: String
    :param token_id: Contract-generated ID of the token to be transferred
    :type token_id: String
    :param nonce: If provided, overrides the computed nonce value for the transaction, defaults to -1
    :type nonce: int, optional

    | The method captures exceptions thrown by txmanager's or enftycontract's methods called during its execution, and consequently updates the transactions as failed. \
        Those exceptions can be ValueError or w3.exceptions.TimeExhausted.
    |

    """
    tx_db_manager = TxDbManager.get_tx_db_manager(g.DATABASE_URL, 'gatewayengine')
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

global process_burn
def process_burn(tx_uuid, from_address, from_pk, token_id, nonce=-1):
    """Processes 'Burn' transactions in the worker

    :param tx_uuid: UUID of the transaction in the postgre database
    :type tx_uuid: String
    :param from_address: On-chain address signing the transaction (current owner of the token)
    :type from_address: String
    :param from_pk: Private key of the signing account
    :type from_pk: String
    :param token_id: Contract-generated ID of the token to be transferred
    :type token_id: String
    :param nonce: If provided, overrides the computed nonce value for the transaction, defaults to -1
    :type nonce: int, optional

    | The method captures exceptions thrown by txmanager's or enftycontract's methods called during its execution, and consequently updates the transactions as failed. \
        Those exceptions can be ValueError or w3.exceptions.TimeExhausted.
    |

    """
    tx_db_manager = TxDbManager.get_tx_db_manager(g.DATABASE_URL, 'gatewayengine')
    try:
        contract = EnftyContract.get_enfty_contract()
        if nonce != -1 and nonce >= 0:
            tx_result = contract.burn(from_address, from_pk, int(token_id), nonce)
        else:
            tx_result = contract.burn(from_address, from_pk, int(token_id))
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