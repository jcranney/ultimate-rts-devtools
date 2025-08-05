#!/usr/bin/env python

import tqdm
import itertools
from pyMilk.interfacing.shm import SHM

pbar = tqdm.tqdm(
    itertools.count(),
)

# these will both already exist
actu_1d = SHM("pyrao_com")
actu_2d = SHM("aol1_dmC")

for i in pbar:
    actu_1d.set_data(actu_2d.get_data(check=True).flatten())
