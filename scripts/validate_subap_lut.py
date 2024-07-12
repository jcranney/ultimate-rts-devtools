from pyMilk.interfacing.isio_shmlib import SHM
import matplotlib.pyplot as plt
import numpy as np

suffix = "lgs01"
prefix = "scmos1"

xx = SHM("lut_xx_c_"+suffix).get_data()
yy = SHM("lut_yy_c_"+suffix).get_data()
# xx_0 = SHM("lut_xx_0_"+suffix).get_data()
# yy_0 = SHM("lut_yy_0_"+suffix).get_data()
img = SHM(prefix+"_data").get_data()-SHM(prefix+"_bg").get_data()
img[img < 0] = 0.0

plt.figure(figsize=[10, 10])
plt.imshow(np.log(img), origin="lower")
plt.plot(xx.flatten(), yy.flatten(), "r+", alpha=0.4)
plt.tight_layout()
plt.show()
