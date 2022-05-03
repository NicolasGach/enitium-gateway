"""Module containing custom exceptions' definitions

    .. moduleAuthor:: Nicolas Gach <nicolas@e-nitium.com>

"""

class AuthError(Exception):
    """Custom Exception subclass, used to handle api request related exceptions.
    
    |

    """
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code

class LogicError(Exception):
    """Custom Exception subclass, used to handle potential errors in the server-side logic and throw resulting exceptions.
    
    |

    """
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code
