# -*- coding: utf-8 -*-
#  @Time      : 2020/10/21
#  @Author    : pfren
#  @FileName  : model_server.py
#  Copyright 2020  FiberHome  renpengfei6748@fiberhome.xa.com
from __future__ import division, print_function, absolute_import
import sys
import uuid, time, socket, base64
import requests,flask_restful
from flask import Flask, jsonify
import math
from flask_restful import reqparse, Api, Resource
from werkzeug.exceptions import HTTPException
import server_logging 
from net.response import generate_response, my_abort
from net.model_error import ModelserverException, ValidationError
from net.video_object_extraction import VideoObjectExtraction

port = sys.argv[1]
logger = server_logging.get_logger(str(port))
video_object_extraction = VideoObjectExtraction()

def noid_check(values, name):
    if len(values) == 0:
        logger.error('The length of parameter {} is 0'.format(name))
        raise ValidationError
    if type(values) is not str:
        logger.error('the data type of parameter {} is not string').format(name)
        raise ValidationError
    return values

def Area_check(area):
    if len(area) < 3:
        return False
    for point in area:
        if len(point) != 2:
            return False
        if (type(point[0]) is not int) or (type(point[1]) is not int):
            return False
    return True

def record_check(values,params_name,name,check_type):
    if check_type != "int" and check_type != "float" and len(values) == 0 :
        logger.error('the  {} of parameter {} is not dict'.format(params_name,name))
        raise ValidationError
    if check_type == "dict":
        if type(values) is not dict:
            logger.error('the  {} type of {} parameter is not dict'.format(params_name,name))
            raise ValidationError
    elif check_type == "str":
        if type(values) is not str:
            logger.error('the  {} type of {} parameter is not str'.format(params_name,name))
            raise ValidationError
    elif check_type == "int":
        if type(values) is not int:
            logger.error('the  {} type of {} parameter is not int'.format(params_name,name))
            raise ValidationError
    elif check_type == "float":
        if type(values) is not float:
            logger.error('the  {} type of {} parameter is not float'.format(params_name,name))
            raise ValidationError
    elif check_type == "list":
        if type(values) is not list:
            logger.error('the  {} type of {} parameter is not list'.format(params_name,name))
            raise ValidationError

def recordset_check(values,name):
    record_check(values,"",name,"dict")

    if "INPUT" in list(values.keys()): 
        record_check(values["INPUT"],"INPUT",name,"dict")
    else:
        logger.error('param {} is not in RECORD'.format("INPUT"))
        raise ValidationError

    if "SOURCEID" in list(values["INPUT"].keys()):
        record_check(values["INPUT"]["SOURCEID"],"SOURCEID",name,"str")
    else:
        logger.error('param {} is not in INPUT'.format("SOURCEID"))
        raise ValidationError

    if "STARTTIME" in list(values["INPUT"].keys()):
        record_check(values["INPUT"]["STARTTIME"],"STARTTIME",name,"int")
    else:
        logger.error('param {} is not in INPUT'.format("STARTTIME"))
        raise ValidationError

    if "VIDEODATA" in list(values["INPUT"].keys()):
        record_check(values["INPUT"]["VIDEODATA"],"VIDEODATA",name,"str")
    else:
        logger.error('param {} is not in INPUT'.format("VIDEODATA"))
        raise ValidationError
    
    if "FPS" in list(values["INPUT"].keys()):
        record_check(values["INPUT"]["FPS"],"FPS",name,"int")
    if "MINHEIGHT" in list(values["INPUT"].keys()):
        record_check(values["INPUT"]["MINHEIGHT"],"MINHEIGHT",name,"int")
    if "MAXHEIGHT" in list(values["INPUT"].keys()):
        record_check(values["INPUT"]["MINWIDTH"],"MINWIDTH",name,"int")
    if "MAXHEIGHT" in list(values["INPUT"].keys()):
        record_check(values["INPUT"]["MAXHEIGHT"],"MAXHEIGHT",name,"int")
    if "MAXWIDTH" in list(values["INPUT"].keys()):
        record_check(values["INPUT"]["MAXWIDTH"],"MAXWIDTH",name,"int")
    if "DETECTAREA" in list(values["INPUT"].keys()):
        ret = Area_check(values["INPUT"]["DETECTAREA"])
        if not ret:
            logger.error('param {} is wrong or not complete'.format("DETECTAREA"))
            raise ValidationError

    return values

def param_parser(args):
    noid,recordset = args["NOID"],args["RECORDSET"]
    return noid,recordset

def service(args, startTime=time.time()):
    noid, recordset = param_parser(args)
    results = dict()
    record_set= list()
    try:
        logger.info("get {} videos totally, noid:{}".format(len(recordset), noid))
        for record in recordset:
            param = dict()
            ret = video_object_extraction.run(record, logger)#ret is a list of output record
            record_set.extend(ret)
        endtime = time.time()
        costTime = math.ceil((endtime-startTime)*1000)
        logger.info("finished process request, noid: {}, total time cost: {} ms".format(args["NOID"], costTime))
        results["STATUSCODE"] = "1200"
        results["MSG"] = "MULTIMEDIA_SUCCESS"
        results["RECORDSET"] = record_set
    except ModelserverException as e:
        logger.error("ModelserverException: %s" %e)
        return generate_response(startTime, results, noid=noid,message=e.errorMsg,status=1203)
    except BaseException as e:
        logger.error("BaseException: %s" %e)
        results["RECORDSET"] = record_set
        return generate_response(startTime, results, noid=noid,message=e.args,status=1203)
    return generate_response(startTime, results, noid)


class ObjectExtractionServer(Resource):

    def __init__(self):

        self.parser = reqparse.RequestParser(bundle_errors=False)
        self.parser.add_argument("NOID",  type=noid_check, required=True, 
                       help="MULTIMEDIA_BAD_REQUEST, request noid is empty or data type is not string", nullable=False)
        try:
            args_noid = self.parser.parse_args()
        except HTTPException as e:
            logger.error("httpException %s" %e)
            logger.error("errorCode: %s, errorMsg: %s" %(e.code, e.data["message"]))
            try:
                my_abort(e.code, e.data["message"])
            except AttributeError as e:
                my_abort(400,"bad request")

        self.noid = args_noid["NOID"]

    def __add_argument(self):
        self.parser.add_argument('RECORDSET', type=recordset_check, action="append",required=True,
                help='MULTIMEDIA_BAD_REQUEST,RECORDSET is empty or incomplete', nullable=False)

    def post(self):
        startTime = time.time()
        self.__add_argument()

        try:
            try:
                args = self.parser.parse_args()
                args["NOID"] = self.noid
                logger.info("get 1 request, noid: %s"%self.noid)
            except HTTPException as e:
                try:
                    my_abort(e.code, e.data["message"], self.noid)
                except AttributeError as e:
                    my_abort(400,"bad request", self.noid)
        except AttributeError as e:
            my_abort(400,"bad request", self.noid)

        return service(args, startTime)



app = Flask(__name__)
api = Api(app)

api.add_resource(ObjectExtractionServer, "/multiMedia/computing/MotorVehicleFrameExtract")

def run(port, host="0.0.0.0"):
    app.run(host=host, port=port, threaded=False, processes=1, debug=False)


if __name__ == "__main__":
    run(port)
