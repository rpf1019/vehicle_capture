import sys
import os
from timeit import time
import numpy as np
from net.tracking.deep_sort import preprocessing
from net.tracking.deep_sort import nn_matching
from net.tracking.deep_sort.tracker import Tracker
import cv2


class Tracking(object):
    def __init__(self, trk_param):
        motor_metric = nn_matching.NearestNeighborDistanceMetric("cosine", trk_param.track_max_cosine_distance, trk_param.track_motor_nn_budget)
        nonmotor_metric = nn_matching.NearestNeighborDistanceMetric("cosine", trk_param.track_max_cosine_distance, trk_param.track_nonmotor_nn_budget)
        self.motor_tracker = Tracker(motor_metric, 0.7, trk_param.track_motor_max_age)
        self.nonmotor_tracker = Tracker(nonmotor_metric, 0.8, trk_param.track_nonmotor_max_age, 2)#max_iou_distance=0.8, max_age=3, n_init=3

    def run(self, motor_detections_for_tracking, nonmotor_detections_for_tracking):
        self.motor_tracker.predict()
        motor_matches = self.motor_tracker.update(motor_detections_for_tracking)
        my_motor_tracks = self.__generate_my_tracks(self.motor_tracker.tracks, motor_matches, motor_detections_for_tracking)
        self.motor_tracker.tracks = [t for t in self.motor_tracker.tracks if not t.is_deleted()]#delete deleted_trakcs
        self.nonmotor_tracker.predict()
        nonmotor_matches = self.nonmotor_tracker.update(nonmotor_detections_for_tracking)
        my_nonmotor_tracks = self.__generate_my_tracks(self.nonmotor_tracker.tracks, nonmotor_matches, nonmotor_detections_for_tracking)
        self.nonmotor_tracker.tracks = [t for t in self.nonmotor_tracker.tracks if not t.is_deleted()]#delete deleted_trakcs
        return my_motor_tracks, my_nonmotor_tracks


    def __generate_my_tracks(self, tracks, matches, detections_for_tracking):
        ret_list = list()
        for i, track in enumerate(tracks):
            ifmatch  = False
            for track_idx, detection_idx in matches: #use detbbox, not track bbox
                if track_idx == i:
                    if not track.is_confirmed():
                        continue
                    ifmatch = True
                    one_track = dict()
                    corresponding_detection = detections_for_tracking[detection_idx]
                    track.conf = corresponding_detection.confidence
                    bbox = corresponding_detection.to_tlbr()
                    one_track["track_id"] = track.track_id
                    one_track["bbox"] = bbox
                    one_track["conf"] = corresponding_detection.confidence
                    one_track["time_since_update"] = track.time_since_update
                    ret_list.append(one_track)
                    break
            if not ifmatch:
                if not track.is_confirmed():
                    continue
                one_track = dict()
                one_track["track_id"] = track.track_id
                one_track["time_since_update"] = track.time_since_update
                one_track["bbox"] = [-1,-1,-1,-1]
                one_track["conf"] = -1
                ret_list.append(one_track)
            
        return ret_list
