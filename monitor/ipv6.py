#!/usr/local/easyops/python/bin/python
# -*- coding: utf-8 -*-
# @Date: 2020-07-23
# @File: ipv6_ping.py
# @Author: zhangwei
# @Desc: ipv6业务监控


import os
import json


cmd_curl = "curl -6 -sI https://{}/|head -n 1|awk '{{print $2}}'"
cmd_ping = 'ping6 -c 5 {}|tail -n 2'

domains = {
    '海保人寿官网IPV6': 'www.haibao-life.com'
}

output = []

for desc, domain in domains.items():
    ret_curl = os.popen(cmd_curl.format(domain)).read()
    try:
        http_code = int(ret_curl.strip())
    except:
        http_code = 0

    ret_ping = os.popen(cmd_ping.format(domain)).read()
    for line in ret_ping.strip().splitlines():
        if 'packet loss' in line:
            try:
                ping_loss = int(line.split(' ')[5].replace('%', ''))
            except:
                ping_loss = 100

        if line.startswith('rtt'):
            times = line.split(' ')[3]
            try:
                ping_avg = float(times.split('/')[1])
            except:
                ping_avg = 10 * 1000
    
    vals = {
        'HTTP_CODE': http_code,
        'PING_AVG': ping_avg,
        'PING_LOSS': ping_loss
    }
    
    output.append({
        'dims': {
            'data_name': 'ping_ipv6', 'desc': desc, 'domain': domain
        },
        'vals': vals
    })

print(json.dumps(output, indent=4, ensure_ascii=False))
