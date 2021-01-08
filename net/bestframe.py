from __future__ import division, print_function, absolute_import
import sys
import os
import cv2
import numpy as np
import base64
import copy
import uuid
from net.selection.plate_analyzer import Plate_analyzer

class BestFrame(object):
    def __init__(self, bestframe_param):
        self.bestframe_once = BestFrameOnce(bestframe_param)
        self.motor_bestframe_extractor = MotorBestFrameExtractor(bestframe_param)
        self.nonmotor_bestframe_extractor = NonmotorBestFrameExtractor(bestframe_param)

    def run(self, allframes, frameid, startTime, motor_tracks, nonmotor_tracks, nonmotor_person_picked_boxes, frame_rate,sourceID):
        lpattrs = self.bestframe_once.run(allframes[frameid], motor_tracks)
        motor_result_list = self.motor_bestframe_extractor.save_bestframe_per_frame(allframes, frameid, startTime, motor_tracks, lpattrs, frame_rate,sourceID)
        nonmotor_result_list = self.nonmotor_bestframe_extractor.save_bestframe_per_frame(allframes, frameid, startTime, nonmotor_tracks, nonmotor_person_picked_boxes, frame_rate,sourceID)
        return motor_result_list, nonmotor_result_list

    def save_unreported_tracks(self, allframes, startTime):
        self.motor_bestframe_extractor.save_bestframe_per_video_ends(allframes, startTime)
        self.nonmotor_bestframe_extractor.save_bestframe_per_video_ends(allframes, startTime)


class BestFrameOnce(object):
    """lisence plate attr"""
    __instance = None
    __first_init = False

    def __new__(cls, bestframe_param):
        if not cls.__instance:
            cls.__instance = object.__new__(cls)
        return cls.__instance

    def __init__(self, bestframe_param):
        if not self.__first_init:
            self.plate_analyzer = Plate_analyzer(bestframe_param.lpattr_model_path)
            BestFrameOnce.__first_init = True

    def run(self, frame, tracks):
       rois = list()
       for track in tracks:
           if track["time_since_update"] > 0:  # time since update = 0 means this frame matched
               continue
           tlbr = track["bbox"]
           left, top, right, bottom = int(tlbr[0]), int(tlbr[1]), int(tlbr[2]), int(tlbr[3])
           roi = frame[top:bottom, left:right]
           rois.append(roi)
       plate_attributes = self.plate_analyzer.run(rois)
       return plate_attributes 


