import warnings
import numpy as np
import os.path as osp

import torch
from torch.utils.data import Dataset
import h5py
import os
import pickle
import copy
warnings.filterwarnings("ignore")
from einops import rearrange

class PRE8dDataset(Dataset):
    def __init__(self, data_root, in_len, out_len, missing_ratio=0.1, mode="train", index="all"):
        super().__init__()
        self.data_root = data_root
        self.in_len = in_len
        self.out_len = out_len

        self.datapath = (
            self.data_root + "/missing_" + str(missing_ratio) + "_in_" + str(in_len) + "_out_" + str(out_len) + "_1_imputed_graph.pk"
        )
        self.mode = mode
        self.adj = np.load(self.data_root+"adj.npy")
        self.area = np.load(self.data_root+"is_sea.npy")
        self.area1 = np.load(self.data_root+"mask1.npy")[self.area.astype(bool)]
        self.area2 = np.load(self.data_root+"mask2.npy")[self.area.astype(bool)]
        self.area3 = np.load(self.data_root+"mask3.npy")[self.area.astype(bool)]
        mean = np.load(self.data_root+"mean.npy")
        std = np.load(self.data_root+"std.npy")
        self.mean = mean[self.area.astype(bool)]
        self.std = std[self.area.astype(bool)]
        max = np.load(self.data_root+"max.npy")
        min = np.load(self.data_root+"min.npy")
        self.max = max[self.area.astype(bool)]
        self.min = min[self.area.astype(bool)]


        if os.path.isfile(self.datapath) is False:
            print(self.datapath + ': data is not prepared')
        else:  # load datasetfile
            with open(self.datapath, "rb") as f:
                self.datas, self.data_ob_masks, self.data_gt_masks, self.labels, self.label_ob_masks = pickle.load(
                    f
                )
        self.datas = self.datas[:,:,:,:,self.area.astype(bool)]
        self.data_ob_masks = self.data_ob_masks[:,:,:, self.area.astype(bool)]
        self.data_gt_masks = self.data_gt_masks[:,:,:,self.area.astype(bool)]
        self.labels = self.labels[:,:,:, self.area.astype(bool)]
        self.label_ob_masks = self.label_ob_masks[:,:,:,self.area.astype(bool)]

        bound = 648 - self.in_len - self.out_len
        self.index = int(index)
        self.datas = self.datas[:,self.index]

        if mode == "train":
            self.datas, self.data_ob_masks, self.data_gt_masks, self.labels, self.label_ob_masks = self.datas[:bound], self.data_ob_masks[:bound], self.data_gt_masks[:bound], self.labels[:bound], self.label_ob_masks[:bound]
        elif mode == 'test':
            self.datas, self.data_ob_masks, self.data_gt_masks, self.labels, self.label_ob_masks = self.datas[bound:], self.data_ob_masks[bound:], self.data_gt_masks[bound:], self.labels[bound:], self.label_ob_masks[bound:]

        B, T, C, N = self.datas.shape
        self.datas = rearrange(self.datas,'b t c n->(b n) t c')
        self.data_ob_masks = rearrange(self.data_ob_masks,'b t c n->(b n) t c')
        self.data_gt_masks = rearrange(self.data_gt_masks,'b t c n->(b n) t c')
        self.labels = rearrange(self.labels,'b t c n->(b n) t c')
        self.label_ob_masks = rearrange(self.label_ob_masks,'b t c n->(b n) t c')

    def __len__(self):
        return self.datas.shape[0]

    def __getitem__(self, index):
        return self.datas[index], self.data_ob_masks[index], self.data_gt_masks[index], self.labels[index], self.label_ob_masks[index]

    def load_data(self):
        data = h5py.File(osp.join(self.data_root, "modis_chla_8d_4km_pre.mat"))
        chla = np.array(data["CHLA_pre"])[:, np.newaxis]
        is_land = np.sum(~np.isnan(chla), 0) == 0
        chla_mask = ~np.isnan(chla)
        self.chla_scaler = LogScaler()
        chla = self.chla_scaler.transform(chla)
        mean = np.nanmean(chla[:648], axis=0)[np.newaxis, :, :, :]
        chla = np.nan_to_num(chla, nan=0.)
        chla = chla_mask.astype(float) * chla + (1 - chla_mask.astype(float)) * mean

        mask = chla_mask.astype(np.float32)
        return chla, mask, mean, is_land.squeeze()

class LogScaler:
    def transform(self, x):
        return np.log10(x)
    def inverse_transform(self, x):
        return 10**x
