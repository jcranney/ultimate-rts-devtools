#!/usr/bin/env python3
import numpy as np
try:
    import matplotlib.pyplot as plt
except ModuleNotFoundError:
    print("skipping matplotlib, probably fine.")


def build_lut(*, n_subx: int, n_suby: int, pitch_x: float, pitch_y: float,
              theta: float, deltax: float, deltay: float,
              img_w: int, img_h: int, fov_x: int, fov_y: int, unsafe: bool):
    """From all of the keyword arguments, build and return a lookup table for
    subaperture coordinates:
    Returns:
        xx_c : ((n_subx*nsub_y,), float) : subap centers (x) in pixel space
        yy_c : ((n_subx*nsub_y,), float) : subap centers (y) in pixel space
        xx_0 : ((n_subx*nsub_y,), int) : subap starting pixel (x)
        yy_0 : ((n_subx*nsub_y,), int) : subap starting pixel (y)
    """
    ########
    # These are the centres of the subaperture images, allowed to be floats
    ####
    # build cartesian grid, aligned to x/y axes, centred at (0,0)
    xx_c, yy_c = np.meshgrid(
        (np.arange(n_subx)-n_subx/2+0.5)*pitch_x,
        (np.arange(n_suby)-n_suby/2+0.5)*pitch_y,
        indexing="xy"
    )
    xx_c = xx_c.flatten()
    yy_c = yy_c.flatten()

    # rotate coordinates around (0,0)
    pp = np.array([xx_c, yy_c])
    rot_mat = np.array([
        [np.cos(theta), -np.sin(theta)],
        [np.sin(theta), np.cos(theta)],
    ])
    pp = rot_mat @ pp
    xx_c, yy_c = pp

    # shift coordinates by (deltax,deltay), and centre in middle of array
    xx_c += deltax + img_w/2
    yy_c += deltay + img_h/2

    # determine origin pixel of each subapeture image:
    xx_0 = np.round(xx_c - fov_x/2).astype(int)
    yy_0 = np.round(yy_c - fov_y/2).astype(int)

    # determine invalid subapertures (accessing out of bounds)
    valid = np.ones(xx_0.shape, dtype=bool)
    valid = valid & (xx_0 >= 0)
    valid = valid & ((xx_0 + fov_x - 1) < img_w)
    valid = valid & (yy_0 >= 0)
    valid = valid & ((yy_0 + fov_y - 1) < img_h)
    invalid_count = (valid == 0).sum()
    if invalid_count > 0 and unsafe == 0:
        raise ValueError(
            f"{invalid_count:d} subapertures are invalid, " +
            "increase image ROI"
        )

    # filter coordinates by valid only
    xx_c = xx_c[valid]
    yy_c = yy_c[valid]
    xx_0 = xx_0[valid]
    yy_0 = yy_0[valid]
    return xx_c, yy_c, xx_0, yy_0


def plot_lut(*, img_w, img_h, fov_x, fov_y, xx_0, yy_0, xx_c, yy_c,
             title=None):
    # project those pixels onto the detector
    image = np.zeros([img_h, img_w])
    for x0, y0 in zip(xx_0, yy_0):
        image[y0:y0+fov_y, x0:x0+fov_x] += 1.0
    overlapping_count = (image > 1.0).sum()
    # Visualisation/sanity checks:
    ####
    # determine vertices of subapertures (for plotting only)
    xx_v = np.stack([
        xx_0+0.5, xx_0+fov_x-0.5, xx_0+fov_x-0.5, xx_0+0.5, xx_0+0.5
    ], axis=0)
    yy_v = np.stack([
        yy_0+0.5, yy_0+0.5, yy_0+fov_y-0.5, yy_0+fov_y-0.5, yy_0+0.5
    ], axis=0)
    fig, ax = plt.subplots(1, 2, figsize=[12, 6])
    ax[0].plot(xx_c.flatten(), yy_c.flatten(), ".")
    for i in range(xx_v.shape[1]):
        xv = xx_v[:, i]
        yv = yy_v[:, i]
        ax[0].plot(xv, yv, "k")
    ax[0].axis("square")
    ax[0].set_title("subaperture coordinates and bounds")
    ax[1].imshow(image, origin="lower")
    ax[1].set_title(
        f"subaperture overlapping regions, {overlapping_count:d} overlaps"
    )
    plt.tight_layout()
    if title:
        fig.canvas.manager.set_window_title(title)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        "build LUT for WFS subapertures based on CLI arguments"
    )
    parser.add_argument(
        "--plot", action="count", default=0,
        help="if present, show plots to user"
    )
    parser.add_argument(
        "--unsafe", action="count", default=0,
        help="if present, don't fail on invalid subapertures"
    )
    parser.add_argument(
        "--n_subx", type=int, default=32,
        help="number of subaps across x-dimension"
    )
    parser.add_argument(
        "--n_suby", type=int, default=32,
        help="number of subaps across y-dimension"
    )
    parser.add_argument(
        "--img_w", type=int, default=256,
        help="image width"
    )
    parser.add_argument(
        "--img_h", type=int, default=256,
        help="image height"
    )
    parser.add_argument(
        "--deltax", type=float, default=0.0,
        help="offset from ideal in x"
    )
    parser.add_argument(
        "--deltay", type=float, default=0.0,
        help="offset from ideal in y"
    )
    parser.add_argument(
        "--theta", type=float, default=0.0,
        help="rotation in radians"
    )
    parser.add_argument(
        "--pitch_x", type=float, default=8.0,
        help="spacing of subaperture images in x"
    )
    parser.add_argument(
        "--pitch_y", type=float, default=8.0,
        help="spacing of subaperture images in y"
    )
    parser.add_argument(
        "--fov_x", type=int, default=8,
        help="number of pixels per subaperture image in x"
    )
    parser.add_argument(
        "--fov_y", type=int, default=8,
        help="number of pixels per subaperture image in y"
    )
    args = parser.parse_args()

    args_dict = args.__dict__.copy()
    plot = args_dict.pop("plot")
    xx_c, yy_c, xx_0, yy_0 = build_lut(**args_dict)
    if plot:
        plt.ion()
        plot_lut(img_w=args.img_w, img_h=args.img_h,
                 fov_x=args.fov_x, fov_y=args.fov_y,
                 xx_0=xx_0, yy_0=yy_0, xx_c=xx_c, yy_c=yy_c)
