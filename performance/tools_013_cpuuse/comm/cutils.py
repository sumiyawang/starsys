# encoding=utf-8
# common functions
import ConfigParser
import logging
import sys
import socket
import commands
import subprocess, datetime, os, time, signal
from urlparse import *
import re

def get_agent_name(config_path):
    config = ConfigParser.ConfigParser()
    config.read(config_path)
    return config.get('name', 'agent_name')


def get_agent_version(config_path):
    config = ConfigParser.ConfigParser()
    config.read(config_path)
    return config.get('name', 'agent_version')


def generate_config(config_path, section_name):
    config = ConfigParser.ConfigParser()
    config.read(config_path)
    config_dict = {}
    if config.has_section(section_name):
        for option_pair in config.items(section_name):
            config_dict[option_pair[0]] = option_pair[1]
    return config_dict


def console_logger():
    logger = logging.getLogger()
    logger.addHandler(logging.StreamHandler(sys.stdout))
    logger.setLevel(logging.DEBUG)
    return logger


_local_ip = ''


def local_ip():
    """Get local ip """
    global _local_ip
    if len(_local_ip) > 0:
        return _local_ip
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(('172.0.0.1', 80))
        _local_ip = sock.getsockname()[0]
    except Exception:
        getIpCmd = "ip route |grep -v eth0|awk '/src/{print $NF}'"
        _local_ip = commands.getoutput(getIpCmd).split("\n")[0]
    return _local_ip


_client_key = ''


def get_client_key():
    CLIENT_KEY_PATH = '/var/lib/tencent/config/clientKey.ini'
    global _client_key
    if len(_client_key) > 0:
        return _client_key
    try:
        if os.path.isfile(CLIENT_KEY_PATH):
            key_file = open(CLIENT_KEY_PATH, "r")
            lines = key_file.readlines()
            for line in lines:
                if line.startswith("clientKey") and line.find('=') > 0:
                    _client_key = line.split('=')[1].strip()
                    break
            key_file.close()
        else:
            import urllib2, json, time
            import constant
            
            config = generate_config(constant.PLUGIN_CONFIG_PATH, 'UpdateServer')
            with open('/etc/uuid', 'r') as f:
                uuid = f.read().split('=')[1].replace('"', '').replace('\'', '').strip()
            req = {
                "version": "v1.0",
                "caller": "agent",
                "password": "",
                "callee": "autoupdate",
                "eventId": 101,
                "timestamp": time.time(),
                'interface': {
                    "interfaceName": "GetClientKey",
                    "para": {
                        "uuid": uuid
                    }
                }
            }
            http_ret = urllib2.urlopen(config['update_url'], json.dumps(req), float(config['update_timeout']))
            response = http_ret.read()
            json_resp = json.loads(response)
            retcode = int(json_resp["returnCode"])
            if retcode != 0:
                print json_resp["returnMsg"]
            else:
                _client_key = json_resp["returnData"]["clientKey"]
                dir, file = os.path.split(CLIENT_KEY_PATH)
                if not os.path.exists(dir):
                    os.makedirs(dir)
                with open(CLIENT_KEY_PATH, "w") as f:
                    str = 'clientKey=' + _client_key
                    f.writelines(str)
    
    except Exception, e:
        print e
    return _client_key


class CommUtils:
    @staticmethod
    def ExecuteCmd(cmd):
        (status, output) = commands.getstatusoutput(cmd)
        if status == 0:
            return output
        return ""
    
    @staticmethod
    def ExecuteTimeoutCommand(command, timeout):
        """call shell-command and either return its output or kill it
        if it doesn't normally exit within timeout seconds and return None"""
        start = datetime.datetime.now()
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        while process.poll() is None:
            time.sleep(0.1)
            now = datetime.datetime.now()
            if (now - start).seconds > timeout:
                # os.kill(process.pid, signal.SIGKILL)
                # os.waitpid(-1, os.WNOHANG)
                '''modified by cloudyang 2014.07.15
                    fix for the fd-leak bug in subprocess module in python 2.6
                    hope it works'''
                process.kill()
                process.wait()
                return ""
        return process.stdout.read()
    
    @staticmethod
    def GetBlockDevices():
        try:
            f = open('/proc/partitions', 'r')
            l = f.readlines()
        except Exception, e:
            return
        n = 0
        res = []
        for x in l:
            n += 1
            if n <= 2:
                continue
            arr = x.split()
            chk_name = "/sys/class/block/" + arr[3]
            if os.path.exists(os.path.realpath(chk_name)):
                try_path = chk_name + "/dm/name"
                try:
                    f2 = open(try_path)
                    best_name = "/dev/mapper/" + f2.read()[0:-1]
                    f2.close()
                except:
                    best_name = "/dev/" + arr[3]
                res.append(best_name)
        f.close()
        return res
    
    @staticmethod
    # add by cloudyang, 2016.01.07
    # 判断该母机是否为vpc母机，判断方法是由网络侧的joeyhe提供，若该命令返回空则不是vpc母机，否则为vpc母机
    # 若命令执行失败，则返回-1(不确定)，执行成功，返回0(非vpc), 1(vpc）
    def GetVPCFlag():
        flag = -1
        host_conf = "/etc/virt/host.conf"
        cmd = cmd_ret = ""
        try:
            if (os.path.exists(host_conf) is True):
                cmd = "sed '/vpc/!d' %s |cut -d '=' -f 2" % host_conf
                cmd_ret = CommUtils.ExecuteTimeoutCommand(cmd, 3)
            if ((os.path.exists(host_conf) is True) and (cmd_ret != "")):
                flag = int(cmd_ret)
            else:
                cmd = "uname -r |grep -i VPC"
                cmd_ret = CommUtils.ExecuteTimeoutCommand(cmd, 3)
                if len(cmd_ret) > 0:
                    flag = 1
                else:
                    flag = 0
        except Exception, e:
            print e
            pass
        return flag

    @staticmethod
    # Get the name of the guest from the qemu cmdline.
    # KVM 1.0/2.0:  qemu-system-x86_64 -name UUID -S ...
    # KVM 3.0:  qemu-system-x86_64 -name guest=UUID,debug-threads=on -S ...
    def GetNameFromCmdline(cmdline):
        start = cmdline.find('guest=')
        end = cmdline.find(',')
        if start >= 0:
            if end >= 0:
                name = cmdline[start+6:end]
            else:
                name = cmdline[start+6:]
        else:
            name = cmdline
        return name

    @staticmethod
    def get_kvm_version():
        version = 0
        if not os.path.exists("/sys/module/kvm"):
            return version

        cmd = "uname -r |awk -F'-' '{print $1}'"
        output = ''
        try:
            output = CommUtils.ExecuteTimeoutCommand(cmd, 3)
            if len(output) == 0:
                return version

            if "2.6.32" in output:
                version = 1
            elif "3.10.83" in output:
                version = 2
            elif "3.10.0" in output:
                version = 3
        except Exception as e:
            print e

        return version

    @staticmethod
    def dns_parse(url):
        try:
            parse_url = urlparse(url)
            domain = parse_url.netloc
            ip = socket.gethostbyname(domain)
            pattern = "^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$"
            if not re.match(pattern, ip):
                return url
            return url.replace(domain,ip)
        except Exception, e:
            return url

    @staticmethod
    def server_parse(server):
        try:
            ip = socket.gethostbyname(server)
            pattern = "^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$"
            if not re.match(pattern, ip):
                return server
            return ip
        except Exception, e:
            return server

if "__main__" == __name__:
    print CommUtils.GetVPCFlag()
