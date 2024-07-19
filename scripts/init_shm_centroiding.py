from pyMilk.interfacing.isio_shmlib import SHM
import numpy as np

NSUBX = 32


def init_wfs_shm(i=0):
    size = SHM(f"scmos{i:01d}_data").get_data().shape
    shm_wfsflat = SHM(f"wfsflat{i:02d}", (size, np.float32))
    shm_wfsflat.set_data(np.ones(size, np.float32))


for i in range(5):
    init_wfs_shm(i+1)
