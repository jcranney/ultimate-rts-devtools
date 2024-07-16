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
    echo "scmos${LOOP}_data"
    tmux send-keys "MILKCLI_ADD_LIBS=ltaomodcentroider milk" C-m
    tmux send-keys "readshmim scmos${LOOP}_data" C-m
    tmux send-keys "readshmim wfsvalid0${LOOP}" C-m
    tmux send-keys "readshmim lut_xx_0_lgs0${LOOP}" C-m
    tmux send-keys "readshmim lut_yy_0_lgs0${LOOP}" C-m
    tmux send-keys "ltao.centroider ..procinfo 1" C-m
    tmux send-keys "ltao.centroider scmos${LOOP}_data wfsvalid0${LOOP} lut_xx_0_lgs0${LOOP} lut_yy_0_lgs0${LOOP} fluxmap0${LOOP} 32 32 slopemap0${LOOP} 32 64 slopevec0${LOOP} 1024 1" C-m
    tmux send-keys "ltao.centroider ..triggermode 3" C-m
    tmux send-keys "ltao.centroider ..triggersname scmos${LOOP}_data" C-m
    tmux send-keys "ltao.centroider ..loopcntMax -1" C-m
    tmux send-keys "ltao.centroider .fluxmap_im.shared 1" C-m
    tmux send-keys "ltao.centroider .slopemap_im.shared 1" C-m
    tmux send-keys "ltao.centroider .slopevec_im.shared 1" C-m
    tmux send-keys "ltao.centroider _FPSINIT_ \"0${LOOP}\"" C-m
    tmux send-keys "exit" C-m
done

sleep 1
milk-fpsCTRL