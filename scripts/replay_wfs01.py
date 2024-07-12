import numpy as np
from pyMilk.interfacing.isio_shmlib import SHM
import time

if __name__ == "__main__":
    framerate = 100.0
    im_buffer = np.load("im_buffer.npy")[:, 0, ...]
    shm_wfs_image = SHM("lgswfs01", ((256, 256), np.float32))
    t = time.time()
    while True:
        for im in im_buffer:
            shm_wfs_image.set_data(im)
            while True:
                if (time.time() - t) > 1/framerate:
                    t = time.time()
                    break
