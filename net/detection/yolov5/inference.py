# encoding: utf-8

import time
import cv2 
import sys 
#import torch.backends.cudnn as cudnn
sys.path.append("/model_server_multi_sourceids/video_vehicles_extraction_server")
#from net.config import Config
from net.detection.yolov5.utils.datasets import *
from net.detection.yolov5.utils.utils import *
import torch.backends.cudnn as cudnn

class DETECT_PARAM:
    IMG_SIZE = 640
    CONF_THRESH = 0.4
    IOU_THRESH = 0.5
    DEVICE = "3"

device = torch.device('cuda: 0' if torch.cuda.is_available() else 'cpu')
class Detector():
    def __init__(self, weights):
        cudnn.benchmark = True
        # Initialize
        # device = torch.device('cuda: 0' if torch.cuda.is_available() else 'cpu')
        self.half = device.type != 'cpu'  # half precision only supported on CUDA
	# Load model
        torch.cuda.is_available()
        self.model = torch.load(weights, map_location=device)['model'].float()  # load to FP32
        self.model.cuda().eval()
        if self.half:
            self.model.half()  # to FP16


    def preprocess(self, inputs, img_size=416):
        img = letterbox(inputs, new_shape=DETECT_PARAM.IMG_SIZE)[0]
        new_shape = img.shape
        # Convert
        img = img[:, :, ::-1].transpose(2, 0, 1)  # BGR to RGB, to 3x416x416
        img = np.ascontiguousarray(img)

        img = torch.from_numpy(img).to(device)
        img = img.half() if self.half else img.float()  # uint8 to fp16/32
        img /= 255.0
        if img.ndimension() == 3:
            img = img.unsqueeze(0)
        return img, new_shape


    def predict(self, inputs):
        ori_shape = inputs.shape
        inputs, new_shape = self.preprocess(inputs)
        with torch.no_grad():
            pred = self.model(inputs)[0]
        det = self.post_process(pred, new_shape, ori_shape)
        return det

    def post_process(self, inputs, new_shape, ori_shape):
        pred = non_max_suppression(inputs, DETECT_PARAM.CONF_THRESH, DETECT_PARAM.IOU_THRESH)
        for i, det in enumerate(pred):
            if det is not None and len(det):
                #det    [x1,y1,x2,y2,conf,label]
                det[:,:4] = scale_coords(new_shape, det[:, :4], ori_shape).round()
        if pred[0] is not None:
            return pred[0].detach().cpu().numpy()
        else:
            return None



def test_img(file_path):
    img = cv2.imread(file_path)
    start_time = time.time()
    dets = detector.predict(img)
    return dets



if __name__ == '__main__':
    'running inference'

    image_dir = './test_pic'
    detector = Detector('./weights/best.pt')
    for file_name in os.listdir(image_dir):
        file_path = os.path.join(image_dir, file_name)
        img = cv2.imread(file_path)
        try:
            dets =  test_img(file_path)
            print(dets)
        except BaseException as e:
            continue
        
    
    


