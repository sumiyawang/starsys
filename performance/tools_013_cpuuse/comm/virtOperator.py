"""
    Description :   lib virt operation
    created by  :   cloudyang, 2013/Nov/10
    Modified by :   samhuang 2013/Nov/12
    Node        :
"""

# -*- coding: utf-8 -*-

import os
import libvirt
import threading

_g_virlock = threading.Lock()


class VirtOperator:
    virt_conn = None
    virt_hyper = "unknow"

    def __init__(self, uri=None, readonly=True):
        self.__uri = uri
        self.__readonly = readonly
        if VirtOperator.virt_conn == None:
            try:
                _g_virlock.acquire()
                if VirtOperator.virt_conn == None:
                    self._getHypervisorType()
                    self.virt_conn = self._createVirtConnection(uri, readonly)
                else:
                    self.virt_conn = VirtOperator.virt_conn
            finally:
                _g_virlock.release()
        else:
            self.virt_conn = VirtOperator.virt_conn

    def _getHypervisorType(self):
        # hyperCmd = '''awk '/Booting .*virtualized kernel/{ str = tolower($0); if (match(str, "xen")){print "xen"} else if (match(str, "kvm")){print "kvm"} else {print "unknow"}}' /var/log/dmesg'''
        # self.virt_hyper = commands.getoutput(hyperCmd)
        if os.path.isdir('/sys/module/kvm'):
            VirtOperator.virt_hyper = 'kvm'
        else:
            VirtOperator.virt_hyper = 'xen'

    def _createVirtConnection(self, uri, readonly):
        if uri == None:
            if cmp(VirtOperator.virt_hyper, 'xen') == 0:
                realUrl = 'xen:///'
            elif cmp(VirtOperator.virt_hyper, 'kvm') == 0:
                realUrl = 'qemu:///system'
            else:
                realUrl = 'xen:///'  # default as xen
        else:
            realUrl = uri

        if readonly == True:
            VirtOperator.virt_conn = libvirt.openReadOnly(realUrl)
        else:
            VirtOperator.virt_conn = libvirt.open(realUrl)
        return VirtOperator.virt_conn

    def getHypervisor(self):
        return VirtOperator.virt_hyper

    def getActiveDomains(self):
        try:
            return [self.virt_conn.lookupByID(x) for x in self.virt_conn.listDomainsID() if x != 0]
        except libvirt.libvirtError, e:
            self.virt_conn = self._createVirtConnection(self.__uri, self.__readonly)
            raise Exception("libvirt connection reset, %s" % e)

    def getDefinedDomains(self):
        try:
            return [self.virt_conn.lookupByName(x) for x in self.virt_conn.listDefinedDomains()]
        except libvirt.libvirtError, e:
            self.virt_conn = self._createVirtConnection(self.__uri, self.__readonly)
            raise Exception("libvirt connection reset, %s" % e)

    def getAllDomains(self):
        return self.getActiveDomains() + self.getDefinedDomains()

    def lookupByName(self, instance_name):
        try:
            return self.virt_conn.lookupByName(instance_name)
        except libvirt.libvirtError, e:
            self.virt_conn = self._createVirtConnection(self.__uri, self.__readonly)
            raise Exception("libvirt connection reset, %s" % e)

    def lookupByID(self, instance_id):
        try:
            return self.virt_conn.lookupByID(instance_id)
        except libvirt.libvirtError, e:
            self.virt_conn = self._createVirtConnection(self.__uri, self.__readonly)
            raise Exception("libvirt connection reset, %s" % e)

    def lookupByUUID(self, instance_uuid):
        try:
            return self.virt_conn.lookupByUUIDString(instance_uuid)
        except libvirt.libvirtError, e:
            self.virt_conn = self._createVirtConnection(self.__uri, self.__readonly)
            raise Exception("libvirt connection reset, %s" % e)

    def lookupByUUIDString(self, uuid):
        try:
            return self.virt_conn.lookupByUUIDString(uuid)
        except libvirt.libvirtError, e:
            self.virt_conn = self._createVirtConnection(self.__uri, self.__readonly)
            raise Exception("libvirt connection reset, %s" % e)

    def getVersion(self):
        """Get current libvert version"""
        try:
            return self.virt_conn.getLibVersion()
        except libvirt.libvirtError, e:
            self.virt_conn = self._createVirtConnection(self.__uri, self.__readonly)
            raise Exception("libvirt connection reset, %s" % e)


if __name__ == "__main__":
    virtObj = VirtOperator()
    print virtObj.getHypervisor()
    print virtObj.getVersion()
    print virtObj.getActiveDomains()
