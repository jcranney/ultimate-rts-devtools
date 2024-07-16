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

cd _build
cmake .. --install-prefix=/usr/local/milk-1.03.00
make
sudo make install
cd ..

tmux new-window -t $SESSION_NAME:
for LOOP in 1 2 3 4 5
do
    tmux send-keys "MILKCLI_ADD_LIBS=ltaomodcentroider milk" C-m
    echo "scmos${LOOP}_data"
    tmux send-keys "readshmim scmos${LOOP}_data" C-m
    tmux send-keys "ltao.helloworld ..procinfo 1" C-m
    tmux send-keys "ltao.helloworld scmos${LOOP}_data bob${LOOP} 10 10" C-m
    tmux send-keys "ltao.helloworld ..triggermode 3" C-m
    tmux send-keys "ltao.helloworld ..triggersname scmos${LOOP}_data" C-m
    tmux send-keys "ltao.helloworld ..loopcntMax -1" C-m
    tmux send-keys "ltao.helloworld .outim.shared 1" C-m
    tmux send-keys "ltao.helloworld _FPSINIT_ \"0${LOOP}\"" C-m
    #tmux send-keys "ltao.helloworld _CONFSTART_ \"0${LOOP}\"" C-m     # these freeze things, I think because each 
    #tmux send-keys "ltao.helloworld _RUNSTART_ \"0${LOOP}\"" C-m      # "running" process/conf needs a dedicated PID?
    tmux send-keys "exit" C-m
done

milk-fpsCTRL