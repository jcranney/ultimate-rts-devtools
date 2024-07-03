#!/bin/bash

SESSION_NAME="replay"
CONF_FILE="config.json"
FRAMERATE=30

# Function to create panes in tmux
create_panes() {
    local window_name="$1"
    local panes=("${!2}")
    local cmd="$3"

    tmux new-window -t $SESSION_NAME: -n "$window_name"

    # Loop through each pane command and split accordingly
    for ((i=0; i<${#panes[@]}; i++)); do
        if [ $i -gt 0 ]; then
            tmux split-window -v
        fi
        tmux send-keys "$cmd ${panes[$i]} --fr=$FRAMERATE" C-m
    done
}


tmux has-session -t $SESSION_NAME 2>/dev/null

if [ $? == 0 ]; then
    echo "Session already exists, kill it with"
    echo "  tmux kill-session -t replay"
    exit
fi

tmux new-session -d -s $SESSION_NAME

# Read conf file and extract commands
N=$(jq '.wfs_streams | length' $CONF_FILE)
M=$(jq '.phi_streams | length' $CONF_FILE)
P=$(jq '.slope_streams | length' $CONF_FILE)

# Read wfs-streams and phi-streams from conf file
WFS_STREAMS=($(jq -r '.wfs_streams | .[]' $CONF_FILE))
PHI_STREAMS=($(jq -r '.phi_streams | .[]' $CONF_FILE))
SLOPE_STREAMS=($(jq -r '.slope_streams | .[]' $CONF_FILE))

# Create windows and panes
tmux rename-window -t $SESSION_NAME:0 "replay buffer"
tmux send-keys "cd scripts" C-m
tmux send-keys "ipython ./replay_all.py" C-m

create_panes "wfs streams" WFS_STREAMS[@] shmImshow.py
create_panes "phase streams" PHI_STREAMS[@] shmImshow.py
create_panes "slope streams" SLOPE_STREAMS[@] shmPlot.py