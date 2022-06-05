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
import random

import passlib.hash  # note that .argon2 is proxy in this pkg
import passlib.utils  # for the RNG, to create Salt values

import cryptography.fernet

# All salt values will be 16 bytes in length. After base64 encoding, they
# will be represented with 22 characters.
SALT_LEN = 16


def gen_salt() -> bytes:
    "Generate bytes to be used as a salt, for hashing."
    return passlib.utils.getrandbytes(passlib.utils.rng, SALT_LEN)


def gen_opened_key(edata: bytes, salt: bytes) -> bytes:
    "Generate the OpenedKey for this election."
    return _hash(edata, salt)


def gen_token(opened_key: bytes, value: str, salt: bytes) -> bytes:
    "Generate a person or issue token."
    return _hash(opened_key + value.encode(), salt)


### fix return type, to be a tuple
def create_vote(person_token: bytes,
                issue_token: bytes,
                votestring: str) -> bytes:
    "Create a vote tuple, to record the VOTESTRING."
    salt = gen_salt()
    key = _hash(person_token + issue_token, salt)
    b64key = base64.urlsafe_b64encode(key)
    f = cryptography.fernet.Fernet(b64key)
    return salt, f.encrypt(votestring.encode())


def decrypt_votestring(person_token: bytes,
                       issue_token: bytes,
                       salt: bytes,
                       token: bytes) -> str:
    "Decrypt TOKEN into a VOTESTRING."
    key = _hash(person_token + issue_token, salt)
    b64key = base64.urlsafe_b64encode(key)
    f = cryptography.fernet.Fernet(b64key)
    return f.decrypt(token).decode()


def _hash(data: bytes, salt: bytes) -> bytes:
    "Apply our desired hashing function."
    ph = passlib.hash.argon2.using(type='d', salt=salt)
    h = ph.hash(data)
    return base64.standard_b64decode(h.split('$')[-1] + '==')


def shuffle(x):
    "Ensure we use the strongest RNG available for shuffling."
    return random.shuffle(x, passlib.utils.rng.random)
