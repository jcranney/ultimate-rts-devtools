import pyrao
import argparse
import itertools
import tqdm

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

aosys = pyrao.aosystem.SubaruLTAO(verbose=verbose, device=args.device)

pbar = tqdm.tqdm(
    itertools.count(),
    desc=f"wfe: {0:0.3f}",
    disable=(not verbose)
)
for i in pbar:
    aosys.step(blocking=blocking_mode)
    if i % 10 == 0:
        # update the residual wavefront every 10 frames, feel free to change
        # this to be faster, but it might slow down your overall simulator a
        # little.
        aosys.update_displays()
        if verbose:
            pbar.set_description(
                f"rmswfe: {aosys.perf['wfe'].item():0.3f}, sr: {100*aosys.perf['strehl']:0.1f}"
            )
