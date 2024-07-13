#!/usr/bin/env python
import argparse
from pyMilk.interfacing.isio_shmlib import SHM
import numpy as np

parser = argparse.ArgumentParser("build LUT for WFS subapertures")
parser.add_argument(
    "--N_SUBX", type=int, default=32,
    help="number of subaps across x-dimension"
)
parser.add_argument(
    "--N_SUBY", type=int, default=32,
    help="number of subaps across y-dimension"
)
parser.add_argument(
    "--MIN_PITCH", type=float, default=6.0,
    help="spacing of subaperture images in x"
)
parser.add_argument(
    "--MAX_PITCH", type=float, default=10.0,
    help="spacing of subaperture images in y"
)
args = parser.parse_args()

Ts = 1.0
N = 2048
F = N/Ts
min_freq = int(F/args.MAX_PITCH)
max_freq = int(F/args.MIN_PITCH)
FOV_X: int = 2
FOV_Y: int = 2


def get_roi(im):
    im_fft = np.abs(np.fft.fft2(im, s=[N, N]))**2
    roi = im_fft[min_freq:max_freq,
                 min_freq:max_freq]
    roi -= roi.mean()
    roi[roi < 0] = 0.0
    return roi


def get_cog(im):
    xx, yy = np.meshgrid(
        np.arange(im.shape[1]),
        np.arange(im.shape[0]),
        indexing="xy"
    )
    cogx = (im*xx).sum()/im.sum()
    cogy = (im*yy).sum()/im.sum()
    return cogx, cogy


def load_im(idx, nstack=10):
    name = f"scmos{idx:01d}_data"
    shm = SHM(name)
    print("getting ", name)
    im = np.mean([shm.get_data(check=True) for _ in range(nstack)], axis=0)
    return im


ims = [load_im(i) for i in np.arange(5)+1]
print(f"{'idx':5s} | {'x0':10s} | {'y0':10s} | {'theta':10s} | {'pitchx':10s} | {'pitchy':10s}")
for im_idx, im in enumerate(ims):
    IMG_H, IMG_W = im.shape
    roi = get_roi(im)
    cog = get_cog(roi)
    freq_x, freq_y = cog
    freq_x += min_freq
    freq_y += min_freq
    PITCH_X = F/freq_x
    PITCH_Y = F/freq_y

    def build_grid(x0, y0, theta):
        # build cartesian grid, aligned to x/y axes, centred at (0,0)
        xx, yy = np.meshgrid(
            (np.arange(args.N_SUBX)-args.N_SUBX/2+0.5)*PITCH_X,
            (np.arange(args.N_SUBY)-args.N_SUBY/2+0.5)*PITCH_Y,
            indexing="xy"
        )
        xx = xx.flatten()
        yy = yy.flatten()
        ####
        # rotate coordinates around (0,0)
        pp = np.array([xx, yy])
        rot_mat = np.array([
            [np.cos(theta), -np.sin(theta)],
            [np.sin(theta), np.cos(theta)],
        ])
        pp = rot_mat @ pp
        xx, yy = pp
        # shift coordinates by (X0,Y0)
        xx += x0 + IMG_W/2
        yy += y0 + IMG_H/2

        # Now calculate coordinates in pixel space
        # determine origin pixel of each subapeture image:
        xx_0 = np.round(xx - FOV_X/2).astype(int)
        yy_0 = np.round(yy - FOV_Y/2).astype(int)
        return xx_0, yy_0

    x0s, y0s, thetas = np.meshgrid(
        np.linspace(-40, 40, 161),
        np.linspace(-40, 40, 161),
        [0.0]
    )
    x0s = x0s.flatten()
    y0s = y0s.flatten()
    thetas = thetas.flatten()
    best_score = np.inf
    for X0, Y0, theta in zip(x0s, y0s, thetas):
        im_tmp = im.copy()
        xx_0, yy_0 = build_grid(X0, Y0, theta)
        for x0, y0 in zip(xx_0, yy_0):
            im_tmp[y0:y0+FOV_Y, x0:x0+FOV_X] *= 0.0
        score = im_tmp.sum()
        if score < best_score:
            best_score = score
            x0_best, y0_best, theta_best = X0, Y0, theta
            im_best = im_tmp.copy()
    print(f"{im_idx:5d} | {x0_best:10.5f} | {y0_best:10.5f} | "
          f"{theta_best:10.5f} | {PITCH_X:10.3f} | {PITCH_Y:10.3f}")
