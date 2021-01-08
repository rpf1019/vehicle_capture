import sys
import os
from timeit import time
import warnings
import cv2
import numpy as np
from net.detection.yolov5.inference import Detector


class Detection(object):
    def __init__(self, det_model_path):
        super(Detection, self).__init__()
        self.yolo_detecter = Detector(det_model_path)
        self.height = 0
        self.width = 0

    def run(self, frame):
        self.height, self.width = frame.shape[:2]
        boxes = self.yolo_detecter.predict(frame)  #x1y1,x2y2,conf
        return boxes

    def pick_boxes(self, boxes, detect_confidence_thresh, roi_param):
        if boxes is None:
            return None, None, None
        else:
            motor_results = list()
            nonmotor_results = list()
            driver_results = list()
            for box in boxes:
                confidence = box[4]
                if confidence < detect_confidence_thresh:
                    continue
                box[0] = max(box[0], 1)
                box[1] = max(box[1], 1)
                box[2] = min(box[2], self.width - 2)
                box[3] = min(box[3], self.height - 2)
                x1 = box[0]
                x2 = box[2]
                y1 = box[1]
                y2 = box[3]
                label = box[5]
                #center_x = (x2 + x1) / 2
                #center_y = (y2 + y1) / 2
                point_lt = (x1, y1)
                point_rt = (x2, y1)
                point_rb = (x2, y2)
                point_lb = (x1, y2)
                rect_width = x2 - x1
                rect_height = y2 - y1
                dist = 0
                if roi_param.hullIndex is None:
                    pass
                else:
                    #dist = cv2.pointPolygonTest(roi_param.hullIndex, (center_x, center_y), False)
                    #if dist < 0:
                    #    continue
                    dist_lt = cv2.pointPolygonTest(roi_param.hullIndex, point_lt, False)
                    dist_rt = cv2.pointPolygonTest(roi_param.hullIndex, point_rt, False)
                    dist_rb = cv2.pointPolygonTest(roi_param.hullIndex, point_rb, False)
                    dist_lb = cv2.pointPolygonTest(roi_param.hullIndex, point_lb, False)
                    if min(dist_lt,dist_rt,dist_rb,dist_lb) < 0:
                        continue
                if roi_param.min_width > 1:#
                    if rect_width < roi_param.min_width:
                        continue
                else:#ratio minwidth not in input
                    if rect_width < self.width * roi_param.min_width:
                        continue
                if roi_param.min_height > 1:#
                    if rect_height < roi_param.min_height:
                        continue
                else:#ratio minwidth not in input
                    if rect_height < self.height * roi_param.min_height:
                        continue
                if roi_param.max_width > 1:#
                    if rect_width > roi_param.max_width:
                        continue
                else:#ratio minwidth not in input
                    if rect_width > self.width * roi_param.max_width:
                        continue
                if roi_param.max_height > 1:#
                    if rect_height > roi_param.max_height:
                        continue 
                else:#ratio minwidth not in input
                    if rect_height > self.height * roi_param.max_height:
                        continue
                if label == 0:#motor
                    motor_results.append(box)
                elif label == 1:#nonmotor
                    nonmotor_results.append(box)
                else:#driver
                    driver_results.append(box)

            motor_results = self.__xyxy2xywh(motor_results)
            nonmotor_results = self.__xyxy2xywh(nonmotor_results)
            driver_results = self.__xyxy2xywh(driver_results)
            #if len(results) > 0:
            #    results=np.array(results)
            #    results[:, 2] = results[:, 2] - results[:, 0]  #origin is x1y1x2y2,to ltwh
            #    results[:, 3] = results[:, 3] - results[:, 1]  #
            #    return results[:, :5]#ltwhconf
            #else:
            #    return None
            return motor_results, nonmotor_results, driver_results

    def __xyxy2xywh(self, results):
        if len(results) > 0:
            results=np.array(results)
            results[:, 2] = results[:, 2] - results[:, 0]  #origin is x1y1x2y2,to ltwh
            results[:, 3] = results[:, 3] - results[:, 1]  #
            return results[:, :5]#ltwhconf
        else:
            return None
