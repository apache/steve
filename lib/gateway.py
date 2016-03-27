#!/usr/bin/env python


import os

def uid():
    """Sample user gateway function. Returns the basic auth username as UID"""
    return os.environ['REMOTE_USER'] if 'REMOTE_USER' in os.environ else None
