#!/usr/bin/env python
from pyMilk.interfacing.isio_shmlib import SHM
import numpy as np


def shm_set(name, data):
    try:
        shm = SHM(name)
        shm.set_data(data)
    except FileNotFoundError:
        SHM(name, data)


suffixes = ["01", "02", "03", "04", "05"]
for suffix in suffixes:
    try:
        flux = SHM("flux"+suffix).get_data()
    except FileNotFoundError as e:
        print(e)
        continue
    valid = (flux > (flux.max()*0.5)).astype(np.uint8)
    shm_set("wfsvalid"+suffix, valid)
