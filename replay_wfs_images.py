import numpy as np
from pyMilk.interfacing.isio_shmlib import SHM
import time

if __name__ == "__main__":
    im_buffer = np.load("im_buffer.npy")
    phi_buffer = np.load("phi_buffer.npy")
    shm_wfs_image = SHM("lgswfs00", ((256, 256), np.float32))
    shm_phase = SHM("phi00", ((64, 64), np.float32))
    t = time.time()
    while True:
        for im, phi in zip(im_buffer, phi_buffer):
            shm_wfs_image.set_data(im)
            shm_phase.set_data(phi)
            while True:
                if (time.time() - t) > 1e-2:
                    t = time.time()
                    break
