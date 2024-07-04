# ULTIMATE Subaru RTS devtools
This repository is a collection of tools/scripts for developing and testing the RTS pipelines for the LTAO system of Subaru (ULTIMATE-START and ULTIMATE-GLAO).

<p align="center">
    <img style="width:100%" src="https://raw.githubusercontent.com/jcranney/ultimate-rts-devtools/main/screenshot.png"
        alt="screenshot.png"/>
</p>

## Setup
Install requirements:
```bash
pip install -r requirements.txt
```

## Python scripts
Run a script, e.g., to build WFS simulator telemetry:
```bash
cd ./scripts
python ./make_simulated_data.py
```

## Centroiding
For developing a centroiding process, we've decided that it would be useful to have a process that dumps WFS images to shm, so that they can be fetched by a centroider which can in-turn save a slope vector to disk.

The pipeline proposed for the centroiding is:
```mermaid
graph TD
    subgraph A["aquisition PC"]
        style A fill:#777,stroke:#444,stroke-width:2px,color:#fff;
        subgraph sg1[centroid pipeline 1]
            cal01[calibrator]--clean_frame_01-->cent01[centroider]
        end
        cent01--slope_vec_01-->concatenator
        subgraph sg2[centroid pipeline 2]
            cal02[calibrator]--clean_frame_02-->cent02[centroider]
        end
        cent02--slope_vec_02-->concatenator
        subgraph sg3[centroid pipeline 3]
            cal03[calibrator]--clean_frame_03-->cent03[centroider]
        end
        cent03--slope_vec_03-->concatenator
        subgraph sg4[centroid pipeline 4]
            cal04[calibrator]--clean_frame_04-->cent04[centroider]
        end
        cent04--slope_vec_04-->concatenator
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

## Replay telemetry buffer
Replay a saved telemetry buffer, e.g., a simulated one. Data will be pushed to shared memory at 500 Hz. See screenshot above.

Replay a simulation:
```bash
./replay_simulation.sh
```
or, e.g.,
```bash
./replay_wfs00.sh
```


## Known Issues
 - `./replay_simulation.sh` will fail the first time after reboot, because `shmImshow.py lgswfs*` will try to load streams that haven't been created yet. Hack fix is to do:
 ```bash
 ./replay_all.sh
 ## this will start replaying the buffer, but fail to show the images
 ## ...
 ## wait for ~10 seconds
 ## ...
 ## then:
 tmux kill-session -t replay
 ./replay_all.sh
 ```
 Note that you need to run `./scripts/make_simulated_data.py` first to save the simulated telemetry to disk.

## TODO:
 - C-profiling/benchmarking for `centroider.c`
 - `procCTRL`-ify the centroider,
 - Simple closed-loop RTS, no POLC.