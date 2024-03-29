"""Class controlling interactions with the postgre database pertaining to transaction log management.

    .. moduleAuthor:: Nicolas Gach <nicolas@e-nitium.com>

"""
import g
import uuid
from datetime import datetime, timezone
from sqlalchemy import create_engine, MetaData, Table, and_, func
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import select, update

log = g.log

class TxDbManager(object):
    """Singleton class controlling interactions with the transaction log in the Postgre database.
    """

    __singleton = None
    __create_key = object()
    __engine = None
    __txs = None

    @classmethod
    def get_tx_db_manager(cls, database_url, logging_name):
        """Singleton getter method, initializes class private variables, including db connection and ORM, if the singleton is not set.

        :return: The single instance of the TxDbManager class
        :rtype: TxDbManager
        
        |

        """
        if cls.__singleton == None:
            cls.__engine = create_engine(database_url.replace('postgres://', 'postgresql://', 1), logging_name=logging_name)
            metadata_obj = MetaData(schema='salesforce')
            metadata_obj.reflect(bind=cls.__engine, only = ['enfty_bol_transfer_data__c'])
            Base = automap_base(metadata=metadata_obj)
            Base.prepare()
            cls.__txs = Base.classes.enfty_bol_transfer_data__c
            log.debug('table keys : {0}'.format(metadata_obj.tables.keys()))
            cls.__singleton = cls(cls.__create_key, cls.__engine)
        return cls.__singleton

    def __init__ (self, create_key, engine):
        assert(create_key == TxDbManager.__create_key), "TxDbManager instances must be obtained via get_tx_db_manager()"
        self.sessionmaker = sessionmaker(engine)

    def create_tx_in_db(self, bill_of_lading_id, sent_from, to_address, tx_type, from_address='', token_id=''):
        """Creates the log entry for the tranasaction in postgre

        :param bill_of_lading_id: Salesforce ID of the Bill_Of_Lading__c record to which the transaction pertains
        :type bill_of_lading_id: String
        :param sent_from: On-chain address who sent the transaction
        :type sent_from: String
        :param to_address: On-chain address considered recipient of the transaction (new token owner in case of transfer or minting for instance)
        :type to_address: String
        :param tx_type: Type of the transaction (3 possible values : Minting, Transfer, Burn), allowed values are those of the Salesforce Bill_Of_Lading__c.Type__c picklist values
        :type tx_type: String
        :param from_address: On-chain address from which the transaction will originate (transaction signer), defaults to ''
        :type from_address: String, optional
        :param token_id: Contract-generated ID of the token to which the transaction will apply, defaults to ''
        :type token_id: String, optional
        :return: Dictionnary containing the transaction log entry identifiers
        :rtype: Dictionnary

        | Example of return value:

        .. code-block:: python

            {
                'uuid': 30df4399-e07f-4c95-9e65-f5c63cd654fe, 
                'id': 26
            }

        |

        """
        with self.sessionmaker() as session:
            tx_uuid = uuid.uuid4()
            tx = TxDbManager.__txs(
                sent_from__c = sent_from,
                to_address__c = to_address,
                gateway_id__c =  tx_uuid,
                bill_of_lading__c = bill_of_lading_id,
                status__c = 'Processing',
                last_status_change_date__c = datetime.now(timezone.utc),
                type__c = tx_type
            )
            if tx_type == 'Transfer':
                tx.from_address__c = from_address
                tx.token_id__c = token_id
            session.add(tx)
            session.commit()
            log.debug('About to return values : {0}, {1}'.format(tx.gateway_id__c, tx.id))
            return {'uuid': tx.gateway_id__c, 'id': tx.id}
    
    def update_tx_as_sent(self, tx_uuid, tx_hash, tx):
        """Update transaction's log entry status as 'Sent' in the database, providing additional information at that stage of the transaction's management (transaction hash and nonce)

        :param tx_uuid: UUID of the log entry in the postgre database
        :type tx_uuid: String
        :param tx_hash: Transaction hash returned by the chain
        :type tx_hash: Hexadecimal
        :param tx: Dictionnary containing the transaction information, must contain a 'nonce' entry
        :type tx: Dictionnary

        |

        """
        with self.sessionmaker() as session:
            session.execute(
                update(TxDbManager.__txs).where(TxDbManager.__txs.gateway_id__c == tx_uuid).values(
                    status__c = 'Sent',
                    last_status_change_date__c = datetime.now(timezone.utc),
                    tx_hash__c = tx_hash.hex(),
                    nonce__c = tx['nonce']
                )
            )
            session.commit()
    
    def update_tx_with_receipt(self, tx_uuid, tx_receipt):
        """Update transaction's log entry status as 'Cleared' in the database, providing additional information at that stage \
            of the transaction's management (receipt information such as from_address, to_address and token_id)

        :param tx_uuid: UUID of the log entry in the postgre database
        :type tx_uuid: String
        :param tx_hash: Transaction hash returned by the chain
        :type tx_hash: Hexadecimal
        :param tx_receipt: Dictionnary containing the decoded transaction's receipt information
        :type tx: Dictionnary
        
        |

        """
        with self.sessionmaker() as session:
            session.execute(    
                update(TxDbManager.__txs).where(TxDbManager.__txs.gateway_id__c == tx_uuid).values(
                    tx_hash__c = tx_receipt[0]['transactionHash'].hex(),
                    from_address__c = tx_receipt[0]['args']['from'], 
                    to_address__c = tx_receipt[0]['args']['to'], 
                    token_id__c = tx_receipt[0]['args']['tokenId'],
                    status__c = 'Cleared',
                    last_status_change_date__c = datetime.now(timezone.utc),
                )
            )
            session.commit()

    def update_tx_as_failed(self, tx_uuid, code, message):
        """Update transaction's log entry status as 'Failed' in the database, providing additional information at that stage \
            of the transaction's management (error code and error message related to the failure state)

        :param tx_uuid: UUID of the log entry in the postgre database
        :type tx_uuid: String
        :param code: Error code for the error related to the transaction's failure
        :type code: String
        :param message: Error message for the error related to the transaction's failure
        :type message: String

        |

        """
        with self.sessionmaker() as session:
            session.execute(
                update(TxDbManager.__txs).where(
                    TxDbManager.__txs.gateway_id__c == str(tx_uuid)
                ).values(
                    status__c = 'Failed',
                    last_status_change_date__c = datetime.now(timezone.utc),
                    error_code__c = code,
                    error_message__c = message
                )
            )
            session.commit()

    def get_highest_nonce(self, from_address):
        """Returns the highest nonce registered in the database for transactions signed by a given on-chain address

        :param from_address: On-chain address, transactions' signee
        :type from_address: String
        :return: Highest nonce for the transaction scope where the signee is from_address
        :rtype: Integer

        |

        """
        with self.sessionmaker() as session:
            db_nonce = session.execute(
                select(
                    func.max(TxDbManager.__txs.nonce__c)
                ).where(
                    TxDbManager.__txs.from_address__c == from_address)
            ).scalar()
            session.commit()
            return db_nonce

    def get_db_nonce(self, from_address):
        """Returns the highest nonce registered in the database for 'Cleared' transactions signed by a given on-chain address

        :param from_address: On-chain address, transactions' signee
        :type from_address: String
        :return: Highest nonce for the transaction scope where the signee is from_address
        :rtype: Integer

        |

        """
        with self.sessionmaker() as session:
            db_nonce = session.execute(
                select(
                    func.max(TxDbManager.__txs.nonce__c)
                ).where(
                    and_(
                        TxDbManager.__txs.sent_from__c == from_address,
                        TxDbManager.__txs.status__c == 'Cleared'
                    )
                )
            ).scalar()
            session.commit()
            return db_nonce


    def get_db_highest_failed_nonce(self, from_address):
        """Returns the highest nonce registered in the database for 'Failed' transactions signed by a given on-chain address

        :param from_address: On-chain address, transactions' signee
        :type from_address: String
        :return: Highest nonce for the transaction scope where the signee is from_address
        :rtype: Integer

        |

        """
        with self.sessionmaker() as session:
            db_highest_failed = session.execute(
                select(
                    func.max(TxDbManager.__txs.nonce__c)
                ).where(
                    and_(
                        TxDbManager.__txs.sent_from__c == from_address,
                        TxDbManager.__txs.status__c == 'Failed'
                    )
                )
            ).scalar()
            return db_highest_failed