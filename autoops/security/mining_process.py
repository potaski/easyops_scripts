# -*- coding: utf-8 -*-
# @Date: 2020-06-03
# @File: mining_process.py
# @Author: zhangwei
# @Desc: 检查服务器挖矿进程


import os


input_process = 'cryptonight,sustes,xmrig,xmr-stak,suppoie,zer0day.ru'


for proc in input_process.split(','):
    if '|' in proc or ';' in proc or ' ' in proc or ' -' in proc:
        ret = 'Invalid Process Name'

    else:
        cmd = 'pgrep -f ' + proc
        ret = os.popen(cmd).read()

        if ret == '':
            ret = 'None'
        else:
            ret = ','.join(ret.splitlines())
            
    PutRow('table_wkjcjc', 'ip=' + EASYOPS_LOCAL_IP + '&proc=' + proc + '&result=' + ret)