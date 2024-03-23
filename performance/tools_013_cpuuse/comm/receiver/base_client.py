from epoll.event_handler import EventHandler
import cutils, constant
import socket,json,struct,time

class BaseClient(EventHandler):
    def __init__(self, reactor, sock, event, logger, router):
        super(BaseClient, self).__init__(reactor, sock, event)
        self.__recv_buffer = ''
        self.__send_buffer = ''
        self.__sock = sock
        self.__logger = logger
        self.__router = router
        
    def logger(self):
        return self.__logger

    def router(self):
        return self.__router
        
    def sock(self):
        return self.__sock

    def handle_input(self):
        try:
            recv_data = self.__sock.recv(4096)
            if len(recv_data) == 0:
                self.logger().warn("client has closed connection.")
                self.reactor().put_del_list(self)
                return -1
    
            if recv_data:
                self.__recv_buffer += recv_data
                ret = self.decode(self.__recv_buffer)
                if ret > 0:
                    self.__recv_buffer = self.__recv_buffer[ret:]
                elif ret == 0: #packet not complete 
                    pass
                else:
                    self.logger().error("decode msg failed, ret = %d" % ret)
                    self.reactor().put_del_list(self)
                    return -1
            return 0
                
        except socket.error,e:
            self.logger().error("recv error,  %s" % e)
            self.reactor().put_del_list(self)
            return -1
        
    def handle_output(self):
        try:
            send_length = self.__sock.send(self.__send_buffer)
            if send_length == len(self.__send_buffer):
                self.disable_output()
            self.__send_buffer = self.__send_buffer[send_length:]
                
        except socket.error,e:
            self.logger().error("handle outpout error, %s" %e)
            self.reactor().put_del_list(self)
            
    def send_response(self, send_data):
        try:
            send_length = self.__sock.send(send_data)
            if send_length < len(send_data):
                self.enable_output()
            self.__send_buffer = send_data[send_length:]
        except socket.error,e: 
            self.logger().error("send_response error %s" % e)
            self.reactor().put_del_list(self)
