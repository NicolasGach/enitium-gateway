"""Module handling operations related to the authentication of incoming request via auth0. The authentication validates a bearer token born by the requests.

    .. moduleAuthor:: Nicolas Gach <nicolas@e-nitium.com>

"""
import g
import json
from exceptions import AuthError
from flask import request, _request_ctx_stack
from functools import wraps
from jose import jwt
from six.moves.urllib.request import urlopen

log = g.log

def get_token_auth_header():
    """Parse request header to extract the bearer token.

    :raises AuthError: 401 exception, authorization_header_missing if the Authorization header is missing from the request
    :raises AuthError: 401 exception, invalid_header if the Authorization header doesn't start with Bearer
    :raises AuthError: 401 exception, invalid_header if the token is not found after Bearer
    :raises AuthError: 401 exception, invalid_header if the Authorization header format doesn't follow the Bearer [token] format
    :return: Extracted bearer token
    :rtype: String

    |

    """
    auth = request.headers.get("Authorization", None)
    if not auth:
        raise AuthError({"code": "authorization_header_missing", "description": "Authorization header is expected"}, 401)

    parts = auth.split()

    if parts[0].lower()!="bearer":
        raise AuthError({"code": "invalid_header", "description": "Authorization header must start with Bearer"}, 401)
    elif len(parts) == 1:
        raise AuthError({"code": "invalid_header", "description": "Token not found"}, 401)
    elif len(parts) > 2:
        raise AuthError({"code": "invalid_header", "description": "Authorization header must be 'Bearer token'"}, 401)

    token = parts[1]

    return token

def requires_auth(f):
    """Decorator function, checks if the requested is authenticated via Auth0

    :raises AuthError: 401 exception, token_expired if the Bearer token is expired
    :raises AuthError: 401 exception, invalid_claims if the Bearer token content has invalid claims (audience, issuer)
    :raises AuthError: 401 exception, invalid_header if the system could not parse the Authorization header
    :raises AuthError: 401 exception, invalid_header if the token could not be extracted from the Authorization header
    :return: decorated function

    |

    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_auth_header()
        jsonurl = urlopen("https://"+g.AUTH0_DOMAIN+"/.well-known/jwks.json")
        jwks = json.loads(jsonurl.read())
        unverified_header = jwt.get_unverified_header(token)
        rsa_key = {}
        for key in jwks["keys"]:
            if key["kid"] == unverified_header["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                }
        if rsa_key:
            try:
                payload = jwt.decode(
                    token,
                    rsa_key,
                    algorithms=g.ALGORITHMS,
                    audience=g.API_AUDIENCE,
                    issuer="https://"+g.AUTH0_DOMAIN+"/"
                )
            except jwt.ExpiredSignatureError:
                raise AuthError({"code": "token_expired", "description": "token is expired"}, 401)

            except jwt.JWTClaimsError:
                raise AuthError({"code": "invalid_claims", "description": "incorrect claims, please check the audience and issuer"}, 401)

            except Exception:
                log.debug(g.API_AUDIENCE)
                log.debug(g.AUTH0_DOMAIN)
                log.debug(g.ALGORITHMS)
                raise AuthError({"code": "invalid_header", "description": "unable to parse authentication token"}, 401)

            _request_ctx_stack.top.current_user = payload
            return f(*args, **kwargs)
        raise AuthError({"code": "invalid_header", "description": "Unable to find appropriate key"}, 401)

    return decorated

def requires_scope(required_scope):
    """Utility method

    :param required_scope: API authorization scope required to access the resource. Client authorization scopes are managed in Auth0.
    :type required_scope: String
    :return: True or false depending on whether the client credentials bear the appropriate authorization scope or not
    :rtype: Boolean

    |
    
    """
    token = get_token_auth_header()
    unverified_claims = jwt.get_unverified_claims(token)
    if unverified_claims.get("scope"):
        token_scopes = unverified_claims["scope"].split()
        for token_scope in token_scopes:
            if token_scope == required_scope:
                return True
    return False