class MotorBestFrameExtractor(object):
    def __init__(self, bestframe_param):
        self.bestframe_attrs_list = list()
        self.motor_maxage = bestframe_param.motor_max_age
        self.update_motor_confidence_thresh = bestframe_param.update_motor_confidence_thresh

    def save_bestframe_per_frame(self, allframes, frameid, startTime, tracks, lpattrs, frame_rate,sourceID):
        self.update_bestframe_attrs_list(allframes, frameid, startTime, tracks, lpattrs)
        result_list = self.save_bestframes(allframes, tracks, self.motor_maxage, frame_rate,sourceID)  ##each frame checks,if bf exists ,put it in final_reslts
        return result_list

    def save_bestframe_per_video_ends(self, allframes, startTime):
        for best_attr in self.bestframe_attrs_list:
            if best_attr['startTime'] == startTime:#means in this video,bf updated at least one time
                best_attr['frame'] = copy.deepcopy(allframes[best_attr['frameid']])
            else:
                pass

    def update_bestframe_attrs_list(self, allframes, frameid, startTime, tracks, lpattrs):
        currentframe_attrs = self.get_attributes(allframes, frameid, startTime, tracks, lpattrs)
        self.update(currentframe_attrs)

    def update_onetrack_attr(self, cur_attr, best_attr):
        best_attr['track_id'] = cur_attr['track_id']
        best_attr['frame'] = cur_attr['frame']
        best_attr['bbox'] = cur_attr['bbox']
        best_attr['license'] = cur_attr['license']
        best_attr['area'] = cur_attr['area']
        best_attr['conf'] = cur_attr['conf']
        best_attr['frameid'] = cur_attr['frameid']
        best_attr['startTime'] = cur_attr['startTime']

    def update(self, currentframe_attrs):
        historic_best_trackid_list = [] #historic best attributes trackid
        for best_attr in self.bestframe_attrs_list:
            historic_best_trackid_list.append(best_attr['track_id'])

        for cur_attr in currentframe_attrs:
            if cur_attr['conf'] < self.update_motor_confidence_thresh:
                continue
            if cur_attr['track_id'] in historic_best_trackid_list:
                best_attr = self.bestframe_attrs_list[historic_best_trackid_list.index(cur_attr['track_id'])]  # get same trkid obj
                if cur_attr['license'] > best_attr['license']:
                    self.update_onetrack_attr(cur_attr, best_attr)
                elif cur_attr['license'] == best_attr['license']:
                    if cur_attr['area'] > best_attr['area']:
                        self.update_onetrack_attr(cur_attr, best_attr)
                    else:
                        pass
                else:
                    pass
            else:
                self.bestframe_attrs_list.append(cur_attr)

    def get_attributes(self, allframes, frameid, startTime, tracks, lpattrs):
        attributes = []
        plate_attr_list_index = 0
        for trk_seq, track in enumerate(tracks):
            if track["time_since_update"] > 0:  # time since update = 0 means this frame matched
                continue
            tlbr = track["bbox"]
            left, top, right, bottom = int(tlbr[0]), int(tlbr[1]), int(tlbr[2]), int(tlbr[3])
            area = (right - left + 1) * (bottom - top + 1)
            one_attr = dict()
            one_attr['conf'] = track["conf"] 
            one_attr['track_id'] = track["track_id"]
            one_attr['frame'] = 'current_video'#we think bf in this video, if not,when video ends,best_attr will save bestframe image
            one_attr['bbox'] = [left, top, right, bottom]  # x1,y1,x2,y2
            one_attr['license'] = lpattrs[plate_attr_list_index]
            one_attr['area'] = area
            one_attr['frameid'] = frameid#frameid and starttime matched, startTime + 40 x frameid = absolute capture time
            one_attr['startTime'] = startTime
            plate_attr_list_index += 1
            attributes.append(one_attr)
        return attributes

    def save_bestframes(self, allframes, tracks, maxage, frame_rate,sourceID):#when a confirmed track's age is maxage(deepsort age_max), save it's bestframe
        result_list = list()
        for track in tracks:
            if track["time_since_update"] == maxage:#when a vehicle is gone, before the tracker is deleted, save best frame
                for bseq, best_attr in enumerate(self.bestframe_attrs_list):
                    if best_attr['track_id'] == track["track_id"]:
                        if best_attr['conf'] > self.update_motor_confidence_thresh:
                            record_dict = dict()
                            input_dict = dict()
                            frameid = best_attr['frameid']
                            startTime = best_attr['startTime']#frameid and starttime matched, startTime + 40 x frameid = absolute capture time
                            input_dict["IMAGETYPE"] = "20"
                            input_dict["CAPTURETIME"] =  startTime + int(frameid * 1/ frame_rate)
                            input_dict["SOURCEID"] = sourceID
                            output_dict = dict()
                            vehicle_object_list=list()
                            vehicle_object_dict=dict()
                            area = list()
                            x1 = best_attr['bbox'][0]
                            y1 = best_attr['bbox'][1]
                            x2 = best_attr['bbox'][2]
                            y2 = best_attr['bbox'][3]
                            rect_dict = {"X1":x1,"Y1":y1,"X2":x2,"Y2":y2}
                            if best_attr['frame'] == 'current_video':#means vehicle only appers in this video, no cross videos
                                best_frame = allframes[frameid]
                                image = cv2.imencode('.jpg', best_frame)[1]
                                best_frame_b64 = str(base64.b64encode(image))[2:-1]
                                input_dict["IMAGEDATA"] = best_frame_b64
                                vehicle_best_frame = best_frame[y1:y2,x1:x2]
                                vehicle_img = cv2.imencode(".jpg",vehicle_best_frame)[1]
                                vehicle_best_frame_b64 = str(base64.b64encode(vehicle_img))[2:-1]
                                vehicle_object_dict["VEHICLEIDIMAGE"] = vehicle_best_frame_b64
                            else:
                                best_frame = best_attr['frame']
                                image = cv2.imencode('.jpg', best_frame)[1]
                                best_frame_b64 = str(base64.b64encode(image))[2:-1]
                                input_dict["IMAGEDATA"] = best_frame_b64
                                vehicle_best_frame = best_frame[y1:y2,x1:x2]
                                vehicle_img = cv2.imencode(".jpg",vehicle_best_frame)[1]
                                vehicle_best_frame_b64 = str(base64.b64encode(vehicle_img))[2:-1]
                                vehicle_object_dict["VEHICLEIDIMAGE"] = vehicle_best_frame_b64
                            record_dict["INPUT"] = input_dict
                            vehicle_object_dict["RECT"] = rect_dict
                            vehicle_object_list.append(vehicle_object_dict)
                            output_dict["VEHICLEOBJECTSET"] = vehicle_object_list
                            output_dict["CAPTURETIME"] = startTime + int(frameid * 1 / frame_rate)
                            output_dict["SOURCEID"] = sourceID
                            record_dict["OUTPUT"] = output_dict
                            result_list.append(record_dict)
                        del self.bestframe_attrs_list[bseq]#delete reported bestattr in case of it gets too long
        return result_list

