#!/usr/bin/env python3

import numpy as np
from pyMilk.interfacing.fps import FPS
from pyMilk.interfacing.shm import SHM
from milkcentroider.build_subap_lut import build_lut


def print_header():
    print(f"{'index':10s} | {'deltax':10s} | {'deltay':10s} | "
          f"{'theta':10s} | {'pitchx':10s} | {'pitchy':10s}")


def fit_config(
    im,  # wfs raw image used to fit parameters
    idx,  # wfs index (for table)
    *,
    n_subx: int = 32,  # number of subaps across x-dimension
    n_suby: int = 32,  # number of subaps across y-dimension
    min_pitch: float = 5.0,  # minimum possible pitch (in pixels) of WFS
    max_pitch: float = 8.0,  # maximum possible pitch (in pixels) of WFS
):
    ts = 1.0  # sampling period in space (1 -> pixel units)
    n = 2048  # size of fft support used to find "pitch"
    f = n/ts  # frequency domain sampling rate [pixels^-1]
    min_freq = int(f/max_pitch)  # minimum frequency to search for pitch
    max_freq = int(f/min_pitch)  # maximum frequency to search for pitch

    img_h, img_w = im.shape

    im_fft = np.abs(np.fft.fft2(im, s=[n, n]))**2
    roi = im_fft[min_freq:max_freq,
                 min_freq:max_freq]
    roi -= roi.mean()
    roi[roi < 0] = 0.0

    def get_cog(im):
        xx, yy = np.meshgrid(
            np.arange(im.shape[1]),
            np.arange(im.shape[0]),
            indexing="xy"
        )
        cogx = (im*xx).sum()/im.sum()
        cogy = (im*yy).sum()/im.sum()
        return cogx, cogy

    cog = get_cog(roi)
    freq_x, freq_y = cog
    freq_x += min_freq
    freq_y += min_freq
    pitch_x = f/freq_x  # estimated pitch in x [pixels]
    pitch_y = f/freq_y  # estimated pitch in y [pixels]

    def build_grid(deltax, deltay, theta):
        xx_c, yy_c, xx_0, yy_0 = build_lut(
            n_subx=n_subx,
            n_suby=n_suby,
            pitch_x=pitch_x,
            pitch_y=pitch_y,
            theta=theta,
            deltax=deltax,
            deltay=deltay,
            img_w=img_w,
            img_h=img_h,
            fov_x=1,  # not relevant, since we ignore xx_0, yy_0
            fov_y=1,  # not relevant, since we ignore yy_0
            unsafe=True  # we shouldn't be accessing invalid pixels, so raise
                         # an error if we do
        )
        return xx_c, yy_c

    sigma = 6.9/2
    # for the first round, do single pixel bins and roll the masking array
    x_range = int(img_w - pitch_x*n_subx)
    y_range = int(img_h - pitch_y*n_suby)

    deltaxs, deltays = np.meshgrid(
        np.arange(-x_range//2, x_range//2+1),
        np.arange(-y_range//2, y_range//2+1),
        indexing="ij"
    )
    deltaxs = deltaxs.flatten()
    deltays = deltays.flatten()
    theta = 0.0
    best_cost = np.inf
    # Pixel coordinates used to build Gaussian
    xx, yy = np.meshgrid(
        np.arange(img_w),
        np.arange(img_h),
        indexing="xy"
    )
    xx_c, yy_c = build_grid(0, 0, theta)
    # this is pretty expensive to build but we only do it once per WFS.
    im_mask = np.zeros_like(im)
    for xc, yc in zip(xx_c, yy_c):
        im_mask += np.exp(-((xx-xc)**2+(yy-yc)**2)/((sigma)**2))
    im_mask = 1 - im_mask
    for deltax, deltay in zip(deltaxs, deltays):
        cost = (im * np.roll(im_mask, [deltay, deltax], [0, 1])).sum()
        if cost < best_cost:
            best_cost = cost
            deltax_best, deltay_best, theta_best = deltax, deltay, theta
    print(f"{idx:10d} | {deltax_best:10.5f} | {deltay_best:10.5f} | "
          f"{theta_best:10.5f} | {pitch_x:10.3f} | {pitch_y:10.3f}")

    return deltax_best, deltay_best, theta_best, pitch_x, pitch_y


def fine_tune(idx, quiet=False, flux_thresh=0.8, nframes=1):
    fpsname = f"centroider{idx:01d}"
    try:
        fps = FPS(fpsname)
    except RuntimeError:
        if not quiet:
            print(f"{fpsname} doesn't exist, can't fine tune")
        return None
    if not fps.run_isrunning():
        print(f"{fpsname} not running, can't fine tune")
        return None

    # fps exists and is running

    fluxname = f"flux{idx:01d}"
    try:
        flux_shm = SHM(fluxname)
    except RuntimeError:
        if not quiet:
            print(f"{fluxname} shm doesn't exist, can't fine tune")
        return None
    slopemapname = f"slopemap{idx:01d}"
    try:
        slopemap_shm = SHM(slopemapname)
    except RuntimeError:
        if not quiet:
            print(f"{slopemapname} shm doesn't exist, can't fine tune")
        return None

    # shm's exist

    # grab a frame of each (assume synced, not a big deal if not):
    data = [(
        slopemap_shm.get_data(),
        flux_shm.get_data()
    ) for _ in range(nframes)]
    slopemap = np.mean([d[0] for d in data], axis=0)
    fluxmap = np.mean([d[1] for d in data], axis=0)

    good_subaps = np.argwhere(fluxmap.flatten() > (fluxmap.max()*flux_thresh))
    tt_x = slopemap.flatten()[good_subaps].mean()
    tt_y = slopemap.flatten()[good_subaps+fluxmap.flatten().shape[0]].mean()
    return tt_x, tt_y
