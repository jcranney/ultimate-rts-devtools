SESSION_NAME="gui"
tmux has-session -t $SESSION_NAME 2>/dev/null
if [ $? == 0 ]; then
    tmux kill-session -t $SESSION_NAME
    echo "killed $SESSION_NAME"
fi
