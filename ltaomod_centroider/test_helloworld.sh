#!/bin/bash
SESSION_NAME=ltaomodtest

tmux has-session -t $SESSION_NAME 2>/dev/null

if [ $? == 0 ]; then
    echo "Session already exists, killing it"
    tmux kill-session -t $SESSION_NAME
    exit
fi

tmux new-session -d -s $SESSION_NAME
tmux send-keys "cd .." C-m "scripts/start_replay.sh" C-m
sleep 1

mkdir -p _build
cd _build
cmake .. --install-prefix=/usr/local/milk-1.03.00
make
sudo make install
cd ..


tmux new-window -t $SESSION_NAME:
for WFS in 1 2 3 4 0
do
    echo "scmos${WFS}_data"
    tmux send-keys "MILKCLI_ADD_LIBS=ltaomodcentroider milk" C-m
    tmux send-keys "ltao.helloworld ${WFS}" C-m
    tmux send-keys "ltao.helloworld _FPSINIT_ \"0${WFS}\"" C-m
    tmux send-keys "exit" C-m
done

milk-fpsCTRL