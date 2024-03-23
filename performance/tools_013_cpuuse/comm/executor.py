from base_process import BaseProcess
import constant
from module_loader import ModuleLoader
from apscheduler.scheduler import Scheduler
from plugin_base import BaseCollector
import copy
from datetime import datetime, timedelta
from Queue import Empty

class Executor(BaseProcess):
    def __init__(self, config_path, router):
        super(Executor, self).__init__(config_path, self.__class__.__name__.lower())
        self.__router = router
        self.__msg_queue = router.get_queue(constant.QUEUE_TO_EXECUTOR)
        module_path = self.get_config('module_path')
        load_dir = self.get_config('module_dir').replace(' ','').split(',')
        self.__module_loader = ModuleLoader(module_path, load_dir)
        #self.__module_loader.load('do_collect', self)
        self.__jobs = { }
        self.load_modules()
      
    def load_modules(self):
        try:
            self.__module_loader.load_by_class(BaseCollector, self)
        except Exception,e:
            self.logger().error(e)
        self.__module_dict = self.__module_loader.get_modules()

    def add_jobs(self):
        curr_time = datetime.now()
        index = 0
        for collector_name in self.__module_dict.keys():
            if not self.__jobs.has_key(collector_name):
                collector = self.__module_dict[collector_name]
                start_date = curr_time + timedelta(seconds = collector.frequency() + index)
                index += 1
                job = self.__sched.add_interval_job(collector.collect, seconds = collector.frequency(), start_date = start_date)
                self.__jobs[collector_name] = job
                self.logger().info("%s add to scheduler." % collector_name)

    def run_scheduler(self):
        self.__sched = Scheduler()
        self.add_jobs()
        self.__sched.start()
    
    def msg_wait(self):
        try:
            msg =  self.__msg_queue.get(timeout = 5)
            if msg.has_key('collector') and msg.has_key('method'):
                collector_name = msg.get('collector')
                if self.__module_dict.has_key(collector_name):
                    collector = self.__module_dict.get(collector_name)
                    method_name = msg.get('method')
                    
                    if hasattr(collector, method_name):
                        method = getattr(collector, method_name)
                        data = method()
                        try:
                            from mr_sender import MRSender
                            sender = MRSender(self.logger())
                            sender.init()
                            ret = sender.send_one_data(8, data, True)
                            self.logger().warn('execute collector : %s , ret : %d' % (collector_name, ret))
                        except Exception,e:
                            import traceback
                            self.logger().error('execute collector failed, %s' % traceback.format_exc().replace('\n','\\n'))
                    else:
                        self.logger().error('collector %s has no method : %s' % (collector_name, method_name))
                else:
                    self.logger().error("collector %s isn't loaded" % collector_name)
        except Empty as e:
            pass

    def run(self):
        self.run_scheduler()
        while True:
            try:
                self.msg_wait()
                self.load_modules()
                self.add_jobs()
            except Exception,e:
                import traceback
                self.logger().error(traceback.format_exc());
                                    
    def put_data(self, msg):
        self.logger().info('put msg : %s to dispatcher' % msg)
        self.__router.route(constant.QUEUE_TO_DISPATCHER, copy.deepcopy(msg))
