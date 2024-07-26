for session in replay
do
    tmux has-session -t $session 2>/dev/null
    if [ $? == 0 ]; then
        tmux kill-session -t $session
        echo "killed $session"
    fi
done
