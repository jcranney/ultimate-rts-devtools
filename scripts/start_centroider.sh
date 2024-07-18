#!/bin/bash

# Create windows and panes
sh ./scripts/load_subap_lut.sh
python ./scripts/init_shm_centroiding.py
python ./scripts/init_valid.py
sh ./ltaomod_centroider/test_centroider.sh

echo "started centroider"