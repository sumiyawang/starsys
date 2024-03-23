import socket, json, struct, time
from base_client import BaseClient
import constant


class MonitorClient(BaseClient):
    def __init__(self, reactor, sock, addr, event, logger, router):
        super(MonitorClient, self).__init__(reactor, sock, event, logger, router)
    
    def execute_command(self, json_data):
        ARISE_COLLECT = 0x01
        if json_data.has_key("cmd"):
            cmd = json_data.get("cmd")
            self.logger().info("valid command : %s" % json_data)
            if cmd == ARISE_COLLECT:
                msg_to_executor = {'collector': 'host.vsHostBaseInfo', 'method': 'get_child_state'}
                self.router().route(constant.QUEUE_TO_EXECUTOR, msg_to_executor)
        else:
            self.logger().error("command : %s has no key 'cmd'" % json_data)
    
    def decode(self, buffer):
        try:
            json_data = json.loads(buffer)
            self.execute_command(json_data)
            data_len = len(buffer)
            return data_len
        except Exception, e:
            self.logger().error('decode error');
            return -1;
