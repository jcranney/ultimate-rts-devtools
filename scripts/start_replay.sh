#!/bin/bash
parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )

SESSION_NAME="replay"
FRAMERATE=30

tmux has-session -t $SESSION_NAME 2>/dev/null
if [ $? == 0 ]; then
    echo "$SESSION_NAME already exists, killing it"
    tmux kill-session -t $SESSION_NAME
fi

tmux new-session -d -s $SESSION_NAME

# Create windows and panes
tmux rename-window -t $SESSION_NAME:0 "replay buffer"
tmux send-keys "$parent_path/play_images.py $1 --fr 100" C-m
tmux send-keys "exit" C-m

echo "started $SESSION_NAME"
echo "  milk-streamCTRL  # to check streams"
