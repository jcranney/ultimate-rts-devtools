from pyMilk.interfacing.isio_shmlib import SHM
import numpy as np

NSUBX = 32


def init_wfs_shm(i=0):
    size = SHM(f"scmos{i:01d}_data").get_data().shape
    shm_wfsflat = SHM(f"wfsflat{i:02d}", (size, np.float32))
    shm_wfsflat.set_data(np.ones(size, np.float32))
    # shm_wfsinterp = SHM(f"wfsinterp{i:02d}",((NPIX,NPIX),np.float32))
    shm_wfsvalid = SHM(f"wfsvalid{i:02d}", ((NSUBX, NSUBX), np.uint8))
    shm_wfsvalid.set_data(np.ones((NSUBX, NSUBX), dtype=np.uint8))


for i in range(5):
    init_wfs_shm(i+1)
