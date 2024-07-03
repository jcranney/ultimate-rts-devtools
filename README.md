# ULTIMATE Subaru RTS devtools
This repository is a collection of tools/scripts for developing and testing the RTS pipelines for the LTAO system of Subaru (ULTIMATE-START and ULTIMATE-GLAO).

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

## Replay telemetry buffer (WIP)
Replay a saved telemetry buffer, e.g., a simulated one. Data will be pushed to shared memory at 500 Hz.

Replay a simulation, (wip):
```bash
./replay_simulation.sh
```
