import base64
import hashlib
import hmac
import binascii

from config import Config


def encode_string(string):
    """Encodes a string to bytes, if it isn't already.
    :param string: The string to encode"""

    if isinstance(string, str):
        string = string.encode("utf-8")
    return string


def get_hmac(password):
    """Returns a Base64 encoded HMAC+SHA512 of the password signed with
    the salt specified by *SECURITY_PASSWORD_SALT*.
    :param password: The password to sign
    """
    salt = Config.PASSWORD_SALT
    password_hash = Config.PASSWORD_HASH

    if salt is None:
        raise RuntimeError(
            "The configuration value `SECURITY_PASSWORD_SALT` must "
            "not be None when the value of `SECURITY_PASSWORD_HASH` is "
            'set to "%s"' % password_hash
        )

    h = hmac.new(encode_string(salt), encode_string(password), hashlib.sha512)
    return base64.b64encode(h.digest())


def verify_password(password, password_hash):
    password = get_hmac(password)
    salt = Config.PASSWORD_SALT.encode()
    return hmac.compare_digest(
        password_hash,
        password
    )


def hash_password(password):
    password = get_hmac(password)
    print(hashlib.sha512(password).hexdigest())
    return get_hmac(password)
