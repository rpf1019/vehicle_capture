# coding: utf-8
import torch
from torch.autograd import Variable
import torchvision
from torchvision import transforms
from PIL import Image
import numpy as np
import sys
import os
import cv2

# -------------------------------------
# for matplotlib to displacy chinese characters correctly


use_cuda = True  # True
device = torch.device('cuda: 0' if torch.cuda.is_available() and use_cuda else 'cpu')

if use_cuda:
    torch.manual_seed(0)
    torch.cuda.manual_seed_all(0)

#mobilenet_pth = 'net/image_quality/model/lpattr_4classes_epoch30.pth'
preprocess_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
    ])

class Plate_analyzer():
    def __init__(self, modelpath):
        self.mobilenet = torch.load(modelpath)
        self.mobilenet.to(device)
        self.mobilenet.eval()  # evaluation mode

    def run(self, imglist):
        pred = list()
        if len(imglist) == 0:
           return pred
        input_tensor = torch.zeros(len(imglist), 3, 224, 224).cuda()
        for i, img in enumerate(imglist):
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img_pil = Image.fromarray(img)
            totensor = preprocess_transform(img_pil).cuda()
            input_tensor[i, :, :, :] = totensor
        image_tensor = input_tensor.to(device)
        with torch.no_grad():
            out = self.mobilenet(image_tensor)
        pred = torch.max(out, 1)[1].cpu().numpy().tolist()###return list of bs x 1
        return pred

