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
from .build_subap_lut import build_lut, plot_lut
import numpy as np


# This redirect class allows suppression of the C-code prints that mess up the
# terminal. E.g.:
#
#   with redirect_stdout():
#       fps = FPS(f"{self._fpsprefix:s}{idx:02d}")
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

    @staticmethod
    def from_dict(config_dict: dict):
        return Config(**config_dict)

    def to_dict(self):
        return self.__dict__

    def build_lut(self):
        xx_c, yy_c, xx_0, yy_0 = build_lut(
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

    # this is a dict with WFS idx as key (not a list, because we don't
    # want to be restricted to always having 0,1,2,... wfs numbering,
    # e.g., when NGS truth sensor is not used, we won't use 0)
    _config: None
    _default_configfile = os.environ["HOME"]+"/.config/centroider.yaml"

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
        usage = """
centroider <command> [<args>]

The valid commands are:
"""
        usage += "\n".join([
            f"{command["cmd"]:>10s}     {command["doc"]:<s}"
            for command in commands
        ])
        parser = argparse.ArgumentParser(usage=usage)
        parser.add_argument("command", help="Subcommand to run")
        args = parser.parse_args(sys.argv[1:2])

        if not hasattr(self, args.command):
            print(f"Unrecognized centroider command: `{args.command}`")
            parser.print_help()
            exit(1)

        # use dispatch pattern to invoke method with same name
        getattr(self, args.command)()

    def start(self, quiet=False):
        """Try to start the centroiders"""
        # Thoughts ###################
        # How should this act?
        # I think by default, we would want to run:
        # ```bash
        # centroider start
        # ```
        # and this would fail if a configuration is not provided. In that case,
        # the user could build a configuration by running (e.g.):
        # ```bash
        # centroider init   # --force to overwrite existing config
        # ```
        # So the config (either default or custom) is the ground truth, and is
        # used every time the CLI is asked to start, or config load.
        # sthguohT ###################

        parser = argparse.ArgumentParser(
            description='start centroiders, using config on disk',
            usage="""
    centroider start [-h] [--filename NAME]
e.g.,
    centroider start
    centroider start --help
    centroider start --filename customconfig.yaml
        """)
        parser.add_argument(
            "--filename", help="centroider configuration filename",
            default=self._default_configfile
        )

        args = parser.parse_args(sys.argv[2:])
        filename = os.path.abspath(args.filename)

        fps_list = self._fps_list()
        if len(fps_list) == len(self._indices):
            if not quiet:
                print("all FPSs aleady exist, aborting (maybe `stop` first?)")
            exit(0)
        self.clean(quiet=True)

        self._load_configs(filename, quiet=quiet)
        self._start(quiet=quiet)

    def _start(self, quiet=False):
        # write luts/configs to shm
        # TODO UP TO HERE

        # create centroider FPS
        for idx in self._indices:
            milk_loopname = f"centroider{idx:02d}"
            milk_cmd = (f"mload ltaomodcentroider;"
                        f"ltao.centroider {idx:01d};"
                        f"ltao.centroider _FPSINIT_;"
                        f"ltao.centroider _TMUXSTART_;"
                        f"exit;")
            cmd = ["milk-exec", "-n", milk_loopname, milk_cmd]
            # start tmux session and fpsinit
            result = subprocess.run(cmd, capture_output=True)
            warning_string = self._parse_launch_result(result)
            if not quiet:
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
            if not quiet:
                print(f"started {fps.name}")

    @staticmethod
    def _parse_launch_result(result):
        if result.stderr is None:
            return None
        # so far, just look for "WARNING (PID XXXX) Cannot open shm file ..."
        warnings = result.stderr.decode().split("Cannot open shm file")[1:]
        warnings = [
            f'    missing required shm: {s.split("\"")[1]}'
            for s in warnings
        ]
        return "\n".join(warnings)

    def _fps_list(self) -> list:
        """returns list of living FPS instances"""
        fps_list = []
        for idx in self._indices:
            name = f"{self._fpsprefix:s}{idx:02d}"
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

    def config(self, quiet=False):
        """load/save the centroider config from/to a file"""
        parser = argparse.ArgumentParser(
            description='configure centroiders',
            )
        # prefixing the argument with -- means it's optional
        parser.add_argument(
            "action", help="action to perform on configuration",
            choices=["load", "init", "edit", "plot"]
        )
        parser.add_argument(
            "--filename", help="path to config file (yaml)",
            default=self._default_configfile
        )
        # now that we're inside a subcommand, ignore the first
        # TWO argvs, ie the command (git) and the subcommand (commit)
        args = parser.parse_args(sys.argv[2:])
        filename = os.path.abspath(args.filename)

        if args.action == "load":
            self._load_configs(filename, quiet=quiet)
        elif args.action == "init":
            self._init_configs(filename, quiet=quiet)
        elif args.action == "plot":
            self._load_configs(filename, quiet=quiet, apply=False)
            self._plot_configs(quiet=quiet)
        elif args.action == "edit":
            editor = "nano"
            if "EDITOR" in os.environ:
                editor = os.environ["EDITOR"]
            subprocess.run([editor, filename])
            self._load_configs(filename, quiet=quiet)
        else:
            raise RuntimeError(
                "This should be unreachable, how did you get here?"
            )

    def _load_configs(self, filename, quiet=False, apply=True):
        # Loading configs from file
        with open(filename, "r") as f:
            configs = yaml.safe_load(f)
        if not quiet:
            print(f"reading configs from:\n{filename}")

        _configs = {}  # new config
        if len(configs.items()) == 0:
            if not quiet:
                print("no WFSs in config file, exiting.")
                exit(1)
        for idx, config in configs.items():
            print(f"loading config {idx}")
            _configs[idx] = Config.from_dict(config)
        self._configs = _configs
        if apply:
            self._apply_configs(quiet=quiet)

    def _init_configs(self, filename, quiet=False):
        configs = {
            1: {
                "deltax": -2.08,
                "deltay": 8.5,
                "img_w": 300,
                "img_h": 256,
                "pitch_x": 6.9121,
                "pitch_y": 6.9078,
                "n_subx": 32,
                "n_suby": 32,
                "fov_x": 6,
                "fov_y": 6,
                "theta": 0.0,
            },
            2: {
                "deltax": -6.0,
                "deltay": 12.0,
                "img_w": 300,
                "img_h": 256,
                "pitch_x": 6.918,
                "pitch_y": 6.903,
                "n_subx": 32,
                "n_suby": 32,
                "fov_x": 6,
                "fov_y": 6,
                "theta": 0.0,
            },
            3: {
                "deltax": -10.0,
                "deltay": 12.5,
                "img_w": 300,
                "img_h": 256,
                "pitch_x": 6.876,
                "pitch_y": 6.924,
                "n_subx": 32,
                "n_suby": 32,
                "fov_x": 6,
                "fov_y": 6,
                "theta": 0.0,
            },
            4: {
                "deltax": -3.5,
                "deltay": 9.0,
                "img_w": 300,
                "img_h": 256,
                "pitch_x": 6.871,
                "pitch_y": 6.909,
                "n_subx": 32,
                "n_suby": 32,
                "fov_x": 6,
                "fov_y": 6,
                "theta": 0.0,
            },
            0: {
                "deltax": 4.5,
                "deltay": -4.5,
                "img_w": 256,
                "img_h": 256,
                "pitch_x": 6.823,
                "pitch_y": 6.850,
                "n_subx": 32,
                "n_suby": 32,
                "fov_x": 6,
                "fov_y": 6,
                "theta": 0.0,
            },
        }
        configs = {
            idx: Config.from_dict(config)
            for idx, config in configs.items()
        }
        self._save_configs(filename, configs=configs, quiet=quiet)
        # load the configs via disk to make sure everything is bulletproof
        self._load_configs(filename, quiet=quiet)

    def _plot_configs(self, configs=None, quiet=False):
        """plot the configuration provided"""
        if not configs:
            if self._configs:
                configs = self._configs
            else:
                raise RuntimeError("configs not provided nor previously set")
        import matplotlib.pyplot as plt
        for idx, config in configs.items():
            xx_c, yy_c, xx_0, yy_0 = config.build_lut()
            plot_lut(img_w=config.img_w, img_h=config.img_h,
                     fov_x=config.fov_x, fov_y=config.fov_y,
                     xx_0=xx_0, yy_0=yy_0, xx_c=xx_c, yy_c=yy_c,
                     title=f"WFS {idx}")
        plt.show()

    def _apply_configs(self, configs=None, quiet=False):
        """apply config, either the provided one or the one in the object"""
        if configs is None:
            if self._configs:
                configs = self._configs
            else:
                raise RuntimeError("configs not provided nor previously set")

        for idx in self._indices:
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
                    shm = SHM(lutxname, yy_c)
            if not quiet:
                print(f"wrote lutx{idx:01d} and luty{idx:01d} to shm")

    def _save_configs(self, filename, configs=None, quiet=False):
        if configs is None:
            configs = self._configs
        if configs is None:
            if not quiet:
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
        if not quiet:
            print(f"saved configs to:\n{filename}")

    def stop(self, quiet=False):
        """Try to stop the centroiders"""
        valid_fps = self._fps_list()
        if len(valid_fps) == 0:
            if not quiet:
                print("all centroiders stopped already")
        for fps in valid_fps:
            if not quiet:
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
            ], capture_output=True, check=False)
            # delete FPS
            dirname = os.environ["MILK_SHM_DIR"]
            filename = fps.name+".fps.shm"
            pathname = os.path.abspath(os.path.join(dirname, filename))
            if pathname.startswith(dirname):
                os.remove(pathname)
        self.clean(quiet=True)

    def clean(self, quiet=False):
        """clean crumbs in shm dir. Shouldn't be necessary but it is"""
        import glob
        files = glob.glob(os.environ["MILK_SHM_DIR"] +
                          "/milkCLIstartup.centroider0*")
        for file in files:
            if not quiet:
                print(f"rm {file}")
            os.remove(file)

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

    def fpsCTRL(self):
        """Launch milk-fpsCTRL with centroider filter on fps's"""
        # run milk-fpsCTRL with centroider filter
        my_env = os.environ.copy()
        my_env["FPS_FILTSTRING_NAME"] = "centroider"
        subprocess.run(["milk-fpsCTRL"], env=my_env)
        # return success

    def setparam(self):
        """set parameter for centroiders"""
        pass

    def getparam(self):
        """get parameter for centroiders"""
        pass

    def ui(self):
        """Launch centroider ui"""
        pass


def main():
    CentroiderCLI()


if __name__ == "__main__":
    cli = CentroiderCLI()
