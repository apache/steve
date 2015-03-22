#!/usr/bin/env python
import json

responseCodes = {
    200: 'Okay',
    201: 'Created',
    206: 'Partial content',
    304: 'Not Modified',
    400: 'Bad Request',
    403: 'Access denied',
    404: 'Not Found',
    410: 'Gone',
    500: 'Server Error'
}

def respond(code, js):
    c = responseCodes[code] if code in responseCodes else "Unknown Response Code(?)"
    out = json.dumps(js, indent=4)
    print("Status: %u %s\r\nContent-Type: application/json\r\nContent-Length: %u\r\n" % (code, c, len(out)))
    print(out)
    
    
    