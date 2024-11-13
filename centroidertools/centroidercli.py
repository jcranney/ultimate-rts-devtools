#!/usr/bin/env python3

import argparse
import sys
import os
import subprocess
import contextlib
import yaml
from pyMilk.interfacing.fps import FPS
from pyMilk.interfacing.shm import SHM
from pydantic import BaseModel
from centroidertools import build_subap_lut as bld
from centroidertools import fit_subap_lut as fit
import numpy as np
from centroidertools.wgui import app
from centroidertools import reconstructor
import time


# This redirect class allows suppression of the C-code prints that mess up the
# terminal. E.g.:
#
#   with redirect_stdout():
#       fps = FPS(f"{self._fpsprefix:s}{idx:2d}")
#
@contextlib.contextmanager
def redirect_stdout(stdout=os.devnull):
    stdout_fd = sys.stdout.fileno()
    saved_stdout_fd = os.dup(stdout_fd)
    try:
        with open(stdout, 'w') as f_out:
            os.dup2(f_out.fileno(), stdout_fd)
        yield
    finally:
        os.dup2(saved_stdout_fd, stdout_fd)
        os.close(saved_stdout_fd)


class Config(BaseModel):
    """Valid configuration object for a single WFS
    If this oject is able to be created, then the relevant config is valid"""
    deltax: float
    deltay: float
    img_w: int
    img_h: int
    pitch_x: float
    pitch_y: float
    n_subx: int
    n_suby: int
    fov_x: int
    fov_y: int
    theta: float
    cogthresh: float
    bgnpix: int

    @staticmethod
    def from_dict(config_dict: dict):
        return Config(**config_dict)

    def to_dict(self):
        return self.__dict__

    def build_lut(self):
        xx_c, yy_c, xx_0, yy_0 = bld.build_lut(
            n_subx=self.n_subx, n_suby=self.n_suby,
            pitch_x=self.pitch_x, pitch_y=self.pitch_y, theta=self.theta,
            deltax=self.deltax, deltay=self.deltay,
            img_w=self.img_w, img_h=self.img_h,
            fov_x=self.fov_x, fov_y=self.fov_y,
            unsafe=False)
        return (xx_c.astype(np.float32), yy_c.astype(np.float32),
                xx_0.astype(np.uint32), yy_0.astype(np.uint32))


