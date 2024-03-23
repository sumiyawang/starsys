#coding=utf-8
import constant
from base_process import BaseProcess
from module_loader import ModuleLoader
from plugin_base import BaseSender
import threading
import Queue, time
'''
    modified by cloudyang, 2014.12.02
            将发送进程由单线程改为多线程，每个dispather_moudle单独为一个线程，防止相互影响
'''
WARN_DELAY = 1000

def dispather_run(sender_name, sender_obj, msg_queue, logger):
    logger.info("sender[%s] thread started." % sender_name)
    while True:
        try:
            data = msg_queue.get()
            start_time = time.time()*1000
            sender_obj.send_data(data)
            end_time = time.time()*1000
            consume_time = end_time - start_time
            if consume_time > WARN_DELAY:
                logger.warn("[DELAY]dispather_module : %s spent time > %d" % (sender_name, WARN_DELAY)) 
        except Exception as e:
            import traceback
            err = traceback.format_exc().replace('\n','\\n')
            logger.error(err)

def watchdog_fun(threadList,logger,router,objlist):
    logger.info("dispatcher watchdog run--")
    while True:
        try:
            for sender in threadList.keys():
                if not threadList[sender].is_alive():
                    logger.error("%s thread dead,just restart it and clear old queue,queue size: %d" % (sender,router[sender].qsize()))
                    new_thread = threading.Thread(target = dispather_run, args = (sender, objlist[sender], router[sender], logger), name = sender)
                    router[sender].queue.clear()
                    new_thread.start()
                    threadList[sender] = new_thread

            time.sleep(10)

        except Exception as e:
            import traceback
            logger.error(traceback.format_exer.warn())
            pass

class Dispatcher(BaseProcess):
    def __init__(self, config_path, router):
        super(Dispatcher, self).__init__(config_path, self.__class__.__name__.lower())
        self.__msg_queue = router.get_queue(constant.QUEUE_TO_DISPATCHER)

        module_path = self.get_config('module_path')
        self.__module_loader = ModuleLoader(module_path)
        self.__module_loader.load_by_class(BaseSender, self.logger())
        self.__module_dict = self.__module_loader.get_modules()
        self.__thread_list = {}
        self.__obj_list = {}
        self.__module_router = { }
        self.init_dispather_thread()

    def init_dispather_thread(self):
        try:
            for (sender, sender_obj) in self.__module_dict.items():
                q = Queue.Queue()
                dispather_thread = threading.Thread(target = dispather_run, args = (sender, sender_obj, q, self.logger()), name = sender)
                self.__module_router[sender] = q
                self.__obj_list[sender] = sender_obj
                self.__thread_list[sender] = dispather_thread
                dispather_thread.start()
            #start a watchdog to monitor Dispatcher threads
            watchdog = threading.Thread(target = watchdog_fun,args = (self.__thread_list,self.logger(),self.__module_router,self.__obj_list),name = "watchdog")
            watchdog.start()

        except Exception,e:
            self.logger().error(e)

    def run(self):
        while True:
            try:
                data = self.__msg_queue.get()
                self.logger().debug('get msg : %s from queue' % data)
                if isinstance(data, list):
                    for one_data in data:
                        self.send_one_data(one_data)
                else:
                    self.send_one_data(data)
            except Exception,e:
                import traceback
                self.logger().error(traceback.format_exc());

    def send_one_data(self, data):
        if data.has_key('sender') and data.has_key('datas'):
            module_name = data.get('sender')
            if self.__module_router.has_key(module_name):
                sender_queue = self.__module_router.get(module_name)
                for one_data in data['datas']:
                    sender_queue.put(one_data)
            else:
                self.logger().error("no sender module named '%s'" % module_name)
        else:
            self.logger().error("invalid data format , %s" % data)
