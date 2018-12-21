# -*- coding: utf-8 -*-
"""
    Securely hash and check passwords using PBKDF2.
    Use random salts to protect againt rainbow tables, many iterations against
    brute-force, and constant-time comparaison againt timing attacks.
    Keep parameters to the algorithm together with the hash so that we can
    change the parameters and keep older hashes working.
    See more details at http://exyr.org/2011/hashing-passwords/
    Author: Simon Sapin
    License: BSD
"""

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import hashlib
import hmac
from os import urandom
from base64 import b64encode
from struct import Struct
from operator import xor
from itertools import starmap


# Parameters to PBKDF2. Only affect new passwords.
SALT_LENGTH = 12
KEY_LENGTH = 24
HASH_FUNCTION = 'sha256'  # Must be in hashlib.
# Linear to the hashing time. Adjust to be high but take a reasonable
# amount of time on your server. Measure with:
# python -m timeit -s 'import passwords as p' 'p.make_hash("something")'
COST_FACTOR = 10000


# From https://github.com/mitsuhiko/python-pbkdf2
_pack_int = Struct('>I').pack


def ord3(arg):
    return ord(chr(arg))


def chr3(arg):
    return chr(arg).encode('latin-1')


def pbkdf2_bin(data, salt, iterations=1000, keylen=24, hashfunc=None):
    """Returns a binary digest for the PBKDF2 hash algorithm of `data`
    with the given `salt`.  It iterates `iterations` time and produces a
    key of `keylen` bytes.  By default SHA-1 is used as hash function,
    a different hashlib `hashfunc` can be provided.
    """
    hashfunc = hashfunc or hashlib.sha1
    mac = hmac.new(data, None, hashfunc)

    def _pseudorandom(x, mac=mac):
        h = mac.copy()
        if type(x) is str:
            x = bytes(x, "utf-8")
        h.update(x)
        return list(map(ord3, h.digest()))
    buf = []
    for block in range(1, -(-keylen // mac.digest_size) + 1):
        rv = u = _pseudorandom(salt + _pack_int(block))
        for i in range(iterations - 1):
            u = _pseudorandom(b''.join(map(chr3, u)))
            rv = starmap(xor, zip(rv, u))
        buf.extend(rv)
    return b''.join(map(chr3, buf))[:keylen]


def make_hash(password, salt=None):
    """Generate a random salt and return a new hash for the password."""
    if isinstance(password, str):
        password = password.encode('utf-8')
    if salt is None:
        salt = b64encode(urandom(SALT_LENGTH))
    return 'PBKDF2${}${}${}${}'.format(
        HASH_FUNCTION,
        COST_FACTOR,
        str(salt, 'utf-8'),
        str(b64encode(pbkdf2_bin(password, salt, COST_FACTOR, KEY_LENGTH,
                      getattr(hashlib, HASH_FUNCTION))), 'utf-8'))


class FilterModule(object):

    def filters(self):
        return {
            'mosquitto_hash': make_hash,
        }
