from jose import jwt
import os

def jwt_gen():
    PRIVATE_KEY=os.environ['JWT_PRIVATE_KEY']
    passphrase=os.environ['JWT_PASSPHRASE']
    jwt_encoded=''
    return jwt_encoded