import os
import sys

#queue define
QUEUE_TO_DISPATCHER = 0x01
QUEUE_TO_EXECUTOR = 0x02

PLUGIN_CONFIG_PATH = None 


BIND_MODE_TCP = 0
BIND_MODE_UDP = 1
BIND_MODE_UNIX = 2

class ErrorCode(object):
    SUCC = 0x0
    MSG_TYPE_ERROR = 1000
    REQUEST_DECODE_ERROR = 1001
    HTTP_SEND_ERROR = 1002
    HTTP_RESPONSE_ERROR = 1003
    QUEUE_FULL_ERROR = 1004
    pass

#addtional path
def add_path():
    additional_path = [
                   "/../",
                   "/../comm/",
                   "/../plugin/base/",
                   "/../lib/",
                   "/../plugin/dispatcher/",
                   "/../plugin/collector/"
                   ]
    base_path = os.path.dirname(__file__) if __name__ != '__main__' else os.getcwd()
    for path in additional_path:
        ab_path = os.path.abspath(base_path + path)
        if ab_path not in sys.path:
            '''
                use our own lib first, then the system
            '''
            if path == "/../lib/":
                sys.path.insert(0, ab_path)
            else:
                sys.path.append(ab_path)
    
    global PLUGIN_CONFIG_PATH
    PLUGIN_CONFIG_PATH = os.path.abspath(base_path + '/../etc/plugin.ini')

add_path()
