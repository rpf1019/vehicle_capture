from __future__ import division, print_function, absolute_import
import sys
import os
from timeit import time
import warnings
import cv2
import numpy as np
from CaptureDecode import capture_decode
from net.dbt import DBT
from net.bestframe import BestFrame
import base64
from net.config import Config
import json
import copy
warnings.filterwarnings('ignore')
conf = Config('./conf/model.conf')

# tracker default params and sourceID params
detect_confidence_thresh = float(str(conf.get('video_object_extraction','detect_confidence_thresh')))
update_motor_confidence_thresh = float(str(conf.get('video_object_extraction','update_motor_confidence_thresh')))
update_nonmotor_confidence_thresh = float(str(conf.get('video_object_extraction','update_nonmotor_confidence_thresh')))
track_max_cosine_distance = float(str(conf.get('video_object_extraction','track_max_cosine_distance')))
track_motor_nn_budget = int(str(conf.get('video_object_extraction','track_motor_nn_budget')))
track_motor_max_age = int(str(conf.get('video_object_extraction','track_motor_max_age')))
track_nonmotor_nn_budget = int(str(conf.get('video_object_extraction','track_nonmotor_nn_budget')))
track_nonmotor_max_age = int(str(conf.get('video_object_extraction','track_nonmotor_max_age')))
track_skip_num = int(str(conf.get('video_object_extraction','track_skip_num')))
detect_model_path = conf.get('video_object_extraction','detect_model_path')
feature_model_path = conf.get('video_object_extraction','feature_model_path')
lpattr_model_path = conf.get('video_object_extraction','lpattr_model_path')
default_frame_rate = float(str(conf.get('video_object_extraction','default_frame_rate')))
default_small_box_ratio = float(str(conf.get('video_object_extraction','default_small_box_ratio')))




class DetParam(object):
    """params setting of detection"""
    def __init__(self):
        self.detect_model_path = detect_model_path
        self.detect_confidence_thresh = detect_confidence_thresh

class TrkParam(object):
    """params setting of tracking"""
    def __init__(self):
        self.feature_model_path = feature_model_path
        self.track_max_cosine_distance = track_max_cosine_distance
        self.track_motor_nn_budget = track_motor_nn_budget
        self.track_motor_max_age = track_motor_max_age
        self.track_nonmotor_nn_budget = track_nonmotor_nn_budget
        self.track_nonmotor_max_age = track_nonmotor_max_age

class ROIParam(object):
    """params settings of ROI"""
    def __init__(self, record):
        if "DETECTAREA" in list(record["INPUT"].keys()):
            area = record["INPUT"]["DETECTAREA"]
            self.hullIndex = self.__calc_hullIndex(area)
        else:
            self.hullIndex = None
        
        self.min_width = record["INPUT"]["MINWIDTH"] if "MINWIDTH" in list(record["INPUT"].keys()) else default_small_box_ratio
        self.min_height = record["INPUT"]["MINHEIGHT"] if "MINHEIGHT" in list(record["INPUT"].keys()) else default_small_box_ratio
        self.max_width = record["INPUT"]["MAXWIDTH"] if "MAXWIDTH" in list(record["INPUT"].keys()) else 1
        self.max_height = record["INPUT"]["MAXHEIGHT"] if "MAXHEIGHT" in list(record["INPUT"].keys()) else 1

    def __calc_hullIndex(self, area):
        points = []
        for point in area:
            x = int(point[0])
            y = int(point[1])
            points.append([x,y])
        points_array = np.array(points)
        hullIndex = cv2.convexHull(points_array, returnPoints = True)
        return hullIndex

class BestFrameParam(object):
    """params setting of bestframe"""
    def __init__(self, ):
        self.lpattr_model_path = lpattr_model_path
        self.update_motor_confidence_thresh = update_motor_confidence_thresh
        self.update_nonmotor_confidence_thresh = update_nonmotor_confidence_thresh
        self.motor_max_age = track_motor_max_age
        self.nonmotor_max_age = track_nonmotor_max_age

class VideoObjectExtraction(object):
    def __init__(self):
        self.det_param = DetParam()
        self.trk_param = TrkParam()
        self.bestframe_param = BestFrameParam()
        self.dbt = DBT(self.det_param, self.trk_param)
        self.bestframe = BestFrame(self.bestframe_param)
        self.sourceid = None


    def run(self, record, logger):
        sourceID = record["INPUT"]["SOURCEID"]
        logger.info("sourceid: {} ".format(sourceID))
        if self.sourceid is None:
            self.sourceid = sourceID
            self.roi_param = ROIParam(record)
        elif self.sourceid != sourceID:
            if sourceID == "0102030405":
                empty_dict = dict()
                record_dict = dict()
                record_dict["INPUT"] = empty_dict
                record_dict["OUTPUT"] = empty_dict
                recordset = list()
                recordset.append(record_dict)
                return recordset
            else:
                self.sourceid = sourceID
                self.dbt.dbt_tracker.vehicle_tracking.motor_tracker.tracks.clear()
                self.dbt.dbt_tracker.vehicle_tracking.nonmotor_tracker.tracks.clear()
                self.bestframe.motor_bestframe_extractor.bestframe_attrs_list.clear()
                self.bestframe.nonmotor_bestframe_extractor.bestframe_attrs_list.clear()
                self.roi_param = ROIParam(record)

        video_binary = base64.b64decode(record["INPUT"]['VIDEODATA'])
        try:
            decoder = capture_decode(video_binary, False, 50)
            flag = decoder.init_ctx()
            if flag:
                allframes = decoder.Capture_BatchDecode()
            else:
                allframes = []
            logger.debug('video decode finish,total {} frames'.format(len(allframes)))
        except BaseException as e:
            logger.exception(e)
            logger.error("video decode error")
        startTime = record["INPUT"]['STARTTIME']
        logger.info("starttime:{}, videolength:{}".format(startTime, len(allframes)))

        skip_num = track_skip_num
        frame_rate = record["INPUT"]["FPS"] if "FPS" in list(record["INPUT"].keys()) else default_frame_rate
        ret = list()

        for frameid, frame in enumerate(allframes):
            if frameid % (skip_num + 1) == 0:
                print("frameid is {}".format(frameid))
                motor_tracks, nonmotor_tracks, nonmotor_person_picked_boxes = self.dbt.run(frame, self.roi_param)
                motor_result_list, nonmotor_result_list = self.bestframe.run(allframes, frameid, startTime, motor_tracks, nonmotor_tracks, nonmotor_person_picked_boxes, frame_rate,sourceID)
                if len(motor_result_list) > 0:
                    ret.extend(motor_result_list)
                if len(nonmotor_result_list) > 0:
                    ret.extend(nonmotor_result_list)
        self.bestframe.save_unreported_tracks(allframes, startTime)
        return ret


