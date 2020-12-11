#!/usr/bin/env python
# -*- coding: utf-8 -*-

#  @Time      : 2019/08/28
#  @Author    : wangwei
#  @FileName  : test_service.py
#  Copyright 2019 FiberHome  wangwei5372@fiberhome.xa.com

import os
import base64
import requests
import sys
import cv2, json
import socket
import numpy as np
import server_logging
import uuid
import time
from net.config import Config
import server_logging

sys.getdefaultencoding()
port = sys.argv[1]
logger = server_logging.get_logger(str(port))

COST_TIME_THRESH = 60

def generate_request(fileDir):
    request = dict()
    noid = str(uuid.uuid1())
    sourceID = "0102030405"
    videoData = open(fileDir.strip(), 'rb').read()
    starttim = 10000
    videoData = base64.b64encode(videoData)
    recordset = []
    input_params = {}
    record = {}
    
    record["STARTTIME"] = starttim
    record["SOURCEID"] = sourceID
    record["VIDEODATA"] = videoData
    record["FPS"] = 12
    record["MINHEIGHT"] = 20
    record["MINWIDTH"] = 20
    record["MAXHEIGHT"] = 1080
    record["MAXWIDTH"] = 1920
    record["DETECTAREA"] = [[0,0],[2000,0],[2000,2000],[0,2000]]

    input_params["INPUT"] = record
    recordset.append(input_params)
    request["NOID"] = noid
    request["RECORDSET"] = recordset
    return request

def run(port):
    fileDir = '/model_server/video_object_extraction_server/testvideos/test.ts'
    req = generate_request(fileDir)

    myname = socket.getfqdn(socket.gethostname())
    myaddr = socket.gethostbyname(myname)
    url = 'http://'+str(myaddr)+':'+str(port)+'/multiMedia/computing/MotorVehicleFrameExtract'
    try:
        time_start = time.time()
        r = requests.post(url.strip(), json=req, timeout=COST_TIME_THRESH, headers={'Connection':'close'})
        cost_time = time.time() - time_start
    except BaseException as e:
        logger.info('post request error:%s, sys.exit(1)'%e)
        sys.exit(1)
    else:
        response = r.json()
        statusCode = response["STATUSCODE"]
        msg = response["MSG"]
        if statusCode == "1200":
            logger.info('statusCode: %s, cost time vs COST_TIME_THRESH: (%s vs %s), sys.exit(0)' \
                           %(statusCode, cost_time, COST_TIME_THRESH))
            sys.exit(0)
        elif statusCode == "1203":
            logger.info('statusCode: %s, msg: %s' %(statusCode,msg))
        else:
            logger.error('statusCode: %s , msg: %s' %(statusCode,msg))
            sys.exit(1)

if __name__ == '__main__':
    #while True:
    run(port)

