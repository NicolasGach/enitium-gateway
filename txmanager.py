import logging
import uuid
from datetime import datetime, timezone
from sqlalchemy import create_engine, MetaData, Table, and_, func
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import select

class TxDbManager(object):

    __singleton = None
    __create_key = object()
    __engine = None
    __txs = None
    __db_session = None

    @classmethod
    def get_tx_db_manager(cls, database_url, logging_name):
        if cls.__singleton == None:
            cls.__engine = create_engine(database_url.replace('postgres://', 'postgresql://', 1), logging_name=logging_name)
            metadata_obj = MetaData(schema='salesforce')
            metadata_obj.reflect(bind=cls.__engine, only = ['enfty_bol_transfer_data__c'])
            Base = automap_base(metadata=metadata_obj)
            Base.prepare()
            cls.__txs = Base.classes.enfty_bol_transfer_data__c
            #cls.__txs = metadata_obj.tables['salesforce.enfty_bol_transfer_data__c']
            logging.info('table keys : %s', metadata_obj.tables.keys())
            cls.__singleton = cls(cls.__create_key, cls.__engine)
        return cls.__singleton

    def __init__ (self, create_key, engine):
        assert(create_key == TxDbManager.__create_key), "TxDbManager instances must be obtained via gt_TxDbManager()"
        self.sessionmaker = sessionmaker(engine)

    def create_tx_in_db(self, sent_from, from_address, to_address, token_id, tx_type, bill_of_lading_id):
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
            return {'uuid': tx.gateway_id__c, 'id': tx.id}

    def log_tx(self):
        pass