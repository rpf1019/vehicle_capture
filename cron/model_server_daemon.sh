#/bin/bash sh




modelConf=/model_server/video_object_extraction_server/conf/model.conf
gpu_id=`cat ${modelConf} | grep "^gpu_id = " | cut -d= -f2 |sed 's/[[:space:]]//g'`

#echo $gpu_id 
port=9700
array=(${gpu_id//,/ })

for id in ${array[@]}
do 
    pid=`ps -few|grep -v grep | grep "python3 model_server.py $port" | awk '{print $2}'`
    if [ -n "${pid}" ];
    then
        DATE="`date +%F,%T`"
        echo "${DATE}  model_server ${port} is already existed... " >>/tmp/f.log
    else
        DATE="`date +%F,%T`"
        echo "${DATE}  model_server ${port} not existed, now begin to start..." >> /tmp/d.loddg
        source /etc/profile
        nohup sh /model_server/video_object_extraction_server/cron/run_models.sh ${id}  ${port} >> /tmp/f.log &
        #sh /model_server/video_object_extraction_server/cron/run_models.sh ${id}  ${port} 
       echo "${DATE}  exec 'CUDA_VISIBLE_DEVICES=${id} nohup python3 model_server.py ${port}'" >> /tmp/f.log
    fi
    port=$[ ${port} + 1 ]
done


