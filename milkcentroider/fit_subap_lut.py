#!/usr/bin/env python
"""
This is spaghetti code that works better than it ought to. It deserves cleaning
up but that's not a priority. If you would like to understand this code better,
maybe just email me, jesse.cranney@anu.edu.au
"""

from pyMilk.interfacing.isio_shmlib import SHM
import numpy as np

N_SUBX: int = 32  # number of subaps across x-dimension
N_SUBY: int = 32  # number of subaps across y-dimension
MIN_PITCH: float = 6.0  # spacing of subaperture images in x
MAX_PITCH: float = 10.0  # spacing of subaperture images in y

Ts = 1.0
N = 2048
F = N/Ts
min_freq = int(F/MAX_PITCH)
max_freq = int(F/MIN_PITCH)
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


ims = [load_im(i) for i in np.arange(5)]
print(f"{'idx':5s} | {'x0':10s} | {'y0':10s} | "
      f"{'theta':10s} | {'pitchx':10s} | {'pitchy':10s}")

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
            (np.arange(N_SUBX)-N_SUBX/2+0.5)*PITCH_X,
            (np.arange(N_SUBY)-N_SUBY/2+0.5)*PITCH_Y,
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
        [0.0]  # don't bother tuning theta, it's currently close enough to 0
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
