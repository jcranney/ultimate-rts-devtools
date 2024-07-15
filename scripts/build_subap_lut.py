#!/usr/bin/env python
import numpy as np
import argparse
import json

parser = argparse.ArgumentParser("build LUT for WFS subapertures")

parser.add_argument(
    "--output", nargs="?",
    help="save data to json file, e.g., for logging"
)
parser.add_argument(
    "--shmsuffix", nargs="?",
    help="suffix for shared memory object name, e.g., lgs01"
)
parser.add_argument(
    "--plot", action="count", default=0,
    help="if present, show plots to user"
)
parser.add_argument(
    "--UNSAFE", action="count", default=0,
    help="if present, don't fail on invalid subapertures"
)
parser.add_argument(
    "--N_SUBX", type=int, default=32,
    help="number of subaps across x-dimension"
)
parser.add_argument(
    "--N_SUBY", type=int, default=32,
    help="number of subaps across y-dimension"
)
parser.add_argument(
    "--IMG_W", type=int, default=256,
    help="image width"
)
parser.add_argument(
    "--IMG_H", type=int, default=256,
    help="image height"
)
parser.add_argument(
    "--X0", type=float, default=0.0,
    help="offset from ideal in x"
)
parser.add_argument(
    "--Y0", type=float, default=0.0,
    help="offset from ideal in y"
)
parser.add_argument(
    "--THETA", type=float, default=0.0,
    help="rotation in radians"
)
parser.add_argument(
    "--PITCH_X", type=float, default=8.0,
    help="spacing of subaperture images in x"
)
parser.add_argument(
    "--PITCH_Y", type=float, default=8.0,
    help="spacing of subaperture images in y"
)
parser.add_argument(
    "--FOV_X", type=int, default=8,
    help="number of pixels per subaperture image in x"
)
parser.add_argument(
    "--FOV_Y", type=int, default=8,
    help="number of pixels per subaperture image in y"
)
args = parser.parse_args()

########
# These are the centres of the subaperture images, allowed to be floats
####
# build cartesian grid, aligned to x/y axes, centred at (0,0)
xx, yy = np.meshgrid(
    (np.arange(args.N_SUBX)-args.N_SUBX/2+0.5)*args.PITCH_X,
    (np.arange(args.N_SUBY)-args.N_SUBY/2+0.5)*args.PITCH_Y,
    indexing="xy"
)
xx = xx.flatten()
yy = yy.flatten()
####
# rotate coordinates around (0,0)
pp = np.array([xx, yy])
rot_mat = np.array([
    [np.cos(args.THETA), -np.sin(args.THETA)],
    [np.sin(args.THETA), np.cos(args.THETA)],
])
pp = rot_mat @ pp
xx, yy = pp
####
# shift coordinates by (X0,Y0)
xx += args.X0 + args.IMG_W/2
yy += args.Y0 + args.IMG_H/2

# Now calculate coordinates in pixel space
####
# determine origin pixel of each subapeture image:
xx_0 = np.round(xx - args.FOV_X/2).astype(int)
yy_0 = np.round(yy - args.FOV_Y/2).astype(int)
####
# determine invalid subapertures (accessing out of bounds)
valid = np.ones(xx_0.shape, dtype=bool)
valid = valid & (xx_0 >= 0)
valid = valid & ((xx_0 + args.FOV_X - 1) < args.IMG_W)
valid = valid & (yy_0 >= 0)
valid = valid & ((yy_0 + args.FOV_Y - 1) < args.IMG_H)
####
# filter coordinates by valid only
xx = xx[valid]
yy = yy[valid]
xx_0 = xx_0[valid]
yy_0 = yy_0[valid]
invalid_count = (valid == 0).sum()
if invalid_count > 0 and args.UNSAFE == 0:
    raise ValueError(
        f"{invalid_count:d} subapertures are invalid, " +
        "increase image ROI"
    )

# project those pixels onto the detector
image = np.zeros([args.IMG_H, args.IMG_W])
for x0, y0 in zip(xx_0, yy_0):
    image[y0:y0+args.FOV_Y, x0:x0+args.FOV_X] += 1.0
overlapping_count = (image > 1.0).sum()

if args.plot > 0:
    # Visualisation/sanity checks:
    ####
    import matplotlib.pyplot as plt
    # determine vertices of subapertures (for plotting only)
    xx_v = np.stack([
        xx_0+0.5, xx_0+args.FOV_X-0.5, xx_0+args.FOV_X-0.5, xx_0+0.5, xx_0+0.5
    ], axis=0)
    yy_v = np.stack([
        yy_0+0.5, yy_0+0.5, yy_0+args.FOV_Y-0.5, yy_0+args.FOV_Y-0.5, yy_0+0.5
    ], axis=0)
    fig, ax = plt.subplots(1, 2, figsize=[12, 6])
    ax[0].plot(xx.flatten(), yy.flatten(), ".")
    for i in range(xx_v.shape[1]):
        xv = xx_v[:, i]
        yv = yy_v[:, i]
        ax[0].plot(xv, yv, "k")
    ax[0].axis("square")
    ax[0].set_title("subaperture coordinates and bounds")
    im = ax[1].imshow(image, origin="lower")
    ax[1].set_title(
        f"subaperture overlapping regions, {overlapping_count:d} overlaps"
    )
    plt.tight_layout()
    plt.show()

if args.output is not None:
    data = vars(args)
    output = data.pop("output")
    data.pop("plot")
    data["invalid_count"] = invalid_count
    data["overlapping_count"] = overlapping_count
    data["xx_c"] = list(xx)
    data["yy_c"] = list(yy)
    data["xx_0"] = list(xx_0)
    data["xx_0"] = list(yy_0)

    with open(output, "w") as fp:
        json.dump(data, fp, default=int, indent=4)

if args.shmsuffix is not None:
    print(f"saving {args.shmsuffix}")
    from pyMilk.interfacing.isio_shmlib import SHM
    shm_datas = [
        ["lut_xx_c_"+args.shmsuffix, xx.astype(np.float32)],
        ["lut_yy_c_"+args.shmsuffix, yy.astype(np.float32)],
        ["lut_xx_0_"+args.shmsuffix, xx_0.astype(np.uint32)],
        ["lut_yy_0_"+args.shmsuffix, yy_0.astype(np.uint32)],
    ]
    for shm_data in shm_datas:
        try:
            shm = SHM(shm_data[0])
            shm.set_data(shm_data[1])
        except FileNotFoundError:
            SHM(*shm_data)
