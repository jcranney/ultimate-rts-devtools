# ULTIMATE Subaru RTS devtools
This repository is a collection of tools/scripts for developing and testing the 
RTS pipelines for the LTAO system of Subaru (ULTIMATE-START and ULTIMATE-GLAO).

## Install
Install requirements and centroider CLI:
```bash
pip install -e .
```

Install the `ltaomodcentroider` package for [milk](https://github.com/milk-org/milk):
```
./compile.sh
cd build
sudo make install
```
Note: the above should be changed to be in the proper format of a milk-plugin.

## Centroiding
The current implementation of the centroider for ULTIMATE-START resides in the 
milk module in this repo under `./ltaomod_centroider`. This directory is used only
to edit the centroider algorithm, or other low level algorithms on the aquisition
PC.

For interacting with the centroider, including:
- launching it,
- stopping it, 
- editing the configuration parameters,
- *etc*.,

there is a Python-written CLI. Installing the Python package from this repository 
(see [instructions above](#Setup)) exposes the `cent` executable, e.g.:
```echo
$ cent --help
usage: cent <command> [<args>]

The valid commands are:
     start     Try to start the centroiders
      stop     Try to stop the centroiders
    config     load/save the centroider config from/to a file
    status     Print current status of centroider
      wgui     Launch centroider ui
     recon     Run the local reconstructor for a while

positional arguments:
  command        Subcommand to run

options:
  -h, --help     show this help message and exit
  --verbose, -v  verbosity level

```
