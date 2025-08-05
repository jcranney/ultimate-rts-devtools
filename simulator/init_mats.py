#!/usr/bin/env python

import pyrao
import torch
from pyMilk.interfacing.shm import SHM
import numpy as np

device: str = "cpu"
tichanov = True

print("building matrices")
m = pyrao.ultimatestart_recon_matrices()
print("solving reconstructor")
cmm = torch.tensor(m.c_meas_meas, device=device)
cmm_reg = (1.0 / torch.tensor(m.p_meas, device=device)).clamp(50.0, 1e10)
cmm_reg = torch.diag(cmm_reg)
ctm = torch.tensor(m.c_ts_meas, device=device)
dtc = torch.tensor(m.d_ts_com, device=device)
dcc_reg = 0.01 * torch.eye(dtc.shape[1], device=device)
print("  factorising cmm")
cmm_factor = torch.linalg.cholesky(cmm + cmm_reg)
print("  solving ctm @ cmm^1")
dtm = torch.cholesky_solve(ctm.T, cmm_factor).T
if tichanov:
    # do tichanov regularsied pinv
    print("  factorising dcc")
    dcc_factor = torch.linalg.cholesky(dtc.T @ dtc + dcc_reg)
    print("  solving dcc^1 @ dtc.T")
    dct = torch.cholesky_solve(dtc.T, dcc_factor)
else:
    # do modal inversion:
    print("  doing eigendecomposition of dcc")
    L, Q = torch.linalg.eigh(dtc.T @ dtc)
    L = L[-188:]
    if any(L < 1e-10):
        raise ValueError("modal inversion failed")
    Q = Q[:, -188:]
    print("  inverting")
    dcc_inv = Q @ torch.diag(1.0 / L) @ Q.T
    print("  evaluating dct")
    dct = dcc_inv @ dtc.T


print("  combining rcm = dct @ dtm")
rcm = dct @ dtm
print("saving matrix")
rcm = rcm

nmeas = rcm.shape[1]
nactu = rcm.shape[0]
nmode = nactu

modesWFS = rcm.T[:, None, :].cpu().numpy().astype(np.float32)
SHM("aol1_modesWFS", modesWFS)

DMmodes = np.eye(nmode, dtype=np.float32)[None, :, :]
# DMmodes *= 0.0
SHM("aol1_DMmodes", DMmodes)
