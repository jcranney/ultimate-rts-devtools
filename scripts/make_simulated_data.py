#!/usr/bin/env python3

import numpy as np
import aotools
from pydantic import BaseModel, ConfigDict
from tqdm import tqdm
import time
from typing import Union
import torch
import aocov

class PhaseScreen(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    pupil: np.ndarray
    r0: float = 0.15  # metres at 0.5 micron
    L0: float = 25.0  # metres
    diam: float = 8.0  # metres
    laminar: float = 0.995  # lamination factor
    wind: np.ndarray = np.r_[10, 20]  # [x,y] m/s
    ittime: float = 1/500  # seconds
    pixsize: float = None
    thresh: float = 1e-5  # eigenval threshold
    seed: int = 1234
    rng: np.random.Generator = None
    height: float = 0.0  # metres
    targets: np.ndarray = np.array([   # one row per phase direction
        [0.0, 0.0],                    # x/y direction (arcsec)
    ])
    ARCSEC2RAD: float = np.pi/180/3600
    device: str = "cpu"

    @property
    def nvalid(self):
        return self.pupil.sum()

    @property
    def n_dirs(self):
        return self.targets.shape[0]

    class StateMatrix(BaseModel):
        """Special class for the state matrix, since I realised it has some
        really nice properties that allow us to do multiplication faster.
        Goes on same device as input arrays were.
        """
        model_config = ConfigDict(arbitrary_types_allowed=True)
        ML: torch.Tensor = None
        LT: torch.Tensor = None
        A: torch.Tensor = None
        device: str = None

        def __init__(self, cov_yx, inv_factor_xx, *args, **kwargs):
            super().__init__(*args,**kwargs)
            self.device = cov_yx.device.type
            self.ML = torch.einsum(
                "ij,jk->ik",
                cov_yx, inv_factor_xx,
            )
            self.LT = inv_factor_xx.T.clone()
            self.A = torch.einsum(
                "ij,jk->ik",
                self.ML, self.LT,
            )

        def _dot(self, x: torch.Tensor):
            return torch.einsum(
                "ij,jk,k...->i...",
                self.ML,
                self.LT,
                x,
            )

        def dot(self, x: np.ndarray):
            return self._dot(
                torch.tensor(x, device=self.device)
            ).detach().cpu().numpy()

        @property
        def shape(self):
            return self.A.shape

        def test_speed(self, ntests=100, seed=1):
            rng = np.random.default_rng(seed)
            x = rng.normal(size=[self.shape[1], ntests])
            t1 = time.time()
            self.dot(x)
            t2 = time.time()
            np.einsum(
                "ij,j...->i...",
                self.A, x)
            t3 = time.time()
            print(f"original: {(t3-t2)/ntests:0.3e}")
            print(f"improved: {(t2-t1)/ntests:0.3e}")

    state_matrix: StateMatrix = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.rng = np.random.default_rng(self.seed)

        self.pixsize = self.diam / self.pupil.shape[0]
        yy, xx = np.mgrid[:pup_width, :pup_width]*self.pixsize
        yy = yy[self.pupil == 1]
        xx = xx[self.pupil == 1]

        xx = np.tile(xx[None, :], [self.n_dirs, 1])
        yy = np.tile(yy[None, :], [self.n_dirs, 1])

        for i in range(self.n_dirs):
            xx[i] += self.height * self.targets[i, 0]*self.ARCSEC2RAD
            yy[i] += self.height * self.targets[i, 1]*self.ARCSEC2RAD

        xx = xx.ravel()
        yy = yy.ravel()
        # let sigma_xx -> covariance of phase with self
        # let sigma_yx -> covariance between phase and next phase
        # let sigma_vv -> covariance of driving noise with self
        print("building first covmat")
        sigma_xx = self._covariance(
            xx, yy, xx, yy
        )
        print("factorising first covmat")
        _factor_xx, _inv_factor_xx = self._factorh(sigma_xx)
        self._factor_xx = _factor_xx

        print("building second covmat")
        sigma_yx = self.laminar * self._covariance(
            xx+self.wind[0]*self.ittime, yy+self.wind[1]*self.ittime, xx, yy
        )
        print("about to build statematrix")
        state_matrix = self.StateMatrix(torch.tensor(sigma_yx, device=self.device), _inv_factor_xx)
        print("got it")
        sigma_vv = sigma_xx - state_matrix.dot(state_matrix.dot(sigma_xx).T).T
        print("did big MMMs")
        self.state_matrix = state_matrix
        print("factorising sigma_vv")
        _factor_vv, _ = self._factorh(sigma_vv)
        self._factor_vv = _factor_vv
        print("nice, starting up")
        self._x = self._factor_xx @ torch.tensor(self.rng.normal(size=self._factor_xx.shape[1]), device=self.device)

    def _covariance(self, x_in, y_in, x_out, y_out):
        cov = aocov.phase_covariance_xyxy(
            x_out, y_out, x_in, y_in, self.r0, self.L0, device=self.device
            )*(0.5/(np.pi*2))**2
        return cov

    def _factorh(self, symmetric_matrix):
        # vals, vecs = np.linalg.eigh(symmetric_matrix)
        vals, vecs = torch.linalg.eigh(
            torch.tensor(symmetric_matrix,device=self.device)
        )
        #vals = vals.detach().cpu().numpy()
        #vecs = vecs.detach().cpu().numpy()
        valid = vals > self.thresh
        vecs = vecs[:, valid]
        vals = vals[valid]
        factor = vecs * (vals**0.5)[None, :]
        inv_factor = vecs * ((1/vals)**0.5)[None, :]
        return factor, inv_factor

    def step(self):
        v = torch.tensor(
            self.rng.normal(size=self._factor_vv.shape[1]), 
            device=self.device
        )
        self._x = self.state_matrix._dot(self._x) + self._factor_vv @ v

    @property
    def x(self):
        return self._x.detach().cpu().numpy()
    
    @property
    def factor_xx(self):
        return self._factor_xx.detach().cpu().numpy()
    
    @property
    def factor_vv(self):
        return self._factor_vv.detach().cpu().numpy()

    @property
    def phase(self):
        phi = np.zeros([self.n_dirs, *self.pupil.shape])
        for i,phi_i in enumerate(phi):
            phi_i[self.pupil] = self.x[i*self.nvalid:(i+1)*self.nvalid].copy()
        return phi


class SHWFS(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    pupil: np.ndarray
    nsubx: int = 32  # number of subapertures across diameter
    fovx: int = 8  # pixels per fov width
    wavelength: float = 0.589  # sensing wavelength in microns
    dft2: np.ndarray = None
    slices: list = None
    es_path: tuple = None
    _im_subaps: np.ndarray = None
    _im_full: np.ndarray = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        padded_width = np.max([self.subwidth*2, self.fovx])
        dft = np.fft.fft(np.eye(padded_width), norm="ortho")
        dft = np.fft.fftshift(dft, axes=[0])
        dft = dft[:, :self.subwidth]
        if self.fovx < padded_width:
            dft = dft[
                padded_width//2-self.fovx//2:padded_width//2+self.fovx//2
            ]
        dft2 = np.kron(dft, dft)
        self.dft2 = dft2

        camp = pupil.astype(np.complex128)
        # reshape camp so that it's batched into a 4d array with shape:
        #   (nsub, nsub, subwidth, subwidth)
        camp = camp.reshape(
            self.nsubx, self.subwidth, self.nsubx, self.subwidth
        ).swapaxes(1, 2)
        # flatten the `subwidth` dimensions:
        camp = camp.reshape(
            self.nsubx, self.nsubx, self.subwidth*self.subwidth
        )
        # get the optimal einsum path to use online
        self.es_path = tuple(
            np.einsum_path("ijq,pq->ijp", camp, self.dft2, optimize="optimal")
        )

    def measure(self, phi):
        """Measure phase `phi` with shwfs.

        Takes `phi` in microns, returns wfs image intensity
        """
        # I'm aware that this is basically unreadable, but it's hella fast.

        # compute complex amplitude from phase and pupil
        camp = pupil.astype(np.complex128) * \
            np.exp(1j*phi*2*np.pi/self.wavelength)

        # reshape camp so that it's batched into a 4d array with shape:
        #   (nsub, nsub, subwidth, subwidth)
        camp = camp.reshape(
            self.nsubx, self.subwidth, self.nsubx, self.subwidth
        ).swapaxes(1, 2)
        # flatten the phase dimension:
        camp = camp.reshape(
            self.nsubx, self.nsubx, self.subwidth*self.subwidth
        )
        # do the fft2's batched using the MVM (DFT2) method
        im = np.einsum(
            "ijq,pq->ijp", camp, self.dft2, optimize=self.es_path[0]
        )
        # convert camplitude to intensity
        im = np.abs(im)**2
        # save a view of the image batched into subapertures (for cog)
        self._im_subaps = im.reshape(
            self.nsubx*self.nsubx, self.fovx, self.fovx
        )
        # reshape into something that looks like a wfs image
        im = im.reshape(
            self.nsubx, self.nsubx, self.fovx, self.fovx
        ).swapaxes(1, 2)
        im = im.reshape(self.nsubx * self.fovx, self.nsubx * self.fovx)
        # save a view of the image as a full WFS readout
        self._im_full = im

    @property
    def subwidth(self):
        return self.pupil.shape[0] // self.nsubx

    @property
    def image(self):
        return self._im_full.copy()

    @property
    def image_batched(self):
        return self._im_subaps.copy()


class ClassicCog(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    npix: int
    r_mat: np.ndarray = None
    xy_mat: np.ndarray = None
    thresh: Union[None, float] = 0.0
    einsum_num_str: str = "jk,ik,jk->ij"
    es_path: list = None

    def calibrate(self):
        x_span = np.arange(self.npix)-self.npix/2+0.5
        xx, yy = np.meshgrid(x_span, x_span, indexing="xy")
        # xy matrix is [2,Npixels]
        self.xy_mat = np.concatenate([
            xx.flatten()[:, None],
            yy.flatten()[:, None]
            ], axis=1).T
        self.r_mat = np.ones(self.xy_mat.shape)
        self.optimize_einsum()

    def optimize_einsum(self, batch_size=1):
        intsty = np.zeros([batch_size, self.npix*self.npix])
        self.es_path = np.einsum_path(
            self.einsum_num_str,
            self.r_mat,
            intsty,
            self.xy_mat,
            optimize=self.es_path
        )

    def cog(self, intensity):
        """compute the centroid of an [npix,npix] image or batch of
        [N,npix,npix] images.
        """
        if len(intensity.shape) == 2:
            intensity = intensity[None, ...]
        if self.thresh is not None:
            intensity = intensity - self.thresh
            intensity[intensity < 0] = 0.0
        num = np.einsum(
            self.einsum_num_str,
            self.r_mat,
            intensity.reshape(
                intensity.shape[0], np.prod(intensity.shape[1:])
            ),
            self.xy_mat,
            optimize=self.es_path[0]
        )
        den = np.sum(intensity, axis=(1, 2))[:, None]
        return num/den


if __name__ == "__main__":
    pup_width = 64
    fovx = 8  # pixels
    nsubx = 32  # across diameter
    pupil = aotools.circle(pup_width//2, pup_width).astype(bool)
    wfs_tar = np.array([
        [-10.0, 0.0],
        [0.0, 10.0],
        [10.0, 0.0],
        [0.0, -10.0],
    ])
    n_wfs = wfs_tar.shape[0]
    sci_tar = np.array([
        [0.0, 0.0],
    ])
    n_sci = sci_tar.shape[0]

    # for now, just one phase screen, eventually this will be wrapped
    # by an atmosphere object, which combines the turbulence sensibly
    # for use in tomographic systems.
    targets = np.concatenate([wfs_tar, sci_tar], axis=0)
    phasescreen = PhaseScreen(
        pupil=pupil,
        thresh=1e-5,
        targets=targets,
        device="cuda",
        height=1000,
    )
    print(f"{phasescreen.factor_xx.shape=}")
    print(f"{phasescreen.factor_vv.shape=}")

    shwfs = SHWFS(pupil=pupil, nsubx=nsubx, fovx=fovx)
    phi = phasescreen.phase[0]
    shwfs.measure(phi)
    im = shwfs.image

    cog = ClassicCog(
        npix=fovx,
        thresh=0.0,
    )
    cog.calibrate()
    slopes = cog.cog(shwfs.image_batched)

    flux = shwfs.image_batched.sum(axis=(1, 2))
    valid = flux > (0.5*flux.max())

    nframes = 10000
    phi_buffer = np.zeros(
        [nframes, n_sci, *phi.shape],
        dtype=np.float32
    )
    im_buffer = np.zeros(
        [nframes, n_wfs, *im.shape],
        dtype=np.float32
    )
    slope_buffer = np.zeros(
        [nframes, n_wfs*2*valid.sum()],
        dtype=np.float32
    )
    pbar = tqdm(range(im_buffer.shape[0]))
    for i in pbar:
        phasescreen.step()
        phis = phasescreen.phase
        slopes = []
        for j,phi in enumerate(phis[:n_wfs]):
            shwfs.measure(phi)
            slopes.append(cog.cog(shwfs.image_batched)[valid].T.flatten())  # yao slope fmt
            im_buffer[i, j, ...] = shwfs.image
        slope_buffer[i, :] = np.concatenate(slopes, axis=0)
        phi_buffer[i, 0, ...] = phis[-1, ...]
        pbar.set_description(f"rms wf: {phi.std():0.2f} um")

    np.save("im_buffer.npy", im_buffer)
    np.save("phi_buffer.npy", phi_buffer)
    np.save("slope_buffer.npy", slope_buffer)
