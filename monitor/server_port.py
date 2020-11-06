#!/usr/local/easyops/python/bin/python
# encoding:utf-8


import socket
import platform
import subprocess
import json
import os


OS_TYPE = platform.system()


def easyops_custom_output(dim_keys, values):
    res = {}
    res["dims"] = {k: values.pop(k) for k in dim_keys if k in values}
    res["vals"] = values
    return res


def run_cmd(cmd):
    process = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    return stdout, stderr


def port_alive(port, host="127.0.0.1"):
    sk = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sk.settimeout(1)

    if not host:
        host = "127.0.0.1"

    port = int(port)

    try:
        sk.connect((host, port))
    except Exception:
        return 0

    sk.close()
    return 1


def port_connections(port, host=None):
    host_info = ""

    if host:
        host_info = "src {}".format(host)

    cmd = "ss {} '( sport = :{} )'|wc -l".format(host_info, port)
    out, err = run_cmd(cmd)

    if err:
        return 0

    return int(out) - 1


def port_process(port, host=None):
    host_info = ""

    if OS_TYPE == 'Windows':
        pid = ""
        pname = ""
        out, err = run_cmd('netstat -ano|find "LISTEN"')

        for line in out.splitlines():
            if ':%s ' % (port) in line:
                pid = line.split(' ')[-1]
                break

        if pid != "":
            out, err = run_cmd('tasklist')

            for line in out.splitlines():
                line = line.split(' ')
                while '' in line:
                    line.remove('')
                if len(line) > 2 and line[1] == pid:
                    pname = line[0]
                    break
                
    elif OS_TYPE == 'Linux':
        cmd = "netstat -ntlp|grep ':%s '" % (port)
        out, err = run_cmd(cmd)

        if err:
            return "", ""
        if not out:
            return "", ""

        out = out.strip().split('  ')[-1].split('/')
        pid = out[0]
        pname = out[1]

    return pname, pid

def get_port_info(data_name, dim_keys, port):
    port = port.split(":")

    if len(port) > 1:
        host = port[0]
        port = port[1]
    else:
        host = None
        port = port.pop()

    # add by haibao to get host ip
    # sort ip: origin_local_ip > other_local_ip(vip) > loopback_ip(127.0.0.1)

    filter_ips = []

    if OS_TYPE == 'Windows':
        hostname = socket.gethostname()
        filter_ips.append(socket.gethostbyname(hostname))

    elif OS_TYPE == 'Linux':
        if os.path.isfile('/etc/sysconfig/network-scripts/ifcfg-eth0'):
            cmd = 'grep "IPADDR=" /etc/sysconfig/network-scripts/ifcfg-eth0'
            origin_ip = os.popen(cmd).read().strip().split('=')[1].replace("'", "")
            filter_ips.append(origin_ip)

        for line in os.popen('ip a').read().splitlines():
            if 'inet' in line:
                line = line.split(' ')
                ip = line[5].split('/')[0] if '/' in line[5] else line[5]
                interface = line[-1]
                if ip not in filter_ips and ip != '127.0.0.1':
                    filter_ips.append(ip)

    filter_ips.append('127.0.0.1')

    for ip in filter_ips:
        alived = port_alive(port, ip)
        if alived == 1:
            host = ip
            break

    if not host:
        host = filter_ips[0]

    # add by haibao to get host ip
    connections = port_connections(port, host)
    pname, pid = port_process(port, host)
    port_info = {
        "data_name": data_name,
        "host": host,
        "port": port,
        "pid": pid,
        "pname": pname,
        "TcpPortAlived": alived,
        "connections": connections,
    }
    return easyops_custom_output(dim_keys, port_info)


# main

# ports = '81,82'
data_name = "port_monitor_hbrs"
ports = ports.split(",")
dim_keys = ["data_name", "port", "pname", "host"]
data = []
while ports:
    port = ports.pop().strip()
    info = get_port_info(data_name, dim_keys, port)
    data.append(info)
    
print json.dumps(data, indent=4)