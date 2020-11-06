#!/usr/local/easyops/python/bin/python
# -*- coding: utf-8 -*-
# @Date: 2020-08-07
# @File: monitor_tcp.py
# @Author: zhangwei
# @Desc: 


import socket
import json


def telnet(ip, port, timeout=10):
    s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    s.settimeout(timeout)

    try:
        s.connect((ip, port))
        s.close()
    except socket.error as err:
        return str(err)

    return ''


# Main
# easy_ips = '10.0.0.1,10.0.0.2'
# easy_port = 3306
# easy_desc = 'xxx数据库'
# easy_timeout = 10

output = []

for ip in easy_ips.split(','):
    if ip == '':
        continue

    ret = telnet(ip, port=easy_port, timeout=easy_timeout)
    status = 1 if len(ret) == 0 else 0
    vals = {'TcpStatus': status, 'msg': ret}
    dims = {
        'data_name': 'tcp_monitor', 'target': ip, 'port': str(easy_port), 'desc': easy_desc
    }
    output.append({'dims': dims, 'vals': vals})

print(json.dumps(output, indent=4))