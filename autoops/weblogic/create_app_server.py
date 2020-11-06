# -*- coding: utf-8 -*-
# @Date: 2020-08-27
# @File: 创建Weblogic应用服务器.py
# @Author: zhangwei
# @Desc: 


from datetime import datetime
import subprocess
import sys
import os


tmpl_wlst_create_server = """
# 开始创建应用Server
connect('weblogic', 'password', 't3://127.0.0.1:7040')
edit()
startEdit()
cd('/')
cmo.createServer("{server_name}")
cd('/Servers/' + "{server_name}")
cmo.setListenAddress("{server_listen_address}")
cmo.setListenPort({server_listen_port})
save()
activate()
exit()
"""


def printf(content):
    print('[{}] {}'.format(datetime.now().strftime("%Y/%m/%d_%H:%M:%S"), content))


def run_cmd(cmd):
    printf('执行命令：{}'.format(cmd))
    process = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    return stdout, stderr


def wlst2file(content):
    EASYOPS_BASE = '/tmp/'
    cache_dir = 'cache_hbrs_weblogic'
    cache_dir = os.path.join(EASYOPS_BASE, cache_dir)
    
    if not os.path.isdir(cache_dir):
        os.mkdir(cache_dir)
        os.popen('chmod 777 {}'.format(cache_dir))
        
    file = 'wlst_file.{}'.format(datetime.now().strftime('%Y%m%d.%H%M%S'))
    file = os.path.join(cache_dir, file)
    with open(file, 'w') as f:
        f.write(content)
    return file


def create_app_server(server, listen_ip, listen_port):
    printf('开始创建服务器 {}'.format(server))
    wlst_shell = "/home/weblogic/Oracle/Middleware/wlserver/common/bin/wlst.sh"

    wlst_create_server = tmpl_wlst_create_server.format(
        # user=user,
        # password=password,
        # admin_interface=admin_interface,
        server_name=server,
        server_listen_address=listen_ip,
        server_listen_port=listen_port
    )
    wlst_create_server = wlst2file(wlst_create_server)

    out, err = run_cmd('cat {}|{}'.format(wlst_create_server, wlst_shell))
    if len(err) > 0:
        if 'Bean already exists' not in err:
            printf('创建Weblogic应用服务器失败')
            printf(err)
            return False
            
    printf('Weblogic应用服务器创建完毕')
    return True


def setting_app_server(domain_root, app_server, app_user):
    server_root = os.path.join(domain_root, 'servers', app_server)
    security_dir = os.path.join(server_root, 'security')
    printf('初始化 security 目录: {}'.format(security_dir))

    os.popen('mkdir -p {}'.format(security_dir))
    boot_properties = os.path.join(security_dir, 'boot.properties')

    if not os.path.isfile(boot_properties):
        with open(boot_properties, 'w') as f:
            f.write("username=weblogic\npassword=password")

    run_cmd(
        'chown -R {user}:{group} {dir}'.format(
            user=app_user, group=app_user, dir=server_root
        )
    )


if __name__ == "__main__":
    # easy_domain_root
    # easy_user
    # easy_app_server

    try:
        servers = json.loads(easy_app_server)
    except ValueError as err:
        print('easy_app_server不是合法的JSON String')
        sys.exit(1)

    for item in servers:
        success = create_app_server(
            item['name'], item['listenIp'], item['listenPort']
        )
        
        if not success:
            sys.exit(1)
        else:
            setting_app_server(easy_domain_root, item['name'], easy_user)
