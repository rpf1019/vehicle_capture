#!/usr/bin/env python
# -*- coding: utf-8 -*-


import uuid, time, math
from flask_restful import abort

#响应状态码
class ResponseCode:
    MULTIMEDIA_SUCCESS = 1200
    MULTIMEDIA_BAD_REQUEST = 1201
    MULTIMEDIA_SERVER_ERROR = 1203

def generate_response(startTime=0, results=dict() ,noid=str(uuid.uuid1()), message='MULTIMEDIA_SUCCESS',
                      status=ResponseCode.MULTIMEDIA_SUCCESS):
    endTime = time.time()
    costTime = int(math.ceil((endTime-startTime)*1000))
    return {
        'NOID': noid,
        'STATUSCODE': str(status),
        'MSG': message,
        'COSTTIME': costTime,
        'RECORDSET': results["RECORDSET"],
    }

def my_abort(http_status_code, message, noid=str(uuid.uuid1()), *args, **kwargs):
    startTime = time.time()
    if http_status_code == 400:
        try:
            for k,v in message.items():
#                message = "%s %s"%(k, v)
                message = "%s"%(v)
        except:
            pass
        results={}
        results['RECORDSET']=[]
        abort(400, **generate_response(startTime=startTime, results=results,noid=noid, message=message, status=ResponseCode.MULTIMEDIA_BAD_REQUEST))
    abort(http_status_code)
