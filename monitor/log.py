#!/usr/local/easyops/python/bin/python
# -*- coding: utf-8 -*-
# @Date: 2020-07-01
# @File: logs.py
# @Author: zhangwei
# @Desc: 


import os
import json
import psutil
from datetime import datetime


def to_cache(cache_file, json_data):
    dir, file = os.path.split(cache_file)
    if not os.path.isdir(dir):
        os.mkdir(cache_dir)
    with open(cache_file, 'w') as f:
        f.write(json.dumps(json_data))
    return True


def from_cache(cache_file):
    if not os.path.isfile(cache_file):
        return False
    try:
        json_data = json.loads(open(cache_file).read())
        return json_data
    except ValueError as err:
        pass
    return False


def cache_date_rotate(now_date, cache_file):
    if not os.path.isfile(cache_file):
        return False
    cache_mdate = datetime.fromtimestamp(int(os.path.getmtime(cache_file)))
    diff_date = now_date - cache_mdate
    if diff_date.days > 0:
        return True
    return False


def del_empty_item(list_data):
    while '' in list_data:
        list_data.remove('')
    return list_data


def get_ts():
    ts = requests.get('http://10.2.33.99/health-check', headers={'Host': 'api.monitor.hb'})
    ts = ts.json()['data']
    return ts


def main(data_name, logs, keywords, split_str):
    cache_dir = '/usr/local/easyops/cache_hbrs_log'
    output = []
    now_date = datetime.now()
    logs = del_empty_item(logs.splitlines())
    keywords = del_empty_item(keywords.splitlines())

    if '%' in split_str:
        split_str = now_date.strftime(split_str)

    for log in logs:
        data = []

        if '%' in log:
            cache_file = '{}.json'.format('_'.join(log.replace('%', '').split('/')))
            log = now_date.strftime(log)
        else:
            cache_file = '{}.json'.format('_'.join(log.split('/')))
            
        dims = {'data_name': data_name, 'log': log}
        vals = {'LogMonitor': 0, 'data': '', 'LogMonitorProc': 0, 'error': ''}
        cache_file = os.path.join(cache_dir, cache_file)

        if not os.path.isfile(log):
            # file not found
            vals.update({'LogMonitorProc': 1, 'error': 'Log Not Found'})
            output.append({'dims': dims, 'vals': vals})
            continue

        # date_change = cache_date_rotate(now_date, cache_file)
        log_mtime = os.path.getmtime(log)
        log_size = os.path.getsize(log)
        cache = from_cache(cache_file)
        # cache = False

        if not cache:
            cache = {'log_mtime': 0, 'log_size': 0, 'mark': 0}

        if log_mtime == cache['log_mtime']:
            # file not changed
            output.append({'dims': dims, 'vals': vals})
            continue
        else:
            # file has changed
            # if file size less then before, see as new file, reset mark
            if 'log_size' in cache and log_size < cache['log_size']:
                cache['mark'] == 0

        mark = 0

        if split_str != 'Null':
            log_size = os.path.getsize(log)
            mem_available = psutil.virtual_memory().available

            if log_size * 10 > mem_available:
                # file too large
                vals.update(
                    {'LogMonitorProc': 1, 'error': 'LogSize={}MB, MemAvailable={}MB'.format(
                        log_size/1024/1024, mem_available/1024/1024
                    )}
                )
                output.append({'dims': dims, 'vals': vals})
                continue
            else:
                list_log = open(log).read().split(split_str)
                for item in list_log:
                    mark += 1
                    if mark <= cache['mark']:
                        continue

                    for key in keywords:
                        if key in item:
                            data.append(split_str + item.strip())
                            break
        
        else:
            with open(log, 'rb') as list_log:
                for item in list_log:
                    mark += 1
                    if mark <= cache['mark']:
                        continue

                    for key in keywords:
                        if key in item:
                            data.append(split_str + item.strip())
                            break

        to_cache(
            cache_file, {'log_mtime': log_mtime, 'log_size': log_size, 'mark': mark}
        )
        vals.update({'log_mtime': log_mtime, 'log_size': log_size, 'mark': mark})
        vals.update({'LogMonitor': len(data), 'data': '\n'.join(data)})
        output.append({'dims': dims, 'vals': vals})

    return output


if __name__ == "__main__":
    ret = main(
        data_name='isee_log',
        logs=easy_logs,
        keywords=easy_keywords,
        split_str=easy_split_str
    )
    print(json.dumps(ret, indent=4))