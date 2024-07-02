import numpy as np
import aotools
from pydantic import BaseModel, ConfigDict
from tqdm import tqdm


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
    thresh: float = 1e-6  # eigenval threshold
    factor_xx: np.ndarray = None
    factor_vv: np.ndarray = None
    state_matrix: np.ndarray = None
    x: np.ndarray = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.pixsize = self.diam / self.pupil.shape[0]
        yy, xx = np.mgrid[:pup_width, :pup_width]*self.pixsize
        yy = yy[self.pupil == 1]
        xx = xx[self.pupil == 1]

        # let sigma_xx -> covariance of phase with self
        # let sigma_yx -> covariance between phase and next phase
        # let sigma_vv -> covariance of driving noise with self
        sigma_xx = self._covariance(
            xx, yy, xx, yy
        )
        self.factor_xx, inv_xx = self._factorh(sigma_xx)

        sigma_yx = self._covariance(
            xx+self.wind[0]*self.ittime, yy+self.wind[1]*self.ittime, xx, yy
        )
        state_matrix = self.laminar*(sigma_yx @ inv_xx)
        sigma_vv = sigma_xx - state_matrix @ sigma_xx @ state_matrix.T
        self.state_matrix = state_matrix
        self.factor_vv, _ = self._factorh(sigma_vv)
        self.x = self.factor_xx @ np.random.randn(self.factor_xx.shape[1])

    def _covariance(self, x_in, y_in, x_out, y_out):
        rr = (x_out[:, None]-x_in[None, :])**2 + \
            (y_out[:, None]-y_in[None, :])**2
        cov = aotools.phase_covariance(rr, self.r0, self.L0)*(0.5/(np.pi*2))**2        
        return cov

    def _factorh(self, symmetric_matrix):
        vals, vecs = np.linalg.eigh(symmetric_matrix)
        vecs = vecs[:, vals > self.thresh]
        vals = vals[vals > self.thresh]
        factor = vecs @ np.diag(vals**0.5)
        inv = vecs @ np.diag((1/vals)) @ vecs.T
        return factor, inv

    def step(self):
        v = np.random.randn(self.factor_vv.shape[1])
        self.x = np.einsum("ij,j->i", self.state_matrix, self.x) + \
            np.einsum("ij,j->i", self.factor_vv, v)

    def get_phase(self):
        phi = np.zeros(self.pupil.shape)
        phi[self.pupil] = self.x.copy()
        return phi


class SHWFS(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    pupil: np.ndarray
    nsubx: int = 32  # number of subapertures across diameter
    fovx: int = 8  # pixels per fov width
    wavelength: float = 0.589  # sensing wavelength in microns
    dft2: np.ndarray = None

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
    
    def measure(self, phi):
        # phi in microns
        camp = pupil.astype(np.complex128) * \
            np.exp(1j*phi*2*np.pi/self.wavelength)
        im = np.zeros([self.fovx*self.nsubx]*2, dtype=np.float32)
        for j in range(self.nsubx):
            for i in range(self.nsubx):
                camp_small = camp[j*self.subwidth:(j+1)*self.subwidth,
                                  i*self.subwidth:(i+1)*self.subwidth]
                im_small = (np.abs(self.dft2 @ camp_small.flatten())**2)
                im[j*self.fovx:(j+1)*self.fovx,
                    i*self.fovx:(i+1)*self.fovx] = im_small.reshape([self.fovx, self.fovx])
        return im

    @property
    def subwidth(self):
        return self.pupil.shape[0] // self.nsubx


if __name__ == "__main__":
    pup_width = 64
    pupil = aotools.circle(pup_width//2, pup_width).astype(bool)

    phasescreen = PhaseScreen(
        pupil=pupil
    )

    shwfs = SHWFS(pupil=pupil)
    phi = phasescreen.get_phase()
    im = shwfs.measure(phi)

    phi_buffer = np.zeros([10000, *phi.shape], dtype=np.float32)
    im_buffer = np.zeros([10000, *im.shape], dtype=np.float32)
    for i in tqdm(range(im_buffer.shape[0])):
        phasescreen.step()
        phi = phasescreen.get_phase()
        im = shwfs.measure(phi)
        phi_buffer[i, ...] = phi
        im_buffer[i, ...] = im

    np.save("im_buffer.npy", im_buffer)
    np.save("phi_buffer.npy", phi_buffer)
