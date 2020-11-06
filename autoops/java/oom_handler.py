# -*- coding: utf-8 -*-
# @Date: 2020-06-08
# @File: java_heap_dump.py
# @Author: zhangwei
# @Desc:


from datetime import datetime
import subprocess
import time
import sys
import os


def printf(content):
    print('[{}] {}'.format(datetime.now().strftime("%Y/%m/%d_%H:%M:%S"), content))


def run_cmd(cmd):
    process = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    printf('[执行Shell命令，PID="{}"]\n{}'.format(process.pid, cmd))
    stdout, stderr = process.communicate()
    return stdout, stderr


def remove_empty(target):
    while '' in target:
        target.remove('')
    return target


def get_pid_by_port(port):
    cmd = "netstat -ntlp 2>/dev/null|grep ':{} '|awk '{{print $NF}}'|uniq".format(port)
    out, err = run_cmd(cmd)
    if len(out) > 0 and len(out.splitlines()) == 1:
        pid = out.split('/')[0]
        return pid
    return False


def get_proc_by_pid(pid):
    cmd = 'ps -ef|grep {}|grep -v grep'.format(pid)
    out, err = run_cmd(cmd)
    if len(out) > 0:
        ret = os.popen(cmd).read().strip().split(' ')
        ret = remove_empty(ret)
        
        java_home = os.path.dirname(ret[7])
        app_user = ret[0]
    return java_home, app_user


def find_thread_by_pid(pid, user):
    # 找到可能异常的线程
    output = []
    max_cpu_thread, err = run_cmd(
        "top -p {} -H -b -n 1|grep {}|sort -k 9 -n|tail -n 1".format(pid, user)
    )
    max_mem_thread, err = run_cmd(
        "top -p {} -H -b -n 1|grep {}|sort -k 10 -n|tail -n 1".format(pid, user)
    )
    
    for thread in [max_cpu_thread, max_mem_thread]:
        if len(thread) > 1 and len(thread.strip().split(' ')) > 14:
            thread = thread.strip().split(' ')
            tid = int(thread[0])
            tid_hex = hex(tid)
            # user = thread[1]
            try:
                cpu = float(thread[13])
                mem = float(thread[14])
                if cpu > 0 or mem > 0:
                    if [tid, tid_hex, cpu, mem] not in output:
                        output.append([tid, tid_hex, cpu, mem])
            except ValueError as err:
                pass

    return output


def exec_jstack(jstack, user, pid, tid_hex):
    # cmd = 'su {} -c "{} -l {}|grep {} -A 200"'.format(user, jstack, pid, tid_hex)
    cmd = [
        'su - {} <<CMD'.format(user),
        ' '.join([jstack, '-l', pid, '|', 'grep', tid_hex, '-C', '25']),
        'CMD'
    ]
    result, err = run_cmd('\n'.join(cmd))
    return result


def exec_jmap_histo_live(jmap, user, pid):
    # cmd = 'su {} -c "jmap -histo:live {}"|head -n 20'.format(user, pid)
    cmd = [
        'su - {} <<CMD'.format(user),
        ' '.join([jmap, '-histo:live', pid, '|', 'head', '-n', '20']),
        'CMD'
    ]
    result, err = run_cmd('\n'.join(cmd))
    return result


def exec_jmap_dump_file(jmap, pid, port):
    now = datetime.now()
    cache_dir = '/tmp/'
    cache_file = os.path.join(
        cache_dir,
        'jmap.hprof_{}_{}'.format(port, now.strftime('%Y%m%d_%H%M'))
    )

    cmd = '{} -F -dump:live,file={} {}'.format(jmap, cache_file, pid)
    result, err = run_cmd(cmd)
    return result, cache_file


