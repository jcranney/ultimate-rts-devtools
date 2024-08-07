from astropy.io import fits
import numpy as np
import scipy.linalg as la
from pyMilk.interfacing.shm import SHM
from tqdm import tqdm
from time import time


def save_control_matrices():
    def solve_recon(dtc, ctm, cmm, dcc_reg, cmm_reg):
        x = la.solve(dtc.T @ dtc + dcc_reg, dtc.T, assume_a="pos").T
        x = x @ la.solve(cmm + cmm_reg, ctm.T, assume_a="pos").T
        return x

    def get_shm_stacked(shm_name, nframes):
        shm = SHM(shm_name)
        return np.mean([
            shm.get_data(check=True)
            for _ in tqdm(range(nframes), leave=False)
        ], axis=0)

    matrices = {
        key: fits.open(f"/tmp/ultimate_{key}.fits")[0].data
        for key in ["dmc", "dtc", "cmm", "ctm"]
    }

    dtc = matrices["dtc"]
    ctm = matrices["ctm"]
    cmm = matrices["cmm"]

    dcc_reg = 1.0*np.eye(dtc.shape[1])

    print("stacking flux frames")
    shm_fluxes = []
    for i in tqdm([1, 2, 3, 4], leave=True):
        flux = get_shm_stacked(f"flux{i:01d}", nframes=10)
        shm_fluxes += list(flux.flatten())
        shm_fluxes += list(flux.flatten())
    shm_fluxes = np.array(shm_fluxes)
    cmm_reg = np.diag(1/(shm_fluxes+1e-10))

    rcm = solve_recon(dtc, ctm, cmm, dcc_reg, cmm_reg)
    fits.writeto("/tmp/ultimate_rcm.fits", rcm, overwrite=True)


def reconstruct_phase(rcm):
    shm = SHM("slopevec")
    s = shm.get_data(check=True)
    phi = rcm @ s
    phi = phi.reshape([64, 64])
    try:
        shm = SHM("recon_phi")
        shm.set_data(phi)
    except RuntimeError:
        shm = SHM("recon_phi", phi)


if __name__ == "__main__":
    try:
        rcm = fits.open("/tmp/ultimate_rcm.fits")[0].data.astype(np.float32)
    except FileNotFoundError:
        save_control_matrices()
        rcm = fits.open("/tmp/ultimate_rcm.fits")[0].data.astype(np.float32)

    while True:
        reconstruct_phase(rcm)
        time.sleep(0.1)
