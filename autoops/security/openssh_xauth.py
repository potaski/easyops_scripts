# -*- coding: utf-8 -*-
# @Date: 2020-06-11
# @File: 20200611_openssh_xauth.py
# @Author: zhangwei
# @Desc: X11Forwarding为YES，且sshd版本小于7.2p2


import os
import re
import platform
import subprocess


def run_cmd(cmd):
    process = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    return stdout, stderr

os_type = platform.system()
wrong_sshd = False

if os_type == 'Linux':

    out, err = run_cmd('sshd -V')
    sshd_version = re.search('OpenSSH_(\S)+', err).group().replace(',', '')
    print('ssh -V: ' + sshd_version)
    ver_num = float(sshd_version.split('_')[-1].split('p')[0][:3])
    pkg_num = int(sshd_version.split('_')[-1].split('p')[1])
    
    if ver_num == 7.2 and pkg_num < 2:
        wrong_sshd = True
    elif ver_num < 7.2:
        wrong_sshd = True

    if wrong_sshd:
        out, err = run_cmd('grep "^X11Forwarding " /etc/ssh/sshd_config')
        x11forwarding = out.strip().split(' ')
        if len(x11forwarding) == 2 and x11forwarding[-1] in ['yes', 'no']:
            x11forwarding = x11forwarding[-1]

        if x11forwarding != 'yes':
            wrong_sshd = False
    else:
        x11forwarding = '不检查'

    PutRow(
        'table_openssh_xauth',
        'ip={}&os={}&sshd_version={}&x11forwarding={}&wrong_sshd={}'.format(
            EASYOPS_LOCAL_IP, os_type, sshd_version, x11forwarding, wrong_sshd
        )
    )
else:
    PutRow(
        'table_openssh_xauth',
        'ip={}&os={}&sshd_version=无&x11forwarding=无&wrong_sshd=无'.format(
            EASYOPS_LOCAL_IP, os_type
        )
    )
    
PutStr('result', wrong_sshd)