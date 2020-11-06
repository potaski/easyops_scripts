#!/usr/local/easyops/python/bin/python
# -*- coding: utf-8 -*-
# @Date: 2020-06-30
# @File: weblogic_server.py
# @Author: zhangwei
# @Desc: 


import requests
import json
import os
from requests import exceptions as httperror
from datetime import datetime
from bs4 import BeautifulSoup


class WeblogicConsole:

    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.s = requests.session()
        self.cache_dir = '/usr/local/easyops/cache_hbrs_weblogic'
        if not os.path.isdir(self.cache_dir):
            os.mkdir(self.cache_dir)

    def login(self, user, passwd):
        url = 'http://{}:{}//console/j_security_check'.format(
            self.ip, self.port
        )
        data = {'j_username': user, 'j_password': passwd}
        try:
            ret = self.s.post(url=url, data=data, timeout=5)
            if ret.status_code == 200:
                return True, 'ok'
            else:
                return False, '登陆失败：{}\n详情：{}'.format(url, ret.text)
        except (httperror.ConnectionError, httperror.ConnectTimeout) as err:
            return False, '链接失败：{}\n详情：{}'.format(url, err.args[0])

    def logout(self):
        url = 'http://{}:{}/console/jsp/common/warnuserlockheld.jsp'.format(
            self.ip, self.port
        )
        self.s.get(url=url)

    def server_cache(self, new_server=False):
        cache_file = os.path.join(
            self.cache_dir, '{}_{}.json'.format(self.ip, self.port)
        )
        cache_expire = 3600  # 1 hour
        now_time = int(datetime.now().strftime('%s'))

        if not new_server and not os.path.isfile(cache_file):
            return False

        if new_server:
            cache_data = {
                'expire_time': now_time + cache_expire,
                'servers': new_server
            }
            with open(cache_file, 'w') as f:
                f.write(json.dumps(cache_data, indent=4))
            return True

        else:
            with open(cache_file) as f:
                server = json.loads(f.read())
            return server

    def server(self, ignore_admin=True, refresh_cache=False):
        # 强制优先使用缓存
        if not refresh_cache:
            result = self.server_cache()
            if result:
                now_time = int(datetime.now().strftime('%s'))
                if now_time < result['expire_time']:
                    return result['servers']

        result = []
        url = 'http://{}:{}/console/console.portal'.format(self.ip, self.port)
        params = {'_nfpb': 'true', '_pageLabel': 'CoreServerServerTablePage'}
        ret = self.s.get(url=url, params=params)
        soup = BeautifulSoup(ret.text, 'html.parser')

        for i in range(1, 20):
            name = soup.select("td[id='name{}']".format(i))
            if len(name) != 1:
                continue
            if ignore_admin and name[0].text == 'AdminServer(admin)':
                continue
            result.append({
                'name': name[0].text,
                'state': soup.select("td[id='state{}']".format(i))[0].text,
                'health': soup.select("td[id='health{}']".format(i))[0].text.replace('\u00a0', ''),
                'listen_port': soup.select("td[id='listenPort{}']".format(i))[0].text
            })

        self.server_cache(new_server=result)
        return result

    def jdbc(self):
        result = []
        url = 'http://{}:{}/console/console.portal'.format(self.ip, self.port)

        params = {
            '_nfpb': 'true', '_pageLabel': 'GlobalJDBCDataSourceTablePage'
        }
        ret = self.s.get(url=url, params=params)
        soup = BeautifulSoup(ret.text, 'html.parser')
        parent = soup.select('title')[0].text.split(' - ')[1]
        for i in range(1, 20):
            name = soup.select("td[id='Name{}']".format(i))
            if len(name) == 1:
                targets = soup.select("td[id='Targets{}']".format(i))[0].text
                result.append({
                    'parent': parent,
                    'name': name[0].text,
                    'jndi_name': soup.select("td[id='JndiName{}']".format(i))[0].text,
                    'server': targets.split(', ')
                })

        return result

    def perf_jdbc(self, parent, name):
        metrics = {
            # 'server': '服务器',
            # 'Enabled': '启用',
            # 'State': '状态',
            # 'VersionJDBCDriver': 'JDBC驱动程序',
            'NumUnavailable': '不可用数量',
            'NumAvailable': '可用数量',
            'CurrCapacity': '当前容量',
            'ActiveConnectionsCurrentCount': '当前活动连接计数',
            # 'HighestNumAvailable': '最大可用容量',
            # 'CurrCapacityHighCount': '最大当前容量计数',
            'ActiveConnectionsHighCount': '最大活动连接计数',
            # 'WaitingForConnectionHighCount': '最大等待连接计数',
            # 'WaitSecondsHighCount': '最长等待秒数',
            'ConnectionDelayTime': '连接延迟时间',
            # 'ConnectionsTotalCount': '连接总数'
        }
        url = 'http://{}:{}/console/console.portal'.format(self.ip, self.port)
        result = {}

        params = {
            '_nfpb': 'true',
            '_pageLabel': 'JdbcDatasourcesJDBCDataSourceMonitorPage',
            'handle': (
                'com.bea.console.handles.JMXHandle("com.bea:Name={name},'
                'Type=weblogic.j2ee.descriptor.wl.JDBCDataSourceBean,'
                'Parent=[{parent}]/'
                'JDBCSystemResources[{name}],Path=JDBCResource[{name}]")'
            ).format(name=name, parent=parent)
        }
        step = self.s.get(url=url, params=params)
        soup = BeautifulSoup(step.text, 'html.parser')
        for i in range(1, 20):
            server = soup.select("td[id='server{}']".format(i))
            if len(server) == 1:
                error = []
                detail = {}
                for metric in metrics:
                    value = soup.select("td[id='{}{}']".format(metric, i))
                    if len(value) == 1:
                        try:
                            detail[metric] = int(value[0].text)
                        except:
                            detail[metric] = value[0].text
                    else:
                        error.append('Metric Not Found: {}'.format(metric))
                detail['error'] = '\n'.join(error)
                detail['error_num'] = len(error)
                result[server[0].text] = detail

        return result

    def perf_base(self, server):
        error = []
        result = {}
        key_perfix = (
            'CoreServerServerMonitoringPerformancePortletserverMonitoringPerformance'
        )
        key_suffix = '_row'
        metrics = {
            'heapSizeCurrent': '当前堆大小',
            'heapFreeCurrent': '当前空闲堆',
            'heapFreePercent': '堆空闲百分比',
            'heapSizeMax': '最大堆大小',
            'processCpuLoad': '进程 CPU 负载',
            'systemCpuLoad': '系统 CPU 负载',
            'freePhysicalMemorySize': '空闲物理内存',
            'committedVirtualMemorySize': '提交的虚拟内存'
        }
        url = 'http://{}:{}/console/console.portal'.format(self.ip, self.port)
        params = {
            '_nfpb': 'true',
            '_pageLabel': 'ServerMonitoringPerformancePage',
            'handle': (
                'com.bea.console.handles.JMXHandle("com.bea:'
                'Name={server},Type=Server")'
            ).format(server=server)
        }
        ret = self.s.get(url=url, params=params)
        soup = BeautifulSoup(ret.text, 'html.parser')
        for metric in metrics:
            value = False
            html_id = '{}.{}{}'.format(key_perfix, metric, key_suffix)
            ret = soup.select("tr[id='{}']".format(html_id))
            if len(ret) == 1:
                new_soup = BeautifulSoup(str(ret[0]), 'html.parser')
                ret = new_soup.select('div')
                if len(ret) == 1:
                    if 'CpuLoad' in metric:
                        value = float(ret[0].text[:5])
                    else:
                        value = int(ret[0].text)
            if value:
                result[metric] = value
            else:
                error.append('Metric Not Found: {}'.format(metric))

        result['error'] = '\n'.join(error)
        result['error_num'] = len(error)
        return result

    def perf_thread(self, server):
        error = []
        result = {}
        metrics = {
            'activeExecuteThreads': '活动执行线程',
            'executeThreadIdleCount': '空闲执行线程计数',
            'pendingUserRequestCount': '暂挂用户请求计数',
            # 'completedRequestCount': '完成的请求计数',
            'hoggingThreadCount': '独占线程计数',
            'standbyThreadCount': '备用线程计数',
            'stuckThreadCount': 'Stuck Threads',
            # 'throughput': '吞吐量',
            # 'healthState': '健康状况'
        }
        url = 'http://{}:{}/console/console.portal'.format(self.ip, self.port)
        params = {
            '_nfpb': 'true',
            '_pageLabel': 'ServerMonitoringThreadsPage',
            'handle': (
                'com.bea.console.handles.JMXHandle("com.bea:'
                'Name={server},Type=Server")'
            ).format(server=server)
        }
        ret = self.s.get(url=url, params=params)
        soup = BeautifulSoup(ret.text, 'html.parser')
        for metric in metrics:
            ret = soup.select("td[id='{}1']".format(metric))
            if len(ret) == 1:
                if metric in ['throughput']:
                    result[metric] = float(ret[0].text)
                elif metric == 'healthState':
                    result[metric] = ret[0].text.replace('\u00a0', '')
                else:
                    result[metric] = int(ret[0].text)
            else:
                error.append('Metric Not Found: {}'.format(metric))

        result['error'] = '\n'.join(error)
        result['error_num'] = len(error)
        return result


