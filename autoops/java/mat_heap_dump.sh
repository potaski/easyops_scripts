datetimeTag() {
    echo "[$(date "+%Y/%m/%d_%H:%M:%S")]"
}


if [ -f "${easy_heap_file}" ];then
    workdir="/home/devops/dump/job_`date +%Y%m%d_%H%M%S`"
    mkdir -p ${workdir}
    echo "`datetimeTag` 创建工作目录 ${workdir}"
    
    mv ${easy_heap_file} ${workdir}
    echo "`datetimeTag` 移动文件 ${easy_heap_file} 到工作目录"
    echo "`datetimeTag` 开始分析HeapDump文件"
    
    cd ${workdir} && /app/tools/mat/ParseHeapDump.sh `echo ${easy_heap_file}|awk -F'/' '{print $NF}'` org.eclipse.mat.api:suspects org.eclipse.mat.api:overview org.eclipse.mat.api:top_components

    if [ `echo $?` -eq "0" ];then
        echo "`datetimeTag` 分析结束，结果存在于 ${workdir}"
        echo "`datetimeTag` 请记得及时清理分析结果，避免占用磁盘空间"
        PutStr "out_workdir" ${workdir}
    fi

    if [ -f "${workdir}/`ls ${workdir}|grep Suspects.zip$`" ];then
        cd /home/devops/dump/web && rm -rf *
        cd /home/devops/dump/web
        cp "${workdir}/`ls ${workdir}|grep Suspects.zip$`" .
        unzip `ls ${workdir}|grep Suspects.zip$`
    else
        echo "`datetimeTag` 找不到分析后的 *Suspects.zip 文件"
        exit 1
    fi

else
    echo "`datetimeTag` 文件 ${easy_heap_file} 未找到"
    exit 1
fi