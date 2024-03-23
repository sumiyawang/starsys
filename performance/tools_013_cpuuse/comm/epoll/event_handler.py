#!/usr/bin/env python
# -*- coding: utf-8 -*-

class EventHandler(object):
    def __init__(self, reactor, sock, event):
        self.__recv_buffer = ''
        self.__send_buffer = ''
        self.__fd = sock.fileno()
        self.__sock = sock
        self.__reactor = reactor
        self.__mask = 0
        reactor.attach(self.__fd, self, event)
    
    def close_sock(self):
        self.__sock.close()
        
    def fd(self):
        return self.__fd

    def reactor(self):
        return self.__reactor
        
    def handle_input(self):
        return 0
    
    def handle_output(self):
        return 0
    
    def handle_error(self):
        self.__reactor.put_del_list(self)
        return -1
    
    def handle_hangup(self):
        self.__reactor.put_del_list(self)
        return -1
    
    def enable_input(self):
        self.enable_event(select.EPOLLIN)
    
    def enable_output(self):
        self.enable_event(select.EPOLLOUT)
    
    def disable_input(self):
        self.disable_event(select.EPOLLIN)    
    
    def disable_output(self):
        self.disable_event(select.EPOLLOUT)
    
    def enable_event(self, event):
        if self.__mask & event == 0:
            self.__mask |= event
            self.__reactor.modify(self.__fd, self.__mask)
    
    def disable_event(self, event):
        if self.__mask & event != 0:
            self.__mask &= ~event
            self.__reactor.modify(self.__fd, self.__mask) 
