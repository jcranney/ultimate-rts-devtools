#!/usr/bin/bash

SESSION_NAME="gui"
tmux has-session -t $SESSION_NAME 2>/dev/null
if [ $? == 0 ]; then
    echo "gui already running, leave it"
    exit
fi
tmux new-session -d -s $SESSION_NAME
tmux send-keys "python -m flask run --debug --host=0.0.0.0" C-m
tmux new-window
tmux send-keys "cd stream-frontend" C-m
tmux send-keys "npm start" C-m
