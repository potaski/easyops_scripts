# -*- coding: utf-8 -*-
# @Date: 2020-08-25
# @File: 创建Weblogic域.py
# @Author: zhangwei
# @Desc: weblogic 12.1.3


from collections import namedtuple
from datetime import datetime
import subprocess
import requests
import json
import sys
import os


rsp_tmpl_create_domain = """
read template from "/home/weblogic/Oracle/Middleware/wlserver/common/templates/wls/wls.jar";

set JavaHome "{java_home}"; 
set ServerStartMode "prod"; 

find Server "AdminServer" as AdmSrv;
set AdmSrv.ListenAddress "0.0.0.0";
set AdmSrv.ListenPort "{admin_port}";

find User "weblogic" as webcfg;
set webcfg.password "password";

write domain to "/app/{domain_name}"; 
close template;
"""


def printf(content):
    print('[{}] {}'.format(datetime.now().strftime("%Y/%m/%d_%H:%M:%S"), content))


def run_cmd(cmd):
    process = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    return stdout, stderr


def rsp2file(content):
    base_dir = '/tmp/'
    cache_dir = 'cache_hbrs_weblogic'
    cache_dir = os.path.join(base_dir, cache_dir)
    
    if not os.path.isdir(cache_dir):
        os.mkdir(cache_dir)
        os.popen('chmod 777 {}'.format(cache_dir))
        
    file = 'rsp_temp.{}'.format(datetime.now().strftime('%Y%m%d.%H%M%S'))
    file = os.path.join(cache_dir, file)
    with open(file, 'w') as f:
        f.write(content)
    return file


def init_domain_root(domain):
    return os.path.join('/app', domain)


def check_domain_root(domain):
    domain_root = init_domain_root(domain)

    if os.path.isdir(domain_root):
        now = datetime.now().strftime('%Y%m%d.%H%M%S')
        printf('已经存在weblogic域目录 {}'.format(domain_root))
        run_cmd(
            'mv {domain_root} {domain_root}.{datetime}'.format(
                domain_root=domain_root, datetime=now
            )
        )
        printf('备份到 {}.{}'.format(domain_root, now))


def create_domain(java_home, domain, admin_ip, admin_port, app_user):
    weblogic_config_script = "/home/weblogic/Oracle/Middleware/wlserver/common/bin/config.sh"
    domain_root = init_domain_root(domain)
    printf('开始创建Weblogic域目录 {}'.format(domain_root))

    tmpl_rsp = rsp_tmpl_create_domain.format(
        java_home=java_home, domain_name=domain, admin_port=admin_port
    )

    rsp_file = rsp2file(tmpl_rsp)
    printf('从rsp命令模板创建域: {}'.format(rsp_file))

    out, err = run_cmd(
        '/bin/sh {} -mode=silent -silent_script={}'.format(
            weblogic_config_script, rsp_file
        )
    )

    if "succeed: write Domain to" in out and os.path.isdir(domain_root):
        printf('创建域成功，域目录为 {}'.format(domain_root))

        security_dir = os.path.join(domain_root, 'servers/AdminServer/security/')
        os.popen('mkdir -p {}'.format(security_dir))
        boot_properties = os.path.join(security_dir, 'boot.properties')

        if not os.path.isfile(boot_properties):
            with open(boot_properties, 'w') as f:
                f.write("username=weblogic\npassword=password")
                PutStr('easy_console_user', 'weblogic')
                PutStr('easy_console_passwd', 'password')

        printf('更新安全文件成功 servers/AdminServer/security/boot.properties')
        
        cmd_chown = 'chown -R {user}:{group} {dir}'.format(
            user=app_user, group=app_user, dir=domain_root
        )
        printf('执行命令: {}'.format(cmd_chown))
        os.popen(cmd_chown)
        printf('创建Weblogic域结束')
        return domain_root

    printf('创建Weblogic域失败，无法创建域根目录 {}'.format(domain_root))
    return False


if __name__ == "__main__":
    # easy_java_home
    # easy_domain
    # easy_admin_ip
    # easy_admin_port
    # easy_user

    printf('开始创建Welbogic域')
    check_domain_root(easy_domain)

    domain_root = create_domain(
        easy_java_home, easy_domain, easy_admin_ip, easy_admin_port, easy_user
    )
    if domain_root:
        PutStr('easy_domain_root', domain_root)
        run_cmd('chmod 755 /app')
    else:
        sys.exit(1)
