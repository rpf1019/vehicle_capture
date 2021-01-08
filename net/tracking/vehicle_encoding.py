import sys
import os
from timeit import time
import cv2
import numpy as np
from net.tracking.feat_extraction.image_encoder import Image_encoder


class Encoding(object):
    def __init__(self, feature_model_path):
        super(Encoding, self).__init__()
        self.encoder = Image_encoder(feature_model_path)

    def run(self, frame, picked_boxes):
        features = self.encoder.encode_image(frame, picked_boxes)
        return features