def main(port, cmd_restart):
    # user args
    # port = easy_port

    # 根据端口查找pid，进而找到详细的进程信息
    pid = get_pid_by_port(port)
    if not pid:
        printf('错误: 未找到端口 {} 所对应的进程PID')
        sys.exit(1)

    java_home, app_user = get_proc_by_pid(pid)
    jstack = os.path.join(java_home, 'jstack')
    jstat = os.path.join(java_home, 'jstat')
    jmap = os.path.join(java_home, 'jmap')

    for file in [jstack, jstat, jmap]:
        if not os.path.isfile(file):
            printf('错误: 未找到java相关执行文件 {}'.format(file))
            sys.exit(1)

    printf('应用java_home {}'.format(java_home))
    printf('应用进程pid {}'.format(pid))
    printf('应用进程用户 {}'.format(app_user))

    # jstack 打印线程
    threads = find_thread_by_pid(pid, app_user)
    if len(threads) == 0:
        printf('未找到异常线程，jstack不执行')
    else:
        out_jstack = []
        for thread in threads:
            printf('找到异常线程: tid="{}", tid_hex="{}", cpu="{}%", mem="{}%"'.format(
                thread[0], thread[1], thread[2], thread[3]
            ))
            ret_jstack = exec_jstack(jstack=jstack, user=app_user, pid=pid, tid_hex=thread[1])
            printf('jstack 追踪线程结束\n{}\n'.format(ret_jstack))

            out_jstack.append('异常线程: tid="{}", tid_hex="{}", cpu="{}%", mem="{}%"'.format(
                thread[0], thread[1], thread[2], thread[3]
            ))
            out_jstack.append(ret_jstack)

        PutStr('out_jstack', '\n'.join(out_jstack))

    # jmap histo live
    ret_jmap_histo_live = exec_jmap_histo_live(jmap=jmap, user=app_user, pid=pid)
    printf('jmap histo live结束，内存暂用最高的类为\n{}\n'.format(ret_jmap_histo_live))
    PutStr('out_jmap_histo_live', ret_jmap_histo_live)

    # jmap dump file
    ret_jmap_dump_file, file_path = exec_jmap_dump_file(jmap=jmap, pid=pid, port=port)
    printf('jmap heap dump结束，生成文件\n{}\n'.format(file_path))

    # 重启应用
    printf('重启应用开始')
    cmd_restart = [
        'su - {} <<CMD'.format(app_user),
        'sh {}'.format(cmd_restart),
        'CMD'
    ]
    out, err = run_cmd('\n'.join(cmd_restart))
    printf('重启应用结束\n{}'.format(out))
    PutStr('out_restart', out)
    
    # 发送dump文件
    if os.path.isfile(file_path):
        run_cmd('yum -y install sshpass')
        remote_ip = '10.2.33.7'
        remote_user = 'devops'
        remote_passwd = 'password'
        remote_path = os.path.join(
            '/home/devops/dump',
            '{ip}:{port}_{datetime}_Heapdump'.format(
                ip=EASYOPS_LOCAL_IP, port=port,
                datetime='_'.join(file_path.split('_')[-2:])
            )
        )
        printf('开始发送 heap dump 文件到 {}'.format(remote_ip))
        out, err = run_cmd(' '.join(
            [
                'sshpass -p "{}"'.format(remote_passwd),
                'scp',
                '-o StrictHostKeyChecking=no',
                '-o UserKnownHostsFile=/dev/null',
                file_path,
                '{}@{}:{}'.format(remote_user, remote_ip, remote_path)
            ]
        ))
        printf(out)
        printf(err)
        printf('文件发送完成，文件存放在 {}'.format(remote_path))
        PutStr('out_jmap_heap_dump_file', remote_path)

    else:
        printf('文件生成失败，不发送至运维服务器')
        PutStr('out_jmap_heap_dump_file', '')

    # MAT analysis tool
    # /app/tools/mat/ParseHeapDump.sh /tmp/jmap.hprof_7041_20200821_0954 org.eclipse.mat.api:suspects org.eclipse.mat.api:overview org.eclipse.mat.api:top_components


if __name__ == "__main__":
    printf('执行IP：{}'.format(EASYOPS_LOCAL_IP))

    if " " in easy_restart_shell:
        shell = easy_restart_shell.split(' ')[0]
    else:
        shell = easy_restart_shell
        
    if not os.path.isfile(shell):
        printf('没有找到重启命令（脚本）: {}'.format(shell))
        sys.exit(1)
    
    main(port=easy_port, cmd_restart=easy_restart_shell)