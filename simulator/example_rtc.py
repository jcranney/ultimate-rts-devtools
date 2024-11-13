import pyrao
import argparse
import itertools
from pydantic import BaseModel, ConfigDict
import torch
from pyMilk.interfacing.shm import SHM

parser = argparse.ArgumentParser(
    "AO system simulator for RTS development",
)
parser.add_argument(
    "--device", "-d", type=str, default="cpu",
    help="which device to run simulator on, e.g., cpu, cuda:0, ..."
)
parser.add_argument(
    "--nonblocking", "-n", action="store_true",
    help="flag for running in non-blocking mode"
)
parser.add_argument(
    "--quiet", "-q", action="store_true",
    help="flag for running in quiet mode"
)
args = parser.parse_args()

blocking_mode = True
if args.nonblocking:
    blocking_mode = False

verbose = True
if args.quiet:
    verbose = False


class UltimateRTC(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    com_buffer: torch.Tensor = None
    rcm: torch.Tensor = None
    dmc: torch.Tensor = None
    com_shm: SHM = None
    meas_shm: SHM = None
    gain: float = 0.5
    device: str = "cpu"
    delay: float = 1.6  # frames of delay
    _tmp_com: torch.Tensor = None  # temporary buffer for pre-calculating com

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        import numpy as np
        print("building matrices")
        m = pyrao.ultimatestart_recon_matrices()
        print("solving reconstructor")
        cmm = torch.tensor(m.c_meas_meas, device=self.device)
        cmm_reg = 50.0*torch.eye(cmm.shape[0], device=self.device)
        ctm = torch.tensor(m.c_ts_meas, device=self.device)
        dtc = torch.tensor(m.d_ts_com, device=self.device)
        dcc_reg = 0.01*torch.eye(dtc.shape[1], device=self.device)
        dmc = torch.tensor(m.d_meas_com, device=self.device)
        print("  factorising cmm")
        cmm_factor = torch.linalg.cholesky(cmm + cmm_reg)
        print("  solving ctm @ cmm^1")
        dtm = torch.cholesky_solve(ctm.T, cmm_factor).T
        print("  factorising dcc")
        dcc_factor = torch.linalg.cholesky(dtc.T @ dtc + dcc_reg)
        print("  solving dcc^1 @ dtc.T")
        dct = torch.cholesky_solve(dtc.T, dcc_factor)
        print("  combining rcm = dct @ dtm")
        rcm = dct @ dtm
        print("initialising RTC")
        self.rcm = rcm
        self.dmc = dmc
        if self.delay < 1.0:
            raise ValueError(
                f"{self.delay=}, must be greater than or equal to 1.0"
            )
        self.com_buffer = torch.zeros(
            [int(self.delay // 1.0) + 1, dct.shape[0]],
            device=self.device,
        )
        self._tmp_com = torch.zeros(
            self.rcm.shape[0],
            device=self.device,
        )
        name = "pyrao_com"
        try:
            self.com_shm = SHM(name)
            if self.com_shm.shape[0] != self.com_buffer.shape[1]:
                self.com_shm = SHM(name, self.com_buffer[0, :].cpu().numpy())
        except FileNotFoundError:
            self.com_shm = SHM(name, self.com_buffer[0, :].cpu().numpy())
        name = "pyrao_meas"
        try:
            self.meas_shm = SHM(name)
            if self.meas_shm.shape[0] != self.dmc.shape[0]:
                self.meas_shm = SHM(name, ((self.dmc.shape[0],), np.float32))
        except FileNotFoundError:
            self.meas_shm = SHM(name, ((self.dmc.shape[0],), np.float32))
        self.reset()

    def reset(self):
        self.com_buffer *= 0.0
        self.com_shm.set_data(self.com_buffer[0, :].cpu().numpy())

    def step(self, blocking=True):
        s_cl = torch.tensor(
            self.meas_shm.get_data(check=blocking),
            device=self.device
        )
        b = self.delay % 1.0
        a = 1.0 - b
        s_pol = s_cl - self.dmc @ (
            self.com_buffer[-2, :]*a + self.com_buffer[-1, :]*b
        )
        com = (1-self.gain)*self.com_buffer[0] - self.gain*(self.rcm @ s_pol)
        self.com_shm.set_data(com.cpu().numpy())
        self.com_buffer[1:, :] = self.com_buffer[:-1, :]
        self.com_buffer[0, :] = com

    def purge(self, *, npurge=10, blocking=True):
        print("purging")
        self.reset()
        for i in range(npurge):
            self.meas_shm.get_data(check=blocking)

    def start(self, blocking=True):
        print("running")
        try:
            for i in itertools.count():
                rtc.step(blocking=True)
        except KeyboardInterrupt:
            print("stopping")
            pass


if __name__ == "__main__":
    rtc = UltimateRTC(device=args.device)
    rtc.start()
