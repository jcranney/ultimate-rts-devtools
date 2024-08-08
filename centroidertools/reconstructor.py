from astropy.io import fits
import numpy as np
import scipy.linalg as la
from pyMilk.interfacing.shm import SHM
from tqdm import tqdm
from time import sleep
import subprocess


def get_shm_stacked(shm_name, nframes):
    shm = SHM(shm_name)
    return np.mean([
        shm.get_data(check=True)
        for _ in tqdm(range(nframes), leave=False)
    ], axis=0)


def save_control_matrices():
    def solve_cmat(dtc, ctm, cmm, dcc_reg, cmm_reg):
        x = la.solve(dtc.T @ dtc + dcc_reg, dtc.T, assume_a="pos").T
        x = x @ la.solve(cmm + cmm_reg, ctm.T, assume_a="pos").T
        return x

    def solve_recon(ctm, cmm, cmm_reg):
        x = la.solve(cmm + cmm_reg, ctm.T, assume_a="pos").T
        return x

    try:
        matrices = {
            key: fits.open(f"/tmp/ultimate_{key}.fits")[0].data
            for key in ["dmc", "dtc", "cmm", "ctm"]
        }
    except FileNotFoundError:
        print("input matrices missing, building them...")
        subprocess.run(["ultimatestart"])
        matrices = {
            key: fits.open(f"/tmp/ultimate_{key}.fits")[0].data
            for key in ["dmc", "dtc", "cmm", "ctm"]
        }

    # dtc = matrices["dtc"]
    ctm = matrices["ctm"]
    cmm = matrices["cmm"]
    # dcc_reg = 1.0*np.eye(dtc.shape[1])

    shm_fluxes = get_flux_vec(nframes=10)
    cmm_reg = np.diag(100/(shm_fluxes+1e-10)+10.0)
    # cmm_reg = np.diag(0*shm_fluxes+5.0)
    print("solving matrices")
    rcm = solve_recon(ctm, cmm, cmm_reg)
    fits.writeto("/tmp/ultimate_rcm.fits", rcm, overwrite=True)


def get_flux_vec(nframes=10):
    print("stacking flux frames")
    shm_fluxes = []
    for i in tqdm([1, 2, 3, 4], leave=True):
        flux = get_shm_stacked(f"flux{i:01d}", nframes=nframes)
        shm_fluxes += list(flux.flatten())
        shm_fluxes += list(flux.flatten())

    shm_fluxes = np.array(shm_fluxes)
    return shm_fluxes


def reconstruct_phase(rcm, shm_in, ref, shm_out=None):
    s = shm_in.get_data(check=True)
    phi = rcm @ (s-ref)
    phi = phi.reshape([64, 64])
    if shm_out is None:
        try:
            shm_out = SHM("recon_phi")
            shm_out.set_data(phi)
        except FileNotFoundError:
            shm_out = SHM("recon_phi", phi)
        return shm_out
    else:
        shm_out.set_data(phi)


def read_offsets():
    shm_offsets = SHM("slopevecref")
    return shm_offsets.get_data()


def save_offsets(nframes=50):
    slopes = get_shm_stacked("slopevec", nframes=nframes)
    try:
        shm_out = SHM("slopevecref")
        shm_out.set_data(slopes)
    except FileNotFoundError:
        shm_out = SHM("slopevecref", slopes)


def main():
    try:
        rcm = fits.open("/tmp/ultimate_rcm.fits")[0].data.astype(np.float32)
        print("loaded reconstructor from disk")
    except FileNotFoundError:
        print("no reconstructor on disk, making new")
        save_control_matrices()
        rcm = fits.open("/tmp/ultimate_rcm.fits")[0].data.astype(np.float32)
        print("done")

    save_offsets(nframes=50)
    ref = read_offsets()
    print("starting reconstruction")
    shm_in = SHM("slopevec")
    shm_out = reconstruct_phase(rcm, shm_in, ref)
    pbar = tqdm(True)
    while pbar:
        reconstruct_phase(rcm, shm_in, ref, shm_out=shm_out)
        sleep(0.1)
        pbar.update()


if __name__ == "__main__":
    main()
