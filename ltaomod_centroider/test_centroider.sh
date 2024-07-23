#!/bin/bash

for WFS in 1 2 3 4 0
do
    MILK_LOOPNAME="centroider0$WFS"
    MILK_CMD="mload ltaomodcentroider;ltao.centroider $WFS;ltao.centroider _FPSINIT_;ltao.centroider _TMUXSTART_;"
    milk-exec -n $MILK_LOOPNAME "$MILK_CMD"
    tmux send-keys -t $MILK_LOOPNAME:1 "milk-exec -n $MILK_LOOPNAME \"mload ltaomodcentroider; ltao.centroider _CONFSTART_\"" C-m
    tmux send-keys -t $MILK_LOOPNAME:2 "milk-exec -n $MILK_LOOPNAME \"mload ltaomodcentroider; ltao.centroider _RUNSTART_\"" C-m
done
