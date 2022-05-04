"""Class handling cryptography operations, used to decrypt encrypted private keys

    .. moduleAuthor:: Nicolas Gach <nicolas@e-nitium.com>

"""
import base64
import g
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

log = g.log

class Crypto(object):
    """Singleton class controlling the use of cryptography methods. Cannot be instantiated directly, provisioned via singleton getter method.
    """

    __create_key = object()
    __singleton = None

    @classmethod
    def get_crypto(cls):
        """Singleton getter method.

        :return: The single instance of the Crypto class
        :rtype: Crypto

        |

        """
        if cls.__singleton == None:
            cls.singleton = Crypto(cls.__create_key)
        return cls.__singleton
    
    def __init__(self, create_key):
        """Constructor method
        """
        assert(Crypto.__create_key == create_key), "Can't instantiate crypto, must use getter"

    def decrypt_sf_aes(content, key, vector):
        """Decryption method for a content encrypted with an AES key and an initialization vector. Uses the 3rd party Crypto module (cryptography)

        :param content: Content to be decrypted.
        :type content: String
        :param key: base64 encoded AES key, stored locally (never exchange AES key)
        :type key: String
        :param vector: Initialization vector used in the original encryption. Should be generated on the fly client-side.
        :type vector: String
        :return: Decrypted content.
        :rtype: String

        |

        """
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