#!/bin/bash
parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )

source $parent_path/load_subap_lut.sh
python ./scripts/init_shm_centroiding.py
source $parent_path/../ltaomod_centroider/test_centroider.sh

echo "started centroider"