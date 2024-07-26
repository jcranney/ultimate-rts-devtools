#!/usr/bin/bash

SESSION_NAME="gui"
tmux has-session -t $SESSION_NAME 2>/dev/null
if [ $? == 0 ]; then
    echo "$SESSION_NAME already running, killing it"
    tmux kill-session -t $SESSION_NAME
fi
tmux new-session -d -s $SESSION_NAME
tmux send-keys "python -m flask run --debug --host=0.0.0.0" C-m
sleep 1
echo "started gui:"
tmux capture-pane -t gui:0 -p | grep Running