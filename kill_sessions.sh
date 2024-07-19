for session in centroider01 centroider02 centroider03 centroider04 centroider00 replay
do
    tmux has-session -t $session 2>/dev/null
    if [ $? == 0 ]; then
        tmux kill-session -t $session
        echo "killed $session"
    fi
done