def get_ts():
    ts = requests.get('http://10.2.33.99/health-check', headers={'Host': 'api.monitor.hb'})
    ts = ts.json()['data']
    return ts


if __name__ == "__main__":
    # easyops arguments scope
    # easy_localtime = 1
    # easy_user = 'weblogic'
    # easy_passwd = 'password'
    # easy_port = '7040'
    easy_data_name = 'lis_weblogic_server'

    if easy_localtime == 0:
        ts = get_ts()

    wc = WeblogicConsole(ip='127.0.0.1', port=easy_port)
    login, msg = wc.login(easy_user, easy_passwd)

    if login:
        output = []
        server = wc.server(ignore_admin=True)

        for s in server:
            if s['state'] != 'RUNNING':
                continue
            
            dims = {
                'data_name': easy_data_name,
                'server_port': s['listen_port'],
                'server': s['name']
            }
            data = {'dims': dims, 'vals': wc.perf_base(server=s['name'])}

            if easy_localtime == 0:
                data['ts'] = ts
                
            output.append(data)

        wc.logout()
        print(json.dumps(output, indent=4))

    else:
        print(json.dumps(
            {
                'dims': {
                    'data_name': easy_data_name,
                    'server': 'server', 'server_port': 'server_port'
                },
                'vals': {
                    'error': msg, 'error_num': 1
                }
            },
            indent=4
        ))