class CentroiderCLI():
    # following example from:
    # https://chase-seibert.github.io/blog/2014/03/21/python-multilevel-argparse.html

    # 1 NGS + 4 LGSs
    _indices = [0, 1, 2, 3, 4]
    # or to ignore the NGS:
    # _indices = [1, 2, 3, 4]
    _fpsprefix = "centroider"

    _wgui_sessionname = "centroider-wgui"

    # this is a dict with WFS idx as key (not a list, because we don't
    # want to be restricted to always having 0,1,2,... wfs numbering,
    # e.g., when NGS truth sensor is not used, we won't use 0)
    _config: None
    _default_configfile = os.environ["HOME"]+"/.config/centroider.yaml"
    _verbosity: int = 0

    def __init__(self, *args, **kwargs):
        commands = []
        for attribute in self.__dir__():
            if attribute[0] == "_":
                continue
            doc = getattr(self, attribute).__doc__
            if doc is None:
                doc = ""
            commands.append({
                "cmd": attribute,
                "doc": doc,
            })
        usage = "cent <command> [<args>]\n\nThe valid commands are:\n"

        usage += "\n".join([
            f"{command["cmd"]:>10s}     {command["doc"]:<s}"
            for command in commands
        ])
        parser = argparse.ArgumentParser(usage=usage)
        parser.add_argument("command", help="Subcommand to run")
        parser.add_argument("--verbose", "-v", action="count", default=0,
                            help="verbosity level")

        split_args = [[], []]
        for i in range(len(sys.argv)):
            tmp = sys.argv.pop(0)
            if i == 0:
                split_args[0].append(tmp)
                split_args[1].append(tmp)
                continue
            if i == 1 or "-v" in tmp:
                split_args[0].append(tmp)
            else:
                split_args[1].append(tmp)
        args = parser.parse_args(split_args[0][1:])
        self._verbosity = args.verbose

        if not hasattr(self, args.command):
            print(f"Unrecognized cent command: `{args.command}`")
            parser.print_help()
            exit(1)
        # prepare sys.argv for next round of commands
        sys.argv = split_args[1]

        # use dispatch pattern to invoke method with same name
        getattr(self, args.command)()

    def start(self):
        """Try to start the centroiders"""

        parser = argparse.ArgumentParser(
            description='start centroiders, using config on disk',
            usage=(
                "   cent start [-h] [--filename NAME]\n\n"
                "e.g.,\n"
                "    cent start\n"
                "    cent start --help\n"
                "    cent start --filename customconfig.yaml\n"
            )
        )
        args = self._standard_args(parser)

        fps_list = self._fps_list()
        if len(fps_list) == len(self._indices):
            if self._verbosity > 0:
                print("all FPSs aleady exist, aborting (maybe `stop` first?)")
            exit(0)

        filename = os.path.abspath(args.filename)
        self._config_load(filename)

        # create centroider FPS
        for idx in self._indices:
            milk_loopname = f"centroider{idx:01d}"
            milk_cmd = (f"mload ltaomodcentroider;"
                        f"ltao.centroider {idx:01d};"
                        f"ltao.centroider _FPSINIT_;"
                        f"ltao.centroider _TMUXSTART_;")
            cmd = ["milk-exec", "-n", milk_loopname, milk_cmd]
            # start tmux session and fpsinit
            result = subprocess.run(cmd, capture_output=True, cwd="/tmp/")
            warning_string = self._parse_launch_result(result)
            if self._verbosity > 0:
                if result.returncode != 0:
                    print(f"failed to create {milk_loopname}")
                if warning_string:
                    print(warning_string)
                    print("")

        fps_list = self._fps_list()
        for fps in fps_list:
            while not fps.conf_isrunning():
                fps.conf_start()
            while not fps.run_isrunning():
                fps.run_start()
            if self._verbosity > 0:
                print(f"started {fps.name}")

        # centroiders have started, now we can kick off the slope gatherer:
        milk_loopname = "slopevec"
        milk_cmd = ("mload ltaomodcentroider;"
                    "ltao.slopevec;"
                    "ltao.slopevec _FPSINIT_;"
                    "ltao.slopevec _TMUXSTART_;")
        cmd = ["milk-exec", "-n", milk_loopname, milk_cmd]
        # start tmux session and fpsinit
        result = subprocess.run(cmd, capture_output=True, cwd="/tmp/")
        warning_string = self._parse_launch_result(result)
        if self._verbosity > 0:
            if result.returncode != 0:
                print(f"failed to create {milk_loopname}")
            if warning_string:
                print(warning_string)
                print("")

        try:
            fps = FPS(milk_loopname)
        except RuntimeError:
            print("couldnt connect to slopevec whattha?")
            fps = None
        if fps:
            while not fps.conf_isrunning():
                fps.conf_start()
            while not fps.run_isrunning():
                fps.run_start()
            if self._verbosity > 0:
                print(f"started {fps.name}")

        self._clean()

    def _standard_args(self, parser):
        parser.add_argument(
            "--filename", help="centroider configuration filename",
            default=self._default_configfile
        )
        args = parser.parse_args(sys.argv[1:])
        return args

    def stop(self):
        """Try to stop the centroiders"""
        self._stop()

    def _stop(self):
        valid_fps = self._fps_list()
        if len(valid_fps) == 0:
            if self._verbosity > 0:
                print("all centroiders stopped already")
        for fps in valid_fps:
            if self._verbosity > 0:
                print(f"stopping {fps.name}")
            # stop run (if running)
            fps.run_stop()
            # stop conf (if confing)
            fps.conf_stop()
            # close tmux (if tmuxing)
            subprocess.run([
                "tmux",
                "kill-session",
                "-t",
                f"{fps.name}"
            ], capture_output=True, check=False, cwd="/tmp/")
            # delete FPS
            dirname = os.environ["MILK_SHM_DIR"]
            filename = fps.name+".fps.shm"
            pathname = os.path.abspath(os.path.join(dirname, filename))
            if pathname.startswith(dirname):
                os.remove(pathname)

        with redirect_stdout():
            try:
                fps = FPS("slopevec")
            except RuntimeError:
                fps = None
        if fps:
            if self._verbosity > 0:
                print(f"stopping {fps.name}")
            # stop run (if running)
            fps.run_stop()
            # stop conf (if confing)
            fps.conf_stop()
            # close tmux (if tmuxing)
            subprocess.run([
                "tmux",
                "kill-session",
                "-t",
                f"{fps.name}"
            ], capture_output=True, check=False, cwd="/tmp/")
            # delete FPS
            dirname = os.environ["MILK_SHM_DIR"]
            filename = fps.name+".fps.shm"
            pathname = os.path.abspath(os.path.join(dirname, filename))
            if pathname.startswith(dirname):
                os.remove(pathname)

        self._clean(cleanshm=True)

    @staticmethod
    def _parse_launch_result(result):
        if result.stderr is None:
            return None
        # so far, just look for "WARNING (PID XXXX) Cannot open shm file ..."
        warnings = result.stderr.decode().split("Cannot open shm file")[1:]
        warnings = [
            f'    missing shm: {s.split("\"")[1]}'
            for s in warnings
        ]
        return "\n".join(warnings)

    def _fps_list(self) -> list:
        """returns list of living FPS instances"""
        fps_list = []
        for idx in self._indices:
            name = f"{self._fpsprefix:s}{idx:01d}"
            with redirect_stdout():
                try:
                    fps = FPS(name)
                    fps_list.append(fps)
                except RuntimeError:
                    # no problem, just that the FPS doesn't exists.
                    # would be more comforting if there was a more specific
                    # "FPSNotExistError" available, but this is fine.
                    pass
        return fps_list

    def config(self):
        """load/save the centroider config from/to a file"""
        parser = argparse.ArgumentParser(
            description='configure centroiders',
            )
        parser.add_argument(
            "action", help="action to perform on configuration",
            choices=["load", "init", "edit", "plot", "fit"]
        )
        parser.add_argument(
            "--nframes", "-n", type=int, default=10,
            help="number of frames to use (e.g., for `cent config fit -n=10`)",
        )
        args = self._standard_args(parser)

        filename = os.path.abspath(args.filename)
        if args.action == "load":
            self._config_load(filename)
        elif args.action == "init":
            self._config_init(filename)
        elif args.action == "fit":
            self._config_fit(filename, nframes=args.nframes)
        elif args.action == "plot":
            self._config_load(filename, apply=False)
            self._config_plot()
        elif args.action == "edit":
            editor = "nano"
            if "EDITOR" in os.environ:
                editor = os.environ["EDITOR"]
            subprocess.run([editor, filename])
            self._config_load(filename)
        else:
            raise RuntimeError(
                "This should be unreachable, how did you get here?"
            )

    def _config_load(self, filename, apply=True):
        # Loading configs from file
        with open(filename, "r") as f:
            configs = yaml.safe_load(f)
        if self._verbosity > 0:
            print(f"reading configs from:\n{filename}")

        _configs = {}  # new config
        if len(configs.items()) == 0:
            if self._verbosity > 0:
                print("no WFSs in config file, exiting.")
                exit(1)
        for idx, config in configs.items():
            if self._verbosity > 0:
                print(f"loading config {idx}")
            _configs[idx] = Config.from_dict(config)
        self._configs = _configs
        if apply:
            self._config_apply()

    def _config_init(self, filename):
        configs = {
            idx: {
                "deltax": 0.0,
                "deltay": 0.0,
                "img_w": 256,
                "img_h": 256,
                "pitch_x": 6.9,
                "pitch_y": 6.9,
                "n_subx": 32,
                "n_suby": 32,
                "fov_x": 6,
                "fov_y": 6,
                "theta": float(np.pi*idx),
                "cogthresh": 0.0,
                "bgnpix": 22,
            } for idx in self._indices
        }
        configs = {
            idx: Config.from_dict(config)
            for idx, config in configs.items()
        }
        self._config_save(filename, configs=configs)
        # load the configs via disk to make sure everything is bulletproof
        self._config_load(filename)

    def _config_fit(self, filename, nframes=10):
        # open config file to extract nsub* img* and any other non-fitted
        # params. Need to allow a reduced set of parameters defined in config,
        with open(filename, "r") as f:
            configs = yaml.safe_load(f)
        if not configs:
            if self._verbosity > 0:
                print(f"empty config file: {filename}\nTry `config init`")
            exit(1)
        if self._verbosity > 0:
            print(f"reading configs from:\n{filename}")

        # These are the parameters required to be defined at minimum.
        required_params = [
            "n_subx",  # number of subaps in x-dimension
            "n_suby",  # number of subaps in y-dimension
            "fov_x",   # fov for subaperture (in pixels) (x)
            "fov_y",   # fov for subaperture (in pixels) (y)
        ]

        # Then, one by one, take WFS frames and fit config parameters to them
        printed_header = False
        for idx in self._indices:
            if idx not in configs:
                if self._verbosity > 0:
                    print(f"wfs{idx:01d} missing from config: {filename}")
                continue
            config = configs[idx]
            good = True
            for param in required_params:
                if param in config:
                    continue
                if self._verbosity > 0:
                    print(
                        f"{param} not defined for wfs{idx:01d} in {filename}"
                    )
                good = False
            if not good:
                if self._verbosity > 0:
                    print(f"can't fit config for wfs{idx:01d}")
                continue

            n_subx = config["n_subx"]
            n_suby = config["n_suby"]

            # get wfs frame
            shm = SHM(f"scmos{idx:01d}_data")
            im = np.mean([
                shm.get_data(check=True).astype(np.float32)
                for _ in range(nframes)
            ], axis=0)
            im -= SHM(f"scmos{idx:01d}_bg").get_data()
            img_h, img_w = im.shape

            if not printed_header:
                fit.print_header()
                printed_header = True
            # fit config params
            deltax, deltay, _, pitch_x, pitch_y = fit.fit_config(
                im, idx, n_subx=n_subx, n_suby=n_suby,
                min_pitch=5.0, max_pitch=8.0
            )

            # save to local config dict
            config["pitch_x"] = pitch_x
            config["pitch_y"] = pitch_y
            config["deltax"] = deltax
            config["deltay"] = deltay
            # config["theta"] = theta
            config["img_w"] = img_w
            config["img_h"] = img_h

            if "cogthresh" not in config.keys():
                config["cogthresh"] = 0.0
            if "bgnpix" not in config.keys():
                config["bgnpix"] = 22
            # convert config dict to Config obj
            # save to local _configs dict
            configs[idx] = Config.from_dict(config)

        for idx, config in configs.items():
            if type(config) is Config:
                continue
            configs[idx] = Config.from_dict(config)
        # replace entries of config with those fitted above, for the WFSs that
        # were fitted. Leave other entries in yaml file alone.
        # save config to disk
        self._config_save(filename, configs=configs)
        # load config from disk and apply to shm
        self._config_load(filename, apply=True)
        for idx in self._indices:
            result = fit.fine_tune(idx, nframes=nframes)
            if result is not None:
                configs[idx].deltax += float(result[0])
                configs[idx].deltay += float(result[1])
            thresh_mean, thresh_std = fit.estimate_thresh(idx, nframes=nframes)
            if result is not None:
                configs[idx].cogthresh += float(thresh_mean)
                print(thresh_mean, thresh_std)
        self._config_save(filename, configs=configs)
        self._config_load(filename, apply=True)

    def _config_plot(self, configs=None):
        """plot the configuration provided"""
        if not configs:
            if self._configs:
                configs = self._configs
            else:
                raise RuntimeError("configs not provided nor previously set")
        import matplotlib.pyplot as plt
        for idx, config in configs.items():
            xx_c, yy_c, xx_0, yy_0 = config.build_lut()
            bld.plot_lut(img_w=config.img_w, img_h=config.img_h,
                         fov_x=config.fov_x, fov_y=config.fov_y,
                         xx_0=xx_0, yy_0=yy_0, xx_c=xx_c, yy_c=yy_c,
                         title=f"WFS {idx}")
        plt.show()

    def _config_apply(self, configs=None):
        """apply config, either the provided one or the one in the object"""
        if configs is None:
            if self._configs:
                configs = self._configs
            else:
                raise RuntimeError("configs not provided nor previously set")

        for idx in self._indices:
            # build lookup table for shm based on config
            xx_c, yy_c, _, _ = configs[idx].build_lut()
            lutxname = f"lutx{idx:01d}"
            lutyname = f"luty{idx:01d}"
            with redirect_stdout():
                try:
                    shm = SHM(lutxname)
                    shm.set_data(xx_c)
                except FileNotFoundError:
                    shm = SHM(lutxname, xx_c)
                try:
                    shm = SHM(lutyname)
                    shm.set_data(yy_c)
                except FileNotFoundError:
                    shm = SHM(lutyname, yy_c)
                # also apply fov from config to fps
                try:
                    fps = FPS(f"{self._fpsprefix:s}{idx:01d}")
                except RuntimeError:
                    if self._verbosity > 0:
                        print(f"FPS doesn't exist, skipping wfs{idx:01d}")
                    continue
                running = fps.run_isrunning()
                if running:
                    while fps.run_isrunning():
                        fps.run_stop()
                fov_x = configs[idx].fov_x
                fov_y = configs[idx].fov_y
                cogthresh = configs[idx].cogthresh
                bgnpix = configs[idx].bgnpix
                fps.set_param("fovx", fov_x)
                while fps.get_param("fovx") != fov_x:
                    fps.set_param("fovx", fov_x)
                fps.set_param("fovy", fov_y)
                while fps.get_param("fovy") != fov_y:
                    fps.set_param("fovy", fov_y)
                fps.set_param("cogthresh", cogthresh)
                while fps.get_param("cogthresh") != cogthresh:
                    fps.set_param("cogthresh", cogthresh)
                fps.set_param("bgnpix", bgnpix)
                while fps.get_param("bgnpix") != bgnpix:
                    fps.set_param("bgnpix", bgnpix)
                if running:
                    while not fps.run_isrunning():
                        fps.run_start()
            # could do other params here too, like bgnpix,
            # cogthresh, fluxthresh

            if self._verbosity > 0:
                print(f"wrote lutx{idx:01d} and luty{idx:01d} to shm")

    def _config_save(self, filename, configs=None):
        if configs is None:
            configs = self._configs
        if configs is None:
            if self._verbosity > 0:
                print("refusing to save empty config")
                exit(1)
        # Saving current config
        with open(filename, "w") as f:
            yaml.dump(
                {
                    idx: config.to_dict()
                    for idx, config in configs.items()
                }, f
            )
        if self._verbosity > 0:
            print(f"saved configs to:\n{filename}")

    def _clean(self, cleanshm=False):
        """clean crumbs in shm dir. Shouldn't be necessary but it is"""
        from glob import glob

        def rm(files):
            for file in files:
                if self._verbosity > 0:
                    print(f"rm {file}")
                os.remove(file)

        rm(glob(os.environ["MILK_SHM_DIR"] + "/milkCLIstartup.centroider*"))
        rm(glob(os.environ["MILK_SHM_DIR"] + "/milkCLIstartup.slopevec*"))
        if cleanshm:
            rm(glob(os.environ["MILK_SHM_DIR"] + "/flux*.im.shm"))
            rm(glob(os.environ["MILK_SHM_DIR"] + "/lutx*.im.shm"))
            rm(glob(os.environ["MILK_SHM_DIR"] + "/luty*.im.shm"))
            rm(glob(os.environ["MILK_SHM_DIR"] + "/slopemap*.im.shm"))
            rm(glob(os.environ["MILK_SHM_DIR"] + "/slopevec.im.shm"))
            rm(glob(os.environ["MILK_SHM_DIR"] + "/proc.centroider*.shm"))
            rm(glob(os.environ["MILK_SHM_DIR"] + "/proc.slopevec*.shm"))
            rm(glob(os.environ["MILK_SHM_DIR"] + "/processinfo.list.shm"))

    def status(self):
        """Print current status of centroider"""
        # print status to stdout
        fps_list = self._fps_list()
        if len(fps_list) != 5:
            print("WARNING, some centroiders are missing."
                  " Consider restarting them.")
        for fps in fps_list:
            print(f"{fps.name}")
            print(f"    running: {fps.conf_isrunning()}")
            print(f"    confing: {fps.run_isrunning()}")

    def wgui(self):
        """Launch centroider ui"""
        parser = argparse.ArgumentParser(
            description='start/stop web gui',
            )
        parser.add_argument(
            "action", help="view/change wgui status",
            choices=["start", "stop", "status"]
        )
        args = self._standard_args(parser)

        if args.action == "start":
            if self._wgui_status() == 0:
                print("wgui already running")
                self._print_wgui_output()
            else:
                self._wgui_start()
                if self._wgui_status() == 0:
                    time.sleep(2.0)
                    print("wgui started successfully")
                    self._print_wgui_output()
                else:
                    print("wgui failed to start")
        elif args.action == "stop":
            self._wgui_kill()
        elif args.action == "status":
            if self._wgui_status() == 0:
                print("wgui alive")
                self._print_wgui_output()
            else:
                print("wgui dead")
        else:
            raise RuntimeError(
                "This should be unreachable, how did you get here?"
            )

    def _wgui_status(self) -> int:
        cmds = [
            "tmux",
            "has-session",
            "-t",
            self._wgui_sessionname
        ]
        result = subprocess.run(cmds, capture_output=True, cwd="/tmp/")
        return result.returncode

    def _wgui_start(self):
        cmds = [
            "tmux",
            "new-session",
            "-d",
            "-s",
            self._wgui_sessionname,
            f"python {app.__file__}",
        ]
        subprocess.run(cmds, capture_output=True, cwd="/tmp/")

    def _wgui_kill(self) -> int:
        cmds = [
            "tmux",
            "kill-session",
            "-t",
            self._wgui_sessionname,
        ]
        subprocess.run(cmds, capture_output=True, cwd="/tmp/")

    def _print_wgui_output(self):
        cmds = [
            "tmux",
            "capture-pane",
            "-t",
            self._wgui_sessionname+":0",
            "-p",
            "-S",
            "-",
            "-E",
            "-"
        ]
        result = subprocess.run(cmds, capture_output=True, cwd="/tmp/")
        if result.returncode == 0:
            out = result.stdout.decode().split("\n")
            out = [o for o in out if len(o) > 0]
            out = [o for o in out if "Running on http" in o]
            print("\n".join(out))
        else:
            print("failed to capture wgui output")

    def recon(self):
        """Run the local reconstructor for a while"""
        reconstructor.main()


def main():
    CentroiderCLI()


if __name__ == "__main__":
    cli = CentroiderCLI()
