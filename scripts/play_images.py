#!/usr/bin/env python

from pyMilk.interfacing.isio_shmlib import SHM
from astropy.io import fits
import numpy as np
import glob
import time
from tqdm import tqdm
import argparse


parser = argparse.ArgumentParser("play a batch of recorded WFS images")
parser.add_argument(
    "dir",
    help="directory where fits files are saved", default="."
)
parser.add_argument(
    "--fr", type=int, default=100,
    help="maximum framerate for playing to shm"
)
args = parser.parse_args()

FRAMERATE = args.fr

raw = [
    fits.open(fname)
    for fname in glob.glob(args.dir+"/scmos*.fits") if "_bg_" not in fname
]
bg = [
    fits.open(fname)
    for fname in glob.glob(args.dir+"/scmos*.fits") if "_bg_" in fname
]

# background image should be held static - just like during operations
bg_data = [
    [b[0].header["CAMERA"]+"_bg", b[0].data.astype(np.float32)]
    for b in bg
]
for data in bg_data:
    try:
        if "5" in data[0]:
            data[0] = data[0].replace("5","0")
        shm = SHM(data[0])
        shm.set_data(data[1])
    except FileNotFoundError:
        SHM(*data)

# now loop over buffer of images to feed to SHM
# initialise first so we don't do it every time
raw_data = [
    [r[0].header["CAMERA"]+"_data", r[0].data.astype(np.float32)]
    for r in raw
]
shms = []
for data in raw_data:
    try:
        if "5" in data[0]:
            data[0] = data[0].replace("5","0")
        shm = SHM(data[0])
        shm.set_data(data[1][0])
    except FileNotFoundError:
        shm = SHM(data[0], data[1][0])
    shms.append(shm)

n_frames = raw[0][0].data.shape[0]
idx: int = 0
t1 = time.time()
pbar = tqdm()
while True:
    for data, shm in zip(raw_data, shms):
        shm.set_data(data[1][idx])
    idx = (idx + 1) % n_frames
    while time.time()-t1 < 1/FRAMERATE:
        pass
    t1 = time.time()
    pbar.update()
