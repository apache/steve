#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# ### TBD docco
#
#

import base64
import secrets

import passlib.hash  # note that .argon2 is proxy in this pkg
import passlib.utils  # for the RNG, to create Salt values

import cryptography.fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf import hkdf


# All salt values will be 16 bytes in length. After base64 encoding, they
# will be represented with 22 characters.
SALT_LEN = 16


def gen_salt() -> bytes:
    "Generate bytes to be used as a salt, for hashing."
    return passlib.utils.getrandbytes(passlib.utils.rng, SALT_LEN)


def gen_opened_key(edata: bytes, salt: bytes) -> bytes:
    "Generate the OpenedKey for this election."
    return _hash(edata, salt)


def gen_vote_token(opened_key: bytes, pid: str, iid: str, salt: bytes) -> bytes:
    "Generate a person or issue token."
    return _hash(opened_key + pid.encode() + iid.encode(), salt)


def _b64_vote_key(vote_token: bytes, salt: bytes) -> str:
    "Key-stretch the vote_token. (ref: PBKDF)"

    ### still using Fernet now, but will switch soon. Leaving comments.
    keymaker = hkdf.HKDF(
        algorithm=hashes.SHA256(),
        length=32,  # 32-byte key for XChaCha20-Poly1305
        salt=salt,
        info=b"xchacha20_key"
    )
    vote_key = keymaker.derive(vote_token)
    return base64.urlsafe_b64encode(vote_key)


def create_vote(vote_token: bytes, salt: bytes, votestring: str) -> bytes:
    "Encrypt VOTESTRING using the VOTE_TOKEN and SALT."

    b64key = _b64_vote_key(vote_token, salt)
    f = cryptography.fernet.Fernet(b64key)
    return f.encrypt(votestring.encode())


def decrypt_votestring(vote_token: bytes,
                       salt: bytes,
                       ciphertext: bytes) -> str:
    "Decrypt CIPHERTEXT into a VOTESTRING."

    b64key = _b64_vote_key(vote_token, salt)
    f = cryptography.fernet.Fernet(b64key)
    return f.decrypt(ciphertext).decode()


def _hash(data: bytes, salt: bytes) -> bytes:
    "Apply our desired hashing function."
    ph = passlib.hash.argon2.using(type='d', salt=salt)
    h = ph.hash(data)
    return base64.standard_b64decode(h.split('$')[-1] + '==')


def shuffle(x):
    "Ensure we use the strongest RNG available for shuffling."

    # Implements the Fisher-Yates shuffle, using secrets.randbelow() for
    # cryptographically-safe (aka unpredictable) shuffling of elements.

    # Count backwards, "fixing" a chosen element into place.
    for i in range(len(x)-1, 0, -1):
        # Choose element to fix from remaining pool.
        j = secrets.randbelow(i + 1)

        # Swap them in-place.
        x[i], x[j] = x[j], x[i]

    # We shuffled in-place, but also return for funsies.
    return x


def create_id():
    "Create a standard ID value."

    # Use 10 hex characters for the ID
    return secrets.token_hex(5)  # 5 bytes
