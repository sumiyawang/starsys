class QueueRouter(object):
    ROUTE_TO_EXECUTOR = 0x01
    ROUTE_TO_DISPATCHER = 0x02
    
    def __init__(self):
        self.__queue_dict = {}
    
    def add_queue(self, name, q):
        self.__queue_dict[name] = q
    
    def get_queue(self, name):
        if self.__queue_dict.has_key(name):
            return self.__queue_dict.get(name)
        else:
            return None
    
    def route(self, name, data):
        queue = self.get_queue(name)
        if queue is not None:
            queue.put(data)
        else:
            raise Exception('no router for \'%s\'' % name)