class NonmotorBestFrameExtractor(object):
    def __init__(self, bestframe_param):
        self.bestframe_attrs_list = list()
        self.nonmotor_maxage = bestframe_param.nonmotor_max_age
        self.update_nonmotor_confidence_thresh = bestframe_param.update_nonmotor_confidence_thresh

    def save_bestframe_per_frame(self, allframes, frameid, startTime, tracks, person_boxes, frame_rate,sourceID):
        self.update_bestframe_attrs_list(allframes, frameid, startTime, tracks, person_boxes)
        result_list = self.save_bestframes(allframes, tracks, self.nonmotor_maxage, frame_rate,sourceID)  ##each frame checks,if bf exists ,put it in final_reslts
        return result_list

    def save_bestframe_per_video_ends(self, allframes, startTime):
        for best_attr in self.bestframe_attrs_list:
            if best_attr['startTime'] == startTime:#means in this video,bf updated at least one time
                best_attr['frame'] = copy.deepcopy(allframes[best_attr['frameid']])
            else:
                pass

    def update_bestframe_attrs_list(self, allframes, frameid, startTime, tracks, person_boxes):
        currentframe_attrs = self.get_attributes(allframes, frameid, startTime, tracks, person_boxes)
        self.update(currentframe_attrs)

    def update_onetrack_attr(self, cur_attr, best_attr):
        best_attr['track_id'] = cur_attr['track_id']
        best_attr['frame'] = cur_attr['frame']
        best_attr['bbox'] = cur_attr['bbox']
        best_attr['ratio'] = cur_attr['ratio']
        best_attr['area'] = cur_attr['area']
        best_attr['conf'] = cur_attr['conf']
        best_attr['frameid'] = cur_attr['frameid']
        best_attr['startTime'] = cur_attr['startTime']
        best_attr['person_boxes'] = cur_attr['person_boxes']
    
    def update(self, currentframe_attrs):
        historic_best_trackid_list = [] #historic best attributes trackid
        for best_attr in self.bestframe_attrs_list:
            historic_best_trackid_list.append(best_attr['track_id'])

        for cur_attr in currentframe_attrs:
            if cur_attr['conf'] < self.update_nonmotor_confidence_thresh:
                continue
            if cur_attr['track_id'] in historic_best_trackid_list:
                best_attr = self.bestframe_attrs_list[historic_best_trackid_list.index(cur_attr['track_id'])]  # get same trkid obj
                if cur_attr['ratio'] >= 1 and  best_attr['ratio'] < 1:
                    self.update_onetrack_attr(cur_attr, best_attr)
                elif cur_attr['ratio'] >= 1 and  best_attr['ratio'] >= 1:
                    if cur_attr['ratio'] * cur_attr['ratio'] * cur_attr['area'] >= best_attr['ratio'] * best_attr['ratio'] * best_attr['area']:#square ratio x area 
                        self.update_onetrack_attr(cur_attr, best_attr)
                    else:
                        pass
                elif cur_attr['ratio'] < 1 and  best_attr['ratio'] < 1:
                    if cur_attr['area'] > best_attr['area']:
                        self.update_onetrack_attr(cur_attr, best_attr)
                    else:
                        pass
                else:
                    pass
            else:
                self.bestframe_attrs_list.append(cur_attr)


    def get_attributes(self, allframes, frameid, startTime, tracks, person_boxes):
        attributes = list()
        for trk_seq, track in enumerate(tracks):
            if track["time_since_update"] > 0:  # time since update = 0 means this frame matched
                continue
            tlbr = track["bbox"]
            left, top, right, bottom = int(tlbr[0]), int(tlbr[1]), int(tlbr[2]), int(tlbr[3])
            ratio = (right - left + 1) / (bottom - top + 1)#bigger is better
            area = (right - left + 1) * (bottom - top + 1)
            one_attr = dict()
            one_attr['conf'] = track["conf"]
            one_attr['track_id'] = track["track_id"]
            one_attr['frame'] = 'current_video'#we think bf in this video, if not,when video ends,best_attr will save bestframe image
            one_attr['bbox'] = [left, top, right, bottom]  # x1,y1,x2,y2
            one_attr['ratio'] = ratio
            one_attr['area'] = area
            one_attr['frameid'] = frameid#frameid and starttime matched, startTime + 40 x frameid = absolute capture time
            one_attr['startTime'] = startTime
            one_attr['person_boxes'] = self.__get_person_boxes(tlbr, person_boxes)#intersection over person > 0.4
            attributes.append(one_attr)
        return attributes

    def save_bestframes(self, allframes, tracks, maxage, frame_rate,sourceID):#when a confirmed track's age is maxage(deepsort age_max), save it's bestframe
        result_list = list()
        for track in tracks:
            if track["time_since_update"] == maxage:#when a vehicle is gone, before the tracker is deleted, save best frame
                for bseq, best_attr in enumerate(self.bestframe_attrs_list):
                    if best_attr['track_id'] == track["track_id"]:
                        if best_attr['conf'] > self.update_nonmotor_confidence_thresh:
                            record_dict = dict()
                            input_dict = dict()
                            frameid = best_attr['frameid']
                            startTime = best_attr['startTime']#frameid and starttime matched, startTime + 40 x frameid = absolute capture time
                            input_dict["IMAGETYPE"] = "20"
                            input_dict["CAPTURETIME"] =  startTime + int(frameid * 1 / frame_rate)
                            input_dict["SOURCEID"] = sourceID
                            output_dict = dict()
                            vehicle_object_list=list()
                            vehicle_object_dict=dict()
                            person_object_list = list()
                            nonmotor_area = list()
                            x1 = best_attr['bbox'][0]
                            y1 = best_attr['bbox'][1]
                            x2 = best_attr['bbox'][2]
                            y2 = best_attr['bbox'][3]
                            nonmotor_rect_dict = {"X1":x1,"Y1":y1,"X2":x2,"Y2":y2}
                            referenceid = str(uuid.uuid1())
                            if best_attr['frame'] == 'current_video':#means vehicle only appers in this video, no cross videos
                                best_frame = allframes[frameid]
                                image = cv2.imencode('.jpg', best_frame)[1]
                                best_frame_b64 = str(base64.b64encode(image))[2:-1]
                                input_dict["IMAGEDATA"] = best_frame_b64
                                vehicle_best_frame = best_frame[y1:y2,x1:x2]
                                vehicle_img = cv2.imencode(".jpg",vehicle_best_frame)[1]
                                vehicle_best_frame_b64 = str(base64.b64encode(vehicle_img))[2:-1]
                                vehicle_object_dict["NONMOTORVEHICLEIMAGE"] = vehicle_best_frame_b64
                                vehicle_object_dict["REFERENCEID"] = referenceid
                                for box in best_attr["person_boxes"]:
                                    person_area = list()
                                    x1 = box[0]
                                    y1 = box[1]
                                    x2 = box[2]
                                    y2 = box[3]
                                    person_rect_dict = {"X1":x1,"Y1":y1,"X2":x2,"Y2":y2}
                                    person_best_frame = best_frame[y1:y2,x1:x2]
                                    person_img = cv2.imencode(".jpg",person_best_frame)[1]
                                    person_best_frame_b64 = str(base64.b64encode(person_img))[2:-1]
                                    person_object_dict = dict()
                                    person_object_dict["PERSONIMAGE"] = person_best_frame_b64################?
                                    person_object_dict["RECT"] = person_rect_dict
                                    person_object_dict["REFERENCEID"] = referenceid
                                    person_object_list.append(person_object_dict)
                            else:
                                best_frame = best_attr['frame']
                                image = cv2.imencode('.jpg', best_frame)[1]
                                best_frame_b64 = str(base64.b64encode(image))[2:-1]
                                input_dict["IMAGEDATA"] = best_frame_b64
                                vehicle_best_frame = best_frame[y1:y2,x1:x2]
                                vehicle_img = cv2.imencode(".jpg",vehicle_best_frame)[1]
                                vehicle_best_frame_b64 = str(base64.b64encode(vehicle_img))[2:-1]
                                vehicle_object_dict["NONMOTORVEHICLEIMAGE"] = vehicle_best_frame_b64
                                vehicle_object_dict["REFERENCEID"] = referenceid
                                for box in best_attr["person_boxes"]:
                                    person_area = list()
                                    x1 = box[0]
                                    y1 = box[1]
                                    x2 = box[2]
                                    y2 = box[3]
                                    person_rect_dict = {"X1":x1,"Y1":y1,"X2":x2,"Y2":y2}
                                    person_best_frame = best_frame[y1:y2,x1:x2]
                                    person_img = cv2.imencode(".jpg",person_best_frame)[1]
                                    person_best_frame_b64 = str(base64.b64encode(person_img))[2:-1]
                                    person_object_dict = dict()
                                    person_object_dict["PERSONIMAGE"] = person_best_frame_b64################?
                                    person_object_dict["RECT"] = person_rect_dict
                                    person_object_dict["REFERENCEID"] = referenceid
                                    person_object_list.append(person_object_dict)
                            record_dict["INPUT"] = input_dict
                            vehicle_object_dict["RECT"] = nonmotor_rect_dict
                            if len(best_attr["person_boxes"]) == 1:
                                vehicle_object_dict["NONMOTORPERSONNUM"] = "0"
                            if  len(best_attr["person_boxes"]) > 1:
                                vehicle_object_dict["NONMOTORPERSONNUM"] = "1" 
                            vehicle_object_list.append(vehicle_object_dict)
                            output_dict["NONMOTORVEHICLEOBJECTSET"] = vehicle_object_list
                            if len(person_object_list) > 0:
                                output_dict["PERSONOBJECTSET"] = person_object_list
                            output_dict["CAPTURETIME"] = startTime + int(frameid * 1 / frame_rate)
                            output_dict["SOURCEID"] = sourceID
                            record_dict["OUTPUT"] = output_dict
                            result_list.append(record_dict)
                        del self.bestframe_attrs_list[bseq]#delete reported bestattr in case of it gets too long
        return result_list

    def __get_person_boxes(self, tlbr, person_boxes):
        ret_list = list()
        if person_boxes is not None:
            for box in person_boxes:
                if self.__get_IOP(tlbr, box) > 0.4:
                    ret_list.append([int(box[0]), int(box[1]), int(box[0]) + int(box[2]), int(box[1]) + int(box[3])])
        return ret_list

    def __get_IOP(self, nonmotor_box, person_box):
        xmin1, ymin1, xmax1, ymax1 = nonmotor_box[0], nonmotor_box[1], nonmotor_box[2], nonmotor_box[3]
        xmin2, ymin2, xmax2, ymax2 = person_box[0], person_box[1], person_box[0] +  person_box[2], person_box[1] + person_box[3]

        #s1 = (xmax1 - xmin1) * (ymax1 - ymin1)  # C的面积
        s2 = (xmax2 - xmin2) * (ymax2 - ymin2)  # G的面积
 
        xmin = max(xmin1, xmin2)
        ymin = max(ymin1, ymin2)
        xmax = min(xmax1, xmax2)
        ymax = min(ymax1, ymax2)
 
        w = max(0, xmax - xmin)
        h = max(0, ymax - ymin)
        area = w * h  #intersection
        iop = area / s2
        return iop

    

