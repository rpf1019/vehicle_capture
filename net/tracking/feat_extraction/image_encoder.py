import argparse
import os
import random
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as models
import cv2
from torchvision import transforms
import torchvision.transforms as T 
#from .models import baseline
from .models import resnet18
from PIL import Image

use_cuda = True  # True
device = torch.device('cuda: 0' if torch.cuda.is_available() and use_cuda else 'cpu')
if use_cuda:
    torch.manual_seed(0)
    torch.cuda.manual_seed_all(0)
torch.cuda.is_available()
#print('=> image_encoder gpu device: ', device)

normalizer = T.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
test_transformer = T.Compose([
        T.Resize((112, 112)),
        T.ToTensor(),
        normalizer,
    ])
	
	
class Image_encoder(object):

    def __init__(self, modelpath):
        #self.model = resnet18.ResNet18(576)
        self.model=resnet18.ResNet18(576)
        self.params = torch.load(modelpath)
        self.model.load_state_dict(self.params['state_dict'])
        self.model.to(device)
        self.model.eval()
        print('=> image_encoder model initiated.')


    def encode_image(self, image, boxes):
        #convert image
        input_tensor = torch.zeros(len(boxes), 3, 112, 112).cuda()
        for i, box in enumerate(boxes):
            top, bottom, left, right = int(box[1]), int(box[1]+box[3]), int(box[0]), int(box[0]+box[2])
            roi = image[top:bottom, left:right]
            roi = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
            roi_pil = Image.fromarray(roi)
            img = test_transformer(roi_pil).cuda()
            input_tensor[i, :, :, :] = img
        image_tensor = input_tensor.to(device)
        with torch.no_grad():
            result = self.model(image_tensor).cpu().detach().numpy() #8*512 d ndarray
        #feat_vecter = result[:len(boxes)]
        return result
        #return feat_vecter


#id = Encoder()
#img1 = cv2.imread('1.jpg')
#boxes = []
#boxes.append([0,0,1200,700])
#boxes.append([0,0,1150,680])
#feat_vecter = id.encode_image(img1,boxes)
#veca = np.mat(feat_vecter[0])
#vecb = np.mat(feat_vecter[1])
#num = float(veca*vecb.T)
#denom = np.linalg.norm(veca)*np.linalg.norm(vecb)
#cos = num/denom
#print(cos)
