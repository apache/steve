import hashlib, json, random, os, sys, time
from __main__ import homedir, config
import cgi


xform = cgi.FieldStorage();

def getvalue(key):
    val = xform.getvalue(key)
    if val:
        return val.replace("<", "&lt;")
    