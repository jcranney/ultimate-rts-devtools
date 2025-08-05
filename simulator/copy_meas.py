#!/usr/bin/env python

import tqdm
import itertools
from pyMilk.interfacing.shm import SHM

pbar = tqdm.tqdm(
    itertools.count(),
)

meas_1d = SHM("pyrao_meas")
meas_2d = SHM(
    "pyrao_meas2d",
    ((meas_1d.shape[0], 1), meas_1d.get_data().dtype)
)

for i in pbar:
    meas_2d.set_data(meas_1d.get_data(check=True)[:, None])
