#!/usr/bin/env python

import os

def uid():
    return os.environ['REMOTE_USER'] if 'REMOTE_USER' in os.environ else None
