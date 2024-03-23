import cutils, constant
import socket, json, struct, time
from base_client import BaseClient
import constant


class CloudClient(BaseClient):
    MSG_ALARM = 0x01
    MSG_USER_DATA = 0x02
    MAGIC_WORD = 0x8f6f6d72
    
    def __init__(self, reactor, sock, addr, event, logger, router):
        super(CloudClient, self).__init__(reactor, sock, event, logger, router)
    
    def decode(self, buffer):
        if len(buffer) < 12:
            return 0
        magic, type, data_len, reserved = struct.unpack('Ihhi', buffer[0:12])
        if data_len <= 12:
            return -1
        if magic != self.MAGIC_WORD:
            return -2
        if len(buffer) >= data_len:
            data = buffer[12:data_len]
            self.logger().info("recv type : %d \t msg : %s" % (type, data))
            if type == self.MSG_ALARM:
                self.process_alarm_msg(data)
            elif type == self.MSG_USER_DATA:
                self.process_user_data(data)
            else:
                self.logger().error("invalid msg type : %d " % type)
                return -3
        
        return data_len
    
    def process_alarm_msg(self, data):
        try:
            json_data = json.loads(data)
            host_ip = cutils.local_ip()
            json_data["localip"] = host_ip
            json_data["localtime"] = int(time.time())
            json_data["clientKey"] = cutils.get_client_key()
            json_str = json.dumps(json_data)
            # send_data = { 'sender':'alarm_sender', 'datas': json_str }
            # self.router().route(constant.QUEUE_TO_DISPATCHER, send_data)
            from alarm_sender import AlarmSender
            sender = AlarmSender()
            sender.init()
            (retcode, retinfo) = sender.send_data(json_str)
        except Exception, e:
            import traceback
            self.logger().error("parse json failed, data : %s\n%s", data, traceback.format_exc())
            retcode = constant.ErrorCode.REQUEST_DECODE_ERROR
            retinfo = 'parse json failed'
        
        str_info = json.dumps({"retCode": retcode, "retMsg": retinfo})
        send_data = struct.pack('i', len(str_info))
        send_data += str_info
        self.send_response(send_data)
    
    def process_user_data(self, data):
        # use define msg  , not finished yet
        pass
