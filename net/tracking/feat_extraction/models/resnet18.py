'''ResNet-18 Image classfication for cifar-10 with PyTorch

Author 'Sun-qian'.

'''
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as models

# resnet18_net = models.resnet18(pretrained=False)
# print(resnet18_net)
# #print(resnet18.state_dict().keys())
# resnet18_backbone = nn.Sequential(*list(resnet18_net.children())[:-1])
# print(resnet18_backbone)
#resnet18_ori = models.resnet18(pretrained=True)
class ResNet18(nn.Module):
    def __init__(self, class_num):
        super(ResNet18, self).__init__()
        self.class_num = class_num
        resnet18_ori = models.resnet18(pretrained=True)
        self.resnet_layer = nn.Sequential(*list(resnet18_ori.children())[:-1])
        self.Linear_layer = nn.Linear(512, self.class_num)
        self.bn = nn.BatchNorm1d(512)
        self.bn.bias.requires_grad_(False)

    def forward(self, x):
        x = self.resnet_layer(x)
        #print('x.shape:', x.shape)
        #global_feats = x.view(x.shape[0], -1)  # flatten to (bs, 2048) #reshape
        #print('=============', x.shape[0])
        batch_size = x.size()[0]
        feats = x.view(batch_size, -1)
        #global_feats = self.fc(global_feats)
        #print('>>>>>>>>>>>>>', global_feats.size())
        feats = self.bn(feats)  # normalize for angular softmax
        if self.training:
            cls_score = self.Linear_layer(feats)
            return cls_score, feats
        else:
            feats = nn.functional.normalize(feats, dim=1, p=2)
            return feats


#test = ResNet18(100)
#print(test.resnet_layer)
#print('--------------------------------------')








