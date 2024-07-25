#!/usr/bin/env python3

import argparse
import sys
import os
import subprocess
import contextlib
import yaml
from pyMilk.interfacing.fps import FPS

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


class CentroiderCLI():
    # following example from:
    # https://chase-seibert.github.io/blog/2014/03/21/python-multilevel-argparse.html

    # 1 NGS + 4 LGSs
    _indices = [0, 1, 2, 3, 4]
    # or to ignore the NGS:
    # _indices = [1, 2, 3, 4] 
    _fpsprefix = "centroider"
    _config = {}
    _default_config = os.environ["HOME"]+"/.config/centroider.yaml"

    def __init__(self, *args, **kwargs):
        commands = []
        for attribute in self.__dir__():
            if attribute[0] == "_":
                continue
            doc = getattr(self,attribute).__doc__
            if doc is None:
                doc = ""
            commands.append({
                "cmd" : attribute,
                "doc" : doc,
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
        ### Thoughts ###
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
        # So the config (either default or custom) is the ground truth, and used
        # every time the CLI is asked to start, restart, or config load.
        ### sthguohT ###

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
            default=self._default_config
        )
        
        args = parser.parse_args(sys.argv[2:])
        filename = os.path.abspath(args.filename)
        self._load_config(filename, quiet=quiet)
        # write luts/configs to shm
        # TODO UP TO HERE

        # create centroider FPS
        for idx in self._indices:
            milk_loopname=f"centroider{idx:02d}"
            milk_cmd=f"mload ltaomodcentroider;ltao.centroider {idx:01d};ltao.centroider _FPSINIT_;ltao.centroider _TMUXSTART_;"
            cmd = ["milk-exec", "-n", milk_loopname, milk_cmd]
            # start tmux session and fpsinit
            result = subprocess.run(cmd, capture_output=True)
            if not quiet:
                if result.returncode != 0:
                    print(f"failed to create {milk_loopname}")
        
        fps_list = self._fps_list()
        for fps in fps_list:
            fps.conf_start()
            fps.run_start()
            if not quiet:
                print(f"started {fps.name}")


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
        parser = argparse.ArgumentParser(
            description='configure centroiders',
            usage="""
    centroider config [-h] [--filename NAME] {save,load}
e.g.,
    centroider config --help
    centroider config load
    centroider config load --filename customconfig.yaml
    centroider config save --filename newconfig.yaml
        """)
        # prefixing the argument with -- means it's optional
        parser.add_argument(
            "action", help="action to perform on configuration",
            choices=["save","load","init"]
        )
        parser.add_argument(
            "--filename", help="path to config file (yaml)",
            default=self._default_config
        )
        # now that we're inside a subcommand, ignore the first
        # TWO argvs, ie the command (git) and the subcommand (commit)
        args = parser.parse_args(sys.argv[2:])
        filename = os.path.abspath(args.filename)

        if args.action == "save":
            self._save_config(filename, quiet=quiet)
        elif args.action == "load":
            self._load_config(filename, quiet=quiet)
        elif args.action == "init":
            self._init_config(filename, quiet=quiet)
        else:
            raise RuntimeError("This should be unreachable, how did you get here?")


    def _load_config(self, filename, quiet=False):
        # Loading config from file
        with open(filename,"r") as f:
            self._config = yaml.safe_load(f)
        if not quiet:
            print(f"loaded config from:\n{filename}")


    def _init_config(self, filename, quiet=False):
        config = {
            0 : {
                "X0" : -2.08,
                "IMG_W" : 300,
                "Y0" : 8.5,
                "IMG_H" : 256,
                "PITCH_X" : 6.9121,
                "PITCH_Y" : 6.9078,
                "N_SUBX" : 32,
                "N_SUBY" : 32,
            },
            1 : {
                "X0" : -6.0,
                "IMG_W" : 300,
                "Y0" : 12.0,
                "IMG_H" : 256,
                "PITCH_X" : 6.918,
                "PITCH_Y" : 6.903,
                "N_SUBX" : 32,
                "N_SUBY" : 32,
            },
            2 : {
                "X0" : -10.0,
                "IMG_W" : 300,
                "Y0" : 12.5,
                "IMG_H" : 256,
                "PITCH_X" : 6.876,
                "PITCH_Y" : 6.924,
                "N_SUBX" : 32,
                "N_SUBY" : 32,
            },
            3 : {
                "X0" : -3.5,
                "IMG_W" : 300,
                "Y0" : 9.0,
                "IMG_H" : 256,
                "PITCH_X" : 6.871,
                "PITCH_Y" : 6.909,
                "N_SUBX" : 32,
                "N_SUBY" : 32,
            },
            4 : {
                "X0" : 4.5,
                "IMG_W" : 256,
                "Y0" : -4.5,
                "IMG_H" : 256,
                "PITCH_X" : 6.823,
                "PITCH_Y" : 6.850,
                "N_SUBX" : 32,
                "N_SUBY" : 32,
            },
        }
        self._save_config(filename, config=config, quiet=quiet)
        # load the config via disk to make sure everything is bulletproof
        self._load_config(filename, quiet=quiet)


    def _save_config(self, filename, config=None, quiet=False):
        if config is None:
            config = self._config
        # Saving current config
        with open(filename,"w") as f:
            yaml.dump(self._config, f)
        if not quiet:
            print(f"saved config to:\n{filename}")        


    def stop(self, quiet=False):
        """Try to stop the centroiders"""
        valid_fps = self._fps_list()
        if len(valid_fps)==0:
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


    def reset(self):
        """Try to reset the centroiders"""
        self.stop()
        self.start()


    def status(self):
        """Print current status of centroider"""
        # print status to stdout
        fps_list = self._fps_list()
        if len(fps_list) != 5:
            print("WARNING, some centroiders are missing. Consider restarting them.")
        for fps in fps_list:
            print(f"{fps.name}")
            print(f"    running: {fps.conf_isrunning()}")
            print(f"    confing: {fps.run_isrunning()}")


    def fpsCTRL(self):
        # run milk-fpsCTRL with centroider filter
        my_env = os.environ.copy()
        my_env["FPS_FILTSTRING_NAME"] = "centroider"
        completed = subprocess.run(["milk-fpsCTRL"], env=my_env)
        # return success


    def bgpix(self):
        """Read/set number of bg pixels used in row subtraction"""
        pass


    def cogthresh(self):
        """Read/set centre of cgravity threshold for WFS"""
        pass


    def ui(self):
        """Launch centroider ui"""
        pass


def main():
    CentroiderCLI()


if __name__ == "__main__":
    main()
