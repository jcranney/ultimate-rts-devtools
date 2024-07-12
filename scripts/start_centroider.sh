#!/bin/bash

SESSION_NAME="centroider"
CONF_FILE=".config/config_centroid.json"
FRAMERATE=30

# Function to create panes in tmux
create_panes() {
    local window_name="$1"
    local panes=("${!2}")
    local cmd="$3"

    # Loop through each pane command and split accordingly
    for ((i=0; i<${#panes[@]}; i++)); do
        tmux new-window -t $SESSION_NAME:
        tmux send-keys "$cmd ${panes[$i]} --fr=$FRAMERATE" C-m
    done
}


tmux has-session -t $SESSION_NAME 2>/dev/null

if [ $? == 0 ]; then
    echo "Session already exists, kill it with"
    echo "  tmux kill-session -t $SESSION_NAME"
    exit
fi

tmux new-session -d -s $SESSION_NAME

# Read conf file and extract commands
N=$(jq '.wfs_streams | length' $CONF_FILE)
P=$(jq '.slope_streams | length' $CONF_FILE)

# Read wfs-streams and phi-streams from conf file
WFS_STREAMS=($(jq -r '.wfs_streams | .[]' $CONF_FILE))
SLOPE_STREAMS=($(jq -r '.slope_streams | .[]' $CONF_FILE))

# Create windows and panes
make clean
make all
sh ./scripts/load_subap_lut.sh
python ./scripts/init_shm_centroiding.py
python ./scripts/init_valid.py
tmux rename-window -t $SESSION_NAME:0 "centroider"
tmux send-keys "./centroider1 &" C-m
tmux send-keys "./centroider2 &" C-m
tmux send-keys "./centroider3 &" C-m
tmux send-keys "./centroider4 &" C-m
tmux send-keys "./centroider5 &" C-m

create_panes "slope streams" SLOPE_STREAMS[@] shmPlot.py
create_panes "wfs streams" WFS_STREAMS[@] shmImshow.py

echo "started $SESSION_NAME"