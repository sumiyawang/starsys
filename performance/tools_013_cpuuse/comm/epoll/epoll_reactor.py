#!/usr/bin/env python
# -*- coding: utf-8 -*-

import socket
import select
import errno

class EpollReactor(object):
    
    def __init__(self):
        #super(EpollReactor,self).__init_()
        self.__epoll_fd = select.epoll()
        self.__handlers = {}
        self.__run_flag = True
        self.__del_list = []
        self.__routine_task = []
        
    def __del__(self):
        self.__epoll_fd.close()
        
    def run(self):
        while self.__run_flag:
            epoll_list = self.__epoll_fd.poll(0.05)
            for fd, events in epoll_list:
                if not self.__handlers.has_key(fd):
                    continue
                event_handler = self.__handlers.get(fd)
                if select.EPOLLIN & events:
                    ret = event_handler.handle_input()
                    if ret != 0:
                        continue
                elif select.EPOLLOUT & events:
                    ret = event_handler.handle_output()
                    if ret != 0:
                        continue
                elif select.EPOLLHUP & events:
                    ret = event_handler.handle_error()
                    if ret != 0:
                        continue
            self.del_invalid_handler()
            self.run_routine_task()
    
    
    def register_routine_task(self, callback, args = None):
        self.__routine_task.append((callback, args))
    
    def run_routine_task(self):
        for (callback, args) in self.__routine_task:
            callback(args)
    
    def del_invalid_handler(self):
        for handler in self.__del_list:
            self.detach(handler.fd())
            handler.close_sock()
        self.__del_list = []

    def put_del_list(self, event_handler):
        self.__del_list.append(event_handler)
        
    def stop(self):
        self._run_flag = False
        
    def attach(self, fd, event_handler, event):
        self.__epoll_fd.register(fd, event)
        self.__handlers[fd] = event_handler
    
    def detach(self, fd):
        self.__epoll_fd.unregister(fd)
        if self.__handlers.has_key(fd):
            self.__handlers.pop(fd)
            
    def modify(self, fd, event):
        self.__epoll_fd.modify(fd, event)
        
        
        
