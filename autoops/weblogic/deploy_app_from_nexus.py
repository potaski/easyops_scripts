# -*- coding: utf-8 -*-
# @Date: 2020-08-27
# @File: 从Nexus部署Weblogic应用.py
# @Author: zhangwei
# @Desc: 


from datetime import datetime
import subprocess
import time
import sys
import os


tmpl_wlst_deploy_app = """
# 部署
connect('weblogic', 'password', 't3://127.0.0.1:7040')
edit()
startEdit()
deploy(appName='{app_name}', path='{app_package}', targets='{server_name}', timeout={timeout})
save()
activate()
exit()
"""


tmpl_wlst_check_app = """
connect('weblogic', 'password', 't3://127.0.0.1:7040')
cd('AppDeployments/{app_name}')
get("AbsoluteSourcePath")
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


def run_chown(user, group, dir):
    run_cmd('chown -R {}:{} {}'.format(user, group, dir))


def download_from_nexus(domain_root, url):
    printf('开始从Nexus下载应用')
    download_dir = os.path.join(domain_root, 'download')
    if not os.path.isdir(download_dir):
        os.mkdir(download_dir)

    filename = url.split('/')[-1]
    pkg_path = os.path.join(download_dir, filename)

    printf('下载到临时位置 {}'.format(pkg_path))
    out, err = run_cmd(
        'cd {} && wget --http-user=user  --http-passwd=password {} 2>/dev/null -O {}&& echo 0 || echo 1'.format(
            download_dir,
            url,
            filename
        )
        # 'cd {} && wget --http-user={} --http-password={} {} 2>/dev/null && echo 0 || echo 1'.format(
        #     download_dir,
        #     nexus_user,
        #     nexus_passwd,
        #     url
        # )
    )

    if len(err) > 0:
        printf('下载失败，无法完成部署')
        printf(err)
        sys.exit(1)

    return pkg_path


def deploy_app(package, deploy_dir, app_server, app_name, app_user):
    """ 参数说明
    包规范: package
        压缩包统一使用 tar czf *.tar.gz 目录，或者 *.tgz 也可
        war/jar包保留原格式
    部署目录: deploy_dir
        当为压缩包时，压缩包应该包含最后一层目录，例如核心
            deploy_dir = /app/lis/webapps/haibao
            压缩包解压出来的应该是项目文件夹haibao
            项目文件夹存放于/app/lis/webapps/
        当为war/jar时，deploy_dir为存放war/jar的目录
    """
    wlst_shell = "/home/weblogic/Oracle/Middleware/wlserver/common/bin/wlst.sh"

    if not os.path.isfile(package):
        printf('没有找到应用包 {}'.format(package))
        printf('部署失败')
        sys.exit(1)

    if package.endswith('tar.gz') or package.endswith('tgz'):
        printf('开始部署压缩包')
        app_path = deploy_dir
        deploy_dir = '/'.join(deploy_dir.split('/')[:-1])

        if not os.path.isdir(deploy_dir):
            os.popen('mkdir -p {}'.format(deploy_dir))

        run_cmd('tar zxf {} -C {}'.format(package, deploy_dir))

    elif package[-3:] in ['war', 'jar']:
        printf('开始部署JAR/WAR包')
        filename = package.split('/')[-1]
        
        if deploy_dir.endswith('.war') or deploy_dir.endswith('.jar'):
            app_path = deploy_dir
        else:
            app_path = os.path.join(deploy_dir, filename)

        run_cmd('mkdir -p {}'.format(os.path.dirname(app_path)))
        run_cmd('mv {} {}'.format(package, app_path))

    else:
        printf('解析应用包异常，检查输入参数')
        sys.exit(1)

    # check if app exist
    # printf('检查Weblogic是否已经部署相同应用')
    # wlst_check_app = tmpl_wlst_check_app.format(app_name=app_name)
    # wlst_check_app = wlst2file(wlst_check_app)

    # out, err = run_cmd('cat {}|{}'.format(wlst_check_app, wlst_shell))
    # print(out)
    # time.sleep(15)
    # if app_path in out:
    #     printf('出现错误：Weblogic中已经存在相同应用')
    #     sys.exit(1)

    printf('开始准备应用部署WLST脚本')
    time.sleep(15)
    wlst_deploy_app = tmpl_wlst_deploy_app.format(
        app_name=app_name,
        app_package=app_path,
        server_name=app_server,
        timeout=600
    )
    wlst_deploy_app = wlst2file(wlst_deploy_app)
    
    if os.path.isfile(wlst_deploy_app):
        printf(wlst_deploy_app)
        printf('脚本已生成')
        return wlst_deploy_app
    
    printf('{} 脚本不存在'.format(wlst_deploy_app))
    sys.exit(1)
    # out, err = run_cmd('cat {}|{}'.format(wlst_deploy_app, wlst_shell))
    # time.sleep(15)
    # printf(out)

    # if len(err) > 0:
    #     printf('部署应用失败')
    #     printf(err)
    #     sys.exit(1)

    return False


if __name__ == "__main__":
    # easy_app_server
    # easy_user
    # easy_domain_root

    try:
        servers = json.loads(easy_app_server)
    except ValueError as err:
        print('easy_app_server不是合法的JSON String')
        sys.exit(1)

    wlst_scripts = []

    for item in servers:
        printf('开始部署Weblogic应用服务器 {}'.format(item['name']))

        if item['deployDir'].startswith('/'):
            deploy_dir = item['deployDir']
        else:
            deploy_dir = os.path.join(easy_domain_root, item['deployDir'])

        app = download_from_nexus(easy_domain_root, item['nexusRepo'])
        success = deploy_app(
            package=app,
            deploy_dir=deploy_dir,
            app_server=item['name'],
            app_name=item['appName'],
            app_user=easy_user
        )

        if success:
            wlst_scripts.append(success)

    run_chown(easy_user, easy_user, easy_domain_root)
    PutStr('easy_wlst_deploy_app', '\n'.join(wlst_scripts))