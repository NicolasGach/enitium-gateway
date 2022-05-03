"""Worker main module, 3 queues are available for allocation: high, default & low. \
    No distinction between the three at the moment, in the future can be the basis for different priority fee allocation for instance. Based on Redistogo
    
    .. moduleAuthor:: Nicolas Gach <nicolas@e-nitium.com> 
    
"""
import os
import redis
from rq import Worker, Queue, Connection

listen = ['high', 'default', 'low']

#redis_url = os.getenv('REDISTOGO_URL', 'redis://localhost:6379')
redis_url = os.environ.get('REDISTOGO_URL', 'redis://')

conn = redis.from_url(redis_url)

if __name__ == '__main__':
    with Connection(conn):
        worker = Worker(map(Queue, listen))
        worker.work()