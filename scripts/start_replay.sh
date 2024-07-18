#!/bin/bash
parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )

SESSION_NAME="replay"
FRAMERATE=30

tmux kill-session -t $SESSION_NAME

tmux new-session -d -s $SESSION_NAME

# Create windows and panes
tmux rename-window -t $SESSION_NAME:0 "replay buffer"
tmux send-keys "$parent_path/play_images.py $parent_path/../scmos_data --fr 100" C-m

echo "started $SESSION_NAME"