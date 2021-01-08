from __future__ import division, print_function, absolute_import
import sys
import os
import cv2
import numpy as np
from net.detection.object_detection import Detection
from net.tracking.vehicle_encoding import Encoding
from net.tracking.object_tracking import Tracking
from net.tracking.deep_sort.detection import DetectionDeepSort

class DBT(object):
    def __init__(self, det_param, trk_param):
        self.dbt_once = DBTOnce(det_param, trk_param)
        self.dbt_tracker = DBTTracker(trk_param) 
        self.frame_seq = 0

    def run(self, frame, roi_param):
        motor_detections_for_tracking, nonmotor_detections_for_tracking, nonmotor_person_picked_boxes = self.dbt_once.run(frame, roi_param)
        motor_tracks, nonmotor_tracks = self.dbt_tracker.run(motor_detections_for_tracking, nonmotor_detections_for_tracking)
        #self.__save_tracks(frame.copy(), motor_tracks, nonmotor_tracks)
        return motor_tracks, nonmotor_tracks, nonmotor_person_picked_boxes

    def __save_tracks(self, frame, motor_tracks, nonmotor_tracks):
        for seq, track in enumerate(motor_tracks):
            if track["time_since_update"] > 0:  # time since update = 0 means this frame matched
                continue
            xmin, ymin, xmax, ymax = int(track["bbox"][0]), int(track["bbox"][1]), int(track["bbox"][2]), int(track["bbox"][3])
            cv2.rectangle(frame, (xmin,ymin), (xmax, ymax), (255, 0, 0), 3)#################
            cv2.putText(frame, "track_id:"+str(track["track_id"]) + "seq:"+str(seq), (xmin, ymin - 7), 0, 1.2, (255, 0, 0), 3)
        for seq, track in enumerate(nonmotor_tracks):
            if track["time_since_update"] > 0:  # time since update = 0 means this frame matched
                continue
            xmin, ymin, xmax, ymax = int(track["bbox"][0]), int(track["bbox"][1]), int(track["bbox"][2]), int(track["bbox"][3])
            cv2.rectangle(frame, (xmin,ymin), (xmax, ymax), (0, 0, 255), 3)#################
            cv2.putText(frame, "track_id:"+str(track["track_id"]) + "seq:"+str(seq), (xmin, ymin - 7), 0, 1.2, (0, 0, 255), 3)
        cv2.imwrite("./trkframes/" + str(self.frame_seq) + ".jpg", frame)
        self.frame_seq += 1



class DBTOnce(object):
    """
    all_boxes_detection, boxes_picking, picked_boxes_encoding
    """
    __instance = None
    __first_init = False

    def __new__(cls, det_param, trk_param):
        if not cls.__instance:
            cls.__instance = object.__new__(cls)
        return cls.__instance

    def __init__(self, det_param, trk_param):
        if not self.__first_init:
            self.object_detection = Detection(det_param.detect_model_path)
            self.detect_confidence_thresh = det_param.detect_confidence_thresh
            self.vehicle_encoding = Encoding(trk_param.feature_model_path)
            self.frame_seq = 0
            DBTOnce.__first_init = True

    def run(self, frame, roi_param):
        boxes = self.object_detection.run(frame)#all detection results
        motor_picked_boxes, nonmotor_picked_boxes, nonmotor_person_picked_boxes = self.object_detection.pick_boxes(boxes, self.detect_confidence_thresh, roi_param)#in roi detection ret
        #self.__save_dets(frame.copy(), motor_picked_boxes, nonmotor_picked_boxes, nonmotor_person_picked_boxes)
        if motor_picked_boxes is None:
            motor_detections_for_tracking = []
            if nonmotor_picked_boxes is None:
                nonmotor_detections_for_tracking = []
                return motor_detections_for_tracking, nonmotor_detections_for_tracking, nonmotor_person_picked_boxes
            else:
                nonmotor_detections_for_tracking = [DetectionDeepSort(picked_box[:4], picked_box[4], [1,1]) for picked_box in nonmotor_picked_boxes]
                return motor_detections_for_tracking, nonmotor_detections_for_tracking, nonmotor_person_picked_boxes
        else:
            features = self.vehicle_encoding.run(frame, motor_picked_boxes)
            motor_detections_for_tracking = [DetectionDeepSort(picked_box[:4], picked_box[4], feature) for picked_box, feature in zip(motor_picked_boxes, features)]
            if nonmotor_picked_boxes is None:
                nonmotor_detections_for_tracking = []
                return motor_detections_for_tracking, nonmotor_detections_for_tracking, nonmotor_person_picked_boxes
            else:
                nonmotor_detections_for_tracking = [DetectionDeepSort(picked_box[:4], picked_box[4], [1,1]) for picked_box in nonmotor_picked_boxes]
                return motor_detections_for_tracking, nonmotor_detections_for_tracking, nonmotor_person_picked_boxes

    def __save_dets(self, frame, motor_picked_boxes, nonmotor_picked_boxes, nonmotor_person_picked_boxes):
        cv2.imwrite("./oriframes/" + str(self.frame_seq) + ".jpg", frame)
        if motor_picked_boxes is not None:
            for bbox in motor_picked_boxes:
                xmin, ymin, w, h = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
                cv2.rectangle(frame, (xmin,ymin), (xmin + w, ymin + h), (255, 0, 0), 3)
                cv2.putText(frame, "conf:"+str(bbox[4]), (xmin, ymin - 7), 0, 1.2, (255, 0, 0), 3)
        if nonmotor_picked_boxes is not None:
            for bbox in nonmotor_picked_boxes:
                xmin, ymin, w, h = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
                cv2.rectangle(frame, (xmin,ymin), (xmin + w, ymin + h), (0, 255, 0), 3)
                cv2.putText(frame, "conf:"+str(bbox[4]), (xmin, ymin - 7), 0, 1.2, (0, 255, 0), 3)
        if nonmotor_person_picked_boxes is not None:
            for bbox in nonmotor_person_picked_boxes:
                xmin, ymin, w, h = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
                cv2.rectangle(frame, (xmin,ymin), (xmin + w, ymin + h), (0, 0, 255), 3)
                cv2.putText(frame, "conf:"+str(bbox[4]), (xmin, ymin - 7), 0, 1.2, (0, 0, 255), 3)
        cv2.imwrite("./detframes/" + str(self.frame_seq) + ".jpg", frame)
        self.frame_seq += 1

class DBTTracker(object):
    """trackers for more than 1 sourceids"""
    def __init__(self, trk_param):
        self.vehicle_tracking = Tracking(trk_param)# with param

    def run(self, motor_detections_for_tracking, nonmotor_detections_for_tracking):
        motor_tracks, nonmotor_tracks = self.vehicle_tracking.run(motor_detections_for_tracking, nonmotor_detections_for_tracking)
        return motor_tracks, nonmotor_tracks#"track_id,bbox,conf,time_since_update"
