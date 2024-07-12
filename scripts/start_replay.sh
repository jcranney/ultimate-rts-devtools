#!/bin/bash

SESSION_NAME="replay"
FRAMERATE=30

tmux has-session -t $SESSION_NAME 2>/dev/null

if [ $? == 0 ]; then
    echo "Session already exists, kill it with"
    echo "  tmux kill-session -t $SESSION_NAME"
    exit
fi

tmux new-session -d -s $SESSION_NAME

# Create windows and panes
tmux rename-window -t $SESSION_NAME:0 "replay buffer"
tmux send-keys "./scmos_data/play_images.py scmos_data --fr 100" C-m

echo "started $SESSION_NAME"