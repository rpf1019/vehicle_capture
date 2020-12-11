#!/usr/bin/env python
# -*- coding=utf-8 -*-

import logging
import os
from logging.handlers import TimedRotatingFileHandler
import re
def logging_conf(log_path):
    '''
    if not os.path.exists(log_path.split("/")[-2]):
        print log_path
        print log_path.split("/")[-2]
        os.makedirs(log_path.split("/")[-2])
    '''
    #创建一个logging的实例logger
    logger = logging.getLogger()

    #设定全局日志级别为DEBUG
    logger.setLevel(logging.INFO)
    #创建一个屏幕的handler，并且设定级别为DEBUG
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    #创建一个日志文件的handler，并且设定级别为DEBUG
  # fh = logging.FileHandler(log_path)
  # fh.setLevel(logging.INFO)
    #设置日志的格式
    formatter = logging.Formatter("%(asctime)s - %(filename)s - [line:%(lineno)d] - %(levelname)s - %(message)s")

   #按天分割日志
    log_time_handler = TimedRotatingFileHandler(filename=log_path, when="D", interval=1, backupCount=10)
    log_time_handler.suffix = "%Y-%m-%d.log"
    log_time_handler.extMatch = re.compile(r"^\d{4}-\d{2}-\d{2}.log$")
    #log_time_handler.suffix = "%Y-%m-%d_%H.log"
    #log_time_handler.extMatch = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{2}.log$")
    log_time_handler.setFormatter(formatter)
    logging.basicConfig(level=logging.INFO)

    #add formatter to ch and fh
    ch.setFormatter(formatter)
#   fh.setFormatter(formatter)
    #add ch and fh to logger
    logger.addHandler(ch)
    logger.addHandler(log_time_handler)
 #  logger.addHandler(fh)
    return logger

def get_logger(subdir,path='/model_server/video_object_extraction_server/log', filename='server.log'):
    absolute_dir = os.path.join(path, subdir)
    if not os.path.isdir(absolute_dir):
        os.mkdir(absolute_dir)
    logger = logging_conf(os.path.join(absolute_dir, filename))
    return logger
