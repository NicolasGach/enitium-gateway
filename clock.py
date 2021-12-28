from pytz import utc
import os

from apscheduler.scheduler.background import BackgroundScheduler
from apscheduler.scheduler.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

jobstores = {
    'default': SQLAlchemyJobStore(os.environ['DATABASE_URL'].replace('postgres://', 'postgresql://', 1))
}
executors = { 'default': ThreadPoolExecutor(20) }
job_defaults = {
    'coalesce': False,
    'max_instances': 3
}

scheduler = BackgroundScheduler(jobstores=jobstores, executors=executors, job_defaults=job_defaults, timezone=utc)

def test():
    print('test_job schedule')

scheduler.add_job(test, 'interval', seconds=30, id='test_job')

scheduler.start()