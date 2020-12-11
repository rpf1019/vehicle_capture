#/bin/bash sh


id=$1
port=$2

cd /model_server/video_object_extraction_server

CUDA_VISIBLE_DEVICES=${id} nohup  python3 model_server.py ${port} & >>/tmp/f.log

while true
do
    python test_service.py ${port}
    res=`echo $?`
    echo ${res}
    if [ ${res} -eq 1 ]
    then 
        sleep 2
    else
        break
    fi
done


