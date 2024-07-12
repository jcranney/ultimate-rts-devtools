from pyMilk.interfacing.isio_shmlib import SHM
import numpy as np

NPIX = 256
NSUBX = 32


def init_wfs_shm(i=0):
    shm_wfsflat = SHM(f"wfsflat{i:02d}", ((NPIX, NPIX), np.float32))
    shm_wfsflat.set_data(np.ones((NPIX, NPIX), np.float32))
    # shm_wfsinterp = SHM(f"wfsinterp{i:02d}",((NPIX,NPIX),np.float32))
    shm_wfsvalid = SHM(f"wfsvalid{i:02d}", ((NSUBX, NSUBX), np.uint8))
    shm_wfsvalid.set_data(np.ones((NSUBX, NSUBX), dtype=np.uint8))


for i in range(5):
    init_wfs_shm(i+1)
