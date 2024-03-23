from epoll_reactor import EpollReactor
from event_handler import EventHandler
import select

class Acceptor(EventHandler):
    def __init__(self, reactor, sock, client_class, logger, router):
        super(Acceptor, self).__init__(reactor, sock, select.EPOLLIN)
        self.__sock = sock
        self.__client_class = client_class
        self.__logger = logger
        self.__router = router
        
    def handle_input(self):
        conn, addr = self.__sock.accept()
        conn.setblocking(0)
        self.__client_class(self.reactor(), conn, addr, select.EPOLLIN, self.__logger, self.__router)
        return 0
        
    def handle_output(self):
        return 0
