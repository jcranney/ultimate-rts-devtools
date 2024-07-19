#!/bin/bash

for LOOP in 1 2 3 4 5
do
    MILK_LOOPNAME="centroider0$LOOP"
    MILK_CMD="mload ltaomodcentroider;ltao.centroider $LOOP;ltao.centroider _FPSINIT_;ltao.centroider _TMUXSTART_;"
    milk-exec -n $MILK_LOOPNAME "$MILK_CMD"
    #milk-exec -n centroider05 "mload ltaomodcentroider; ltao.centroider 5; ltao.centroider _FPSINIT_;"
    tmux send-keys -t $MILK_LOOPNAME:1 "milk-exec -n $MILK_LOOPNAME \"mload ltaomodcentroider; ltao.centroider _CONFSTART_\"" C-m
    tmux send-keys -t $MILK_LOOPNAME:2 "milk-exec -n $MILK_LOOPNAME \"mload ltaomodcentroider; ltao.centroider _RUNSTART_\"" C-m
done
