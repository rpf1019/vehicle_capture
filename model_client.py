#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  File  : model_client.py
#  Author: pfren
#  Time  : 2020/04/10
#
#  Copyright 2020

import os
import base64
import requests
import sys
import cv2
import json
import socket
import numpy as np
import uuid



port = sys.argv[1]
fileDir = sys.argv[2]

COST_TIME_THRESH = 100000
sys.getdefaultencoding()


def generate_request(filename, starttim):
    request = {}
    noid = str(uuid.uuid1())
    sourceID = "2012009091"
    videoData = open(filename.strip(), 'rb').read()
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
    record["MAXHEIGHT"] = 2008
    record["MAXWIDTH"] = 3392
    record["DETECTAREA"] = [[693,165],[2681,125],[3345,645],[3337,1970],[41,1960],[33,1153]]
    input_params["INPUT"] = record
    recordset.append(input_params)
    request["NOID"] = noid
    request["RECORDSET"] = recordset
    return request

def run(port, filedir, starttime=0):
    filenames = os.listdir(filedir)
    filenames.sort()
    for i, filename in enumerate(filenames):
        print("processing video:{}".format(filename))
        req = generate_request(os.path.join(filedir, filename), starttime+i*10000)
        #with open('./request.json','w') as f:
        #    json.dump(req, f)
        myname = socket.getfqdn(socket.gethostname())
        myaddr = "21.3.16.20"#socket.gethostbyname(myname)
        url = 'http://'+str(myaddr)+':'+str(port)+'/multiMedia/computing/MotorVehicleFrameExtract'
        r = requests.post(url.strip(), json=req, timeout=COST_TIME_THRESH, headers={'Connection':'close'})
        response = r.json()
        #with open('./result.json','w') as f:
        #    json.dump(response,f)
        print("process video complete,get {} bfs".format(len(response["RECORDSET"])))
        for bestframe in response["RECORDSET"]:
            best_frame = bestframe["INPUT"]["IMAGEDATA"]
            best_frame = base64.b64decode(best_frame)
            best_frame = np.fromstring(best_frame, np.uint8)
            img = cv2.imdecode(best_frame, cv2.COLOR_RGB2BGR)
            cv2.imwrite('./201/{}_VEHICLE_BACKGROUND.jpg'.format(bestframe["INPUT"]["CAPTURETIME"]), img)
            if "VEHICLEOBJECTSET" in bestframe["OUTPUT"].keys():
                for elemet in bestframe["OUTPUT"]["VEHICLEOBJECTSET"]:
                    vehicle_best_frame = elemet["VEHICLEIDIMAGE"]
                    vehicle_best_frame = base64.b64decode(vehicle_best_frame)
                    vehicle_best_frame = np.asarray(bytearray(vehicle_best_frame), dtype='uint8')
                    vehicle_img = cv2.imdecode(vehicle_best_frame, cv2.IMREAD_COLOR)
#                   vehicle_best_frame = np.fromstring(vehicle_best_frame, np.uint8)
#                   vehicle_img = cv2.imdecode(vehicle_best_frame, cv2.COLOR_RGB2BGR)
                    rect = elemet["RECT"]
                    print("motor rect: ",rect)
                    cv2.imwrite('./201/{}_MOTOR_RECT{}.jpg'.format(bestframe["INPUT"]["CAPTURETIME"], rect), vehicle_img)
            if "NONMOTORVEHICLEOBJECTSET" in bestframe["OUTPUT"]:
                for elemet in bestframe["OUTPUT"]["NONMOTORVEHICLEOBJECTSET"]:
                    vehicle_best_frame = elemet["NONMOTORVEHICLEIMAGE"]
                    vehicle_best_frame = base64.b64decode(vehicle_best_frame)
                    vehicle_best_frame = np.fromstring(vehicle_best_frame, np.uint8)
                    vehicle_img = cv2.imdecode(vehicle_best_frame, cv2.IMREAD_COLOR)
                    rect = elemet["RECT"]
                    print("nonmotor rect:{},uuid:{}".format(rect, elemet["REFERENCEID"]))
                    cv2.imwrite('./201/{}_NONMOTOR_RECT{}.jpg'.format(bestframe["INPUT"]["CAPTURETIME"], rect), vehicle_img)
            if "PERSONOBJECTSET" in bestframe["OUTPUT"]:
                for elemet in bestframe["OUTPUT"]["PERSONOBJECTSET"]:
                    vehicle_best_frame = elemet["PERSONIMAGE"]
                    vehicle_best_frame = base64.b64decode(vehicle_best_frame)
                    vehicle_best_frame = np.fromstring(vehicle_best_frame, np.uint8)
                    vehicle_img = cv2.imdecode(vehicle_best_frame, cv2.COLOR_RGB2BGR)
                    rect = elemet["RECT"]
                    print("person rect:{}, uuid:{}".format(rect, elemet["REFERENCEID"]))
                    cv2.imwrite('./201/{}_PERSON_RECT{}.jpg'.format(bestframe["INPUT"]["CAPTURETIME"], rect), vehicle_img)


if __name__ == '__main__':
    run(port, fileDir)
