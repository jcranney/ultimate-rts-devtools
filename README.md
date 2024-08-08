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

The centroider is a standard milk functions, so for each WFS, there is an associated
milk-FPS defined during runtime. E.g., a normal startup will look like:
```echocent start
```


The pipeline proposed for the centroiding is:
```mermaid
graph TD
    subgraph A["aquisition PC"]
        style A fill:#777,stroke:#444,stroke-width:2px,color:#fff;
        subgraph sg1[centroid pipeline 1]
            cal01[calibrator\n+\ncentroider]
        end
        cal01--slope_vec_01-->concatenator
        subgraph sg2[centroid pipeline 2]
            cal02[calibrator\n+\ncentroider]
        end
        cal02--slope_vec_02-->concatenator
        subgraph sg3[centroid pipeline 3]
            cal03[calibrator\n+\ncentroider]
        end
        cal03--slope_vec_03-->concatenator
        subgraph sg4[centroid pipeline 4]
            cal04[calibrator\n+\ncentroider]
        end
        cal04--slope_vec_04-->concatenator
    end
    concatenator--cl_slopes-->RTS
    LGS1--raw_frame_01-->cal01
    LGS2--raw_frame_02-->cal02
    LGS3--raw_frame_03-->cal03
    LGS4--raw_frame_04-->cal04
```
with the possibility of combining the `calibrator` and `centroider` processes into a single `calibrate_and_centroid` process. The `concatenator` process would also be required to synchronize the 4 input streams before passing the slope vector to the RTS.

## Tomographic Reconstruction
For developing the tomographic reconstructor/pseudo-open-loop controller (POLC) we'll take a similar approach as the centroider, where we will build a process that writes to the slope vector in shared memory, triggering the start of a control iteration in the RTS.

The control pipeline proposed for the reconstructor is:
```mermaid
graph TD

aqu[aquisition PC]--cl_slopes-->add
AO3k
delay--applied_commands-->imat("D imat")
add((+))--pol_slope_vec-->recon("R recon")
recon--"ol_modes"-->mfilt
mfilt--command_modal-->dmproj("P dmproj")
dmproj--command_dm-->delay
imat--command_feedback_slopes-->add
dmproj--command_dm-->AO3k
```
with the possibility of combining the `calibrator` and `centroider` processes into a single `calibrate_and_centroid` process. The `concatenator` process would also be required to synchronize the 4 input streams before passing the slope vector to the RTS.

## TODO:
 - C-profiling/benchmarking for `centroider.c`
 - Simple closed-loop RTS, no POLC.
 - Allow centroider FPS to be created without shm initialised yet.