import numpy as np
from pyMilk.interfacing.isio_shmlib import SHM
import time

if __name__ == "__main__":
    im_buffer = np.load("im_buffer.npy")
    phi_buffer = np.load("phi_buffer.npy")
    slope_buffer = np.load("slope_buffer.npy")
    shm_wfs_images = [
        SHM(f"lgswfs{n:02d}", ((256, 256), np.float32))
        for n in range(4)
    ]
    shm_phases = [SHM("phi00", ((64, 64), np.float32))]
    shm_slopes = SHM("olslopes00", ((slope_buffer.shape[1],), np.float32))
    framerate = 100
    t = time.time()
    while True:
        for im, phi, slope in zip(im_buffer, phi_buffer, slope_buffer):
            for data, shm in zip(im, shm_wfs_images):
                shm.set_data(data)
            for data, shm in zip(phi, shm_phases):
                shm.set_data(data)
            shm_slopes.set_data(slope)
            while True:
                if (time.time() - t) > 1/framerate:
                    t = time.time()
                    break
