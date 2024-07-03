import numpy as np
from pyMilk.interfacing.isio_shmlib import SHM
import time

if __name__ == "__main__":
    im_buffer = np.load("im_buffer.npy")
    phi_buffer = np.load("phi_buffer.npy")
    shm_wfs_images = [
        SHM(f"lgswfs{n:02d}", ((256, 256), np.float32))
        for n in range(4)
    ]
    shm_phases = [SHM("phi00", ((64, 64), np.float32))]
    t = time.time()
    while True:
        for im, phi in zip(im_buffer, phi_buffer):
            for data,shm in zip(im,shm_wfs_images):
                shm.set_data(data)
            for data,shm in zip(phi,shm_phases):
                shm.set_data(data)
            while True:
                if (time.time() - t) > 2e-3:
                    t = time.time()
                    break
