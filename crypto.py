import base64
import g
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

log = g.log

class Crypto(object):

    __create_key = object()
    __singleton = None

    @classmethod
    def get_crypto(cls):
        if cls.__singleton == None:
            cls.singleton = Crypto(cls.__create_key)
    
    def __init__(self, create_key):
        assert(Crypto.__create_key == create_key), "Can't instantiate crypto, must use getter"

    def decrypt_sf_aes(content, key, vector):
        log.debug('vector : %s | content : %s', vector, content)
        bvector = vector.encode('utf-8')
        bkey = base64.b64decode(key)
        log.debug('decoded vector : %s | decoded key : %s', bvector, bkey)
        cipher = AES.new(bkey, AES.MODE_CBC, bvector)
        log.debug('after cipher')
        bcontent = base64.b64decode(content)
        result = unpad(cipher.decrypt(bcontent), AES.block_size)
        result_text = result.decode('utf-8')
        return result_text.strip()