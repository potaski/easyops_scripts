# -*- coding: utf-8 -*-
# @Date: 2020-08-27
# @File: 创建WeblogicJDBC数据源.py
# @Author: zhangwei
# @Desc: 


from datetime import datetime
import subprocess
import sys
import os


tmpl_wlst_create_jdbc = """
# 开始配置数据源
connect('weblogic', 'password', 't3://127.0.0.1:7040')
edit()
startEdit()
cd('/')
cmo.createJDBCSystemResource('{jdbc_name}')
cd('/JDBCSystemResources/' + '{jdbc_name}' + '/JDBCResource/' + '{jdbc_name}')
cmo.setName('{jdbc_name}')
cd('/JDBCSystemResources/' + '{jdbc_name}' + '/JDBCResource/' + '{jdbc_name}' + '/JDBCDataSourceParams/' + '{jdbc_name}' )
set('JNDINames', '{jdbc_jdni}', String))
# 这个不理解
# 可能为页面上的：配置 - 事务处理 - 一阶段提交
cd('/JDBCSystemResources/' + '{jdbc_name}' + '/JDBCResource/' + '{jdbc_name}' + '/JDBCDataSourceParams/' + '{jdbc_name}' )
cmo.setGlobalTransactionsProtocol('OnePhaseCommit')
# 开始配置 Driver
cd('/JDBCSystemResources/' + '{jdbc_name}' + '/JDBCResource/' + '{jdbc_name}' + '/JDBCDriverParams/' + '{jdbc_name}' )
cmo.setUrl('{jdbc_url}')
cmo.setDriverName('{jdbc_driver}')
cmo.setPassword('{jdbc_db_passwd}')
cd('/JDBCSystemResources/' + '{jdbc_name}' + '/JDBCResource/' + '{jdbc_name}' + '/JDBCDriverParams/' + '{jdbc_name}' + '/Properties/' + '{jdbc_name}' )
cmo.createProperty('user')
cd('/JDBCSystemResources/' + '{jdbc_name}' + '/JDBCResource/' + '{jdbc_name}' + '/JDBCDriverParams/' + '{jdbc_name}' + '/Properties/' + '{jdbc_name}' + '/Properties/user')
cmo.setValue('{jdbc_db_user}')
# 开始配置连接池
cd('/JDBCSystemResources/' + '{jdbc_name}' + '/JDBCResource/' + '{jdbc_name}' + '/JDBCConnectionPoolParams/' + '{jdbc_name}' )
cmo.setTestTableName('{jdbc_db_test_sql}')
cmo.setInitialCapacity({jdbc_pool_init_capacity})
cmo.setMinCapacity({jdbc_pool_min_capacity})
cmo.setMaxCapacity({jdbc_pool_max_capacity})
# 开始配置所属服务器
cd('/SystemResources/' + '{jdbc_name}' )
set('Targets',jarray.array([{jdbc_target}], ObjectName))
save()
## active耗时过长，暂时忽略实时，依赖应用部署再做active
## activate()
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


def create_jdbc(jdbc):
    """ jdbc = appspec jdbcDataSources to json """
    wlst_shell = "/home/weblogic/Oracle/Middleware/wlserver/common/bin/wlst.sh"

    for item in jdbc:
        printf('创建JDBC: {}'.format(item['name']))
        targets = [
            "ObjectName('com.bea:Name=' + '{}' + ',Type=Server')".format(tgt) for tgt in item['targets']
        ]
        print(targets)

        wlst_create_jdbc = tmpl_wlst_create_jdbc.format(
            jdbc_name=item['name'],
            jdbc_jdni=item['jdni'],
            jdbc_url=item['url'],
            jdbc_driver=item['driver'],
            jdbc_db_passwd=item['password'],
            jdbc_db_user=item['user'],
            jdbc_db_test_sql=item['testSql'],
            jdbc_pool_init_capacity=item['initialSize'],
            jdbc_pool_min_capacity=item['minIdle'],
            jdbc_pool_max_capacity=item['maxActive'],
            jdbc_target=','.join(targets)
        )
        wlst_create_jdbc = wlst2file(wlst_create_jdbc)

        out, err = run_cmd('cat {} | {} && echo 0'.format(
            wlst_create_jdbc, wlst_shell
        ))
        if out.strip() == '1':
            printf('创建JDBC失败')
            printf(err)
            sys.exit(1)

    return True


if __name__ == "__main__":
    # easy_app_jdbc

    try:
        jdbc = json.loads(easy_app_jdbc)
    except ValueError as err:
        printf('easy_jdbc 不是合法的JSON字符串')
        sys.exit(1)

    create_jdbc(jdbc)
