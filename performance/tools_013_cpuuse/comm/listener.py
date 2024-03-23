import socket,json,select,os,time,struct
import constant,cutils
from base_process import BaseProcess
from receiver.cloud_agent import CloudClient
from receiver.monitor_agent import MonitorClient
from epoll.epoll_reactor import EpollReactor
from epoll.acceptor import Acceptor

class Listener(BaseProcess):
    def __init__(self, config_path, router):
        super(Listener, self).__init__(config_path, self.__class__.__name__.lower())
        self.__router = router
        self.__config_path = config_path
        
    def bind_sock(self):
        bind_host = self.get_config('bind_host')
        bind_mode = int(self.get_config('bind_mode'))
        listen_sock = None
        if bind_mode == constant.BIND_MODE_TCP or bind_mode == constant.BIND_MODE_UDP:
            listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
            bind_addr = (bind_host, int(self.get_config('bind_port')))
        elif bind_mode == constant.BIND_MODE_UNIX:
            listen_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM, 0)
            bind_addr = bind_host
            if os.path.exists(bind_addr):
                os.unlink(bind_addr)
        else:
            self.logger().error("invalid bind mode %d", bind_mode)
            raise Exception("invalid bind mode")

        listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listen_sock.bind(bind_addr)
        listen_sock.listen(1024)
        
        reactor = EpollReactor()
        agent_name = cutils.get_agent_name(self.__config_path)
        if agent_name == "cloud_agent":
            Client = CloudClient
        else:
            Client = MonitorClient
            
        self.logger().info('listener bind on : %s , use \'%s\' mode' % (repr(bind_addr), agent_name))
        
        acceptor = Acceptor(reactor, listen_sock, Client, self.logger(), self.__router)
        return reactor
        
    def run(self):
        reactor = self.bind_sock()
        reactor.run()
