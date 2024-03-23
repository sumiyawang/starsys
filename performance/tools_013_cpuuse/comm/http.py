#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
File: common.http.py
Created on 2015-09-06

@module: common.http
@author: daniclin
@summary: common http send and recv util

"""

import json
import urllib
import urllib2
import time

__all__ = ['send_recv']


class CHttp(object):
    def __init__(self, logger=None):
        self._url = None
        self._timeout = None
        self._conn = None
        self.logger = logger

    def __del__(self):
        self.destroy()

    def init(self, url, timeout):
        if (not isinstance(url, (str, unicode)) or
                not isinstance(timeout, (int, long)) or
                not url or
                not timeout):
            raise Exception('[url or timeout] is invalid')
        self._url = url
        self._timeout = timeout

    def destroy(self):
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def get(self, data):
        try:
            if not isinstance(data, dict):
                str_data = urllib.quote_plus(urllib.urlencode(data))
            else:
                str_data = data
            urlstr = '%s?%s' % (self._url, str_data)
            self._conn = urllib2.urlopen(urlstr, timeout=self._timeout)
            result = self._conn.read()
            code = self._conn.getcode()
            self.destroy()
            if (code / 100) == 2:
                return result
            else:
                return None
        except Exception as e:
            self.logger.error('http get occur some error: %s' % e)
            return None

    def post(self, data):
        try:
            self._conn = urllib2.urlopen(self._url, data, timeout=self._timeout)
            result = self._conn.read()
            code = self._conn.getcode()
            self.destroy()
            if (code / 100) == 2:
                return result
            else:
                return None
        except Exception as e:
            self.logger.error('http post occur some error: %s' % e)
            return None


def send_recv(url, req, logger, method='post', timeout=None):
    if timeout is None:
        timeout = 30
    beg_time = time.time()
    httpreq = CHttp(logger=logger)
    httpreq.init(url, timeout)
    if method in ('POST', 'post'):
        if not isinstance(req, basestring):
            req = json.dumps(req)
        respose = httpreq.post(req)
    else:
        respose = httpreq.get(req)
    cost_time = time.time() - beg_time
    if not respose:
        # info = 'url[%s], http req[%s] error, return None, cost[%s]' % (url, str(req), str(cost_time))
        info = "curl -d '{0}' {1}\nrsp: None, cost: {2}".format(req, url, cost_time)
        logger.error(info)
        return None

    # log_info('url[%s], http req[%s]\r\nrsp[%s], cost[%s]' % (url, str(req), str(respose), str(cost_time)))
    logger.info("curl -d '{0}' {1}\nrsp: {2}, cost: {3}".format(req, url, respose, cost_time))
    return json.loads(respose)
