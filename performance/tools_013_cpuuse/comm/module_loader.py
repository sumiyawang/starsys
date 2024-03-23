#!/usr/bin/env python
#coding=utf-8
import os
import sys
import inspect
import traceback
'''
    class for install plug-ins for dispatcher or executor
'''
class ModuleLoader(object):
    FILT_BY_METHOD = 1
    FILT_BY_CLASS = 2
    def __init__(self, module_path, load_dir = None):
        self.__module_path = os.getcwd() + '/' + module_path
        self.__module_dict = { }
        self.__load_dir = load_dir
        if self.__module_path not in sys.path:
            sys.path.append(self.__module_path)
    '''
        load plug-ins from configure path, including the sub-path
        the class that will be loaded must has the particular method in parameter 'methods'
    ''' 
    def load(self, methods = None, args = None):
        self.__load(self.__module_path, ModuleLoader.FILT_BY_METHOD, methods, args)
        for file_node in os.listdir(self.__module_path):
            dir_path = self.__module_path + '/' + file_node
            if os.path.isdir(dir_path):
                if (self.__load_dir is not None) and (file_node not in self.__load_dir):
                    continue
                self.__load(dir_path, ModuleLoader.FILT_BY_METHOD, methods, args, file_node)
                
    '''
        load plug-ins from configure path, including the sub-path
        the class that will be loaded must be inherited from particular base-class by parameter 'base-class'
    '''             
    def load_by_class(self, base_class = None, args = None):
        self.__load(self.__module_path, ModuleLoader.FILT_BY_CLASS, base_class, args)
        for file_node in os.listdir(self.__module_path):
            dir_path = self.__module_path + '/' + file_node
            if os.path.isdir(dir_path):
                if (self.__load_dir is not None) and (file_node not in self.__load_dir):
                    continue
                self.__load(dir_path, ModuleLoader.FILT_BY_CLASS,  base_class, args, file_node)
    
    def __load(self, path, filt_mode, filt_name, args, prefix = ''):
        for file_node in os.listdir(path):
            full_path = path + '/' + file_node
            if os.path.isfile(full_path):
                (name, ext) = os.path.splitext(file_node)
                if name != '__init__' and ext == '.py':
                    try:
                        if len(prefix)>0:
                            import_name = '%s.%s' % (prefix,  name)
                        else:
                            import_name = name
                        if self.__module_dict.has_key(import_name):
                            continue
                        module = __import__(import_name, globals(), locals(), [ name ])
                        for m in dir(module):
                            fun = getattr(module, m)
                            if ((inspect.isclass(fun) and not inspect.isabstract(fun))
                                and ((filt_mode == ModuleLoader.FILT_BY_METHOD and self.method_filter(fun, filt_name)) 
                                or (filt_mode == ModuleLoader.FILT_BY_CLASS and issubclass(fun, filt_name) and fun != filt_name))):
                                try:
                                    self.__module_dict[import_name] = fun(args)
                                except Exception,e:
                                    traceback.print_exc()
                                    continue
                    except Exception, e:
                        '''这里对加载失败的插件做忽略处理'''
                        traceback.print_exc()
                        #raise Exception(traceback.format_exc().replace('\n','\\n'))
                        continue
                        
    
    def method_filter(self, module_name, method_list):
        if method_list is None:
            return True
        if not isinstance(method_list, list):
            method_list = [ method_list ]
        for method_name in method_list:
            if hasattr(module_name, method_name):
                return True
        return False

    def get_modules(self):
        return self.__module_dict

if __name__ == '__main__':
    import constant
    loader = ModuleLoader('../plugin/collector/', ['host'])
    from plugin_base import BaseCollector,BaseSender
    loader.load_by_class(BaseCollector)
    #loader.load('do_collect')
    print loader.get_modules()
                
