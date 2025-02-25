#!/bin/bash
set -x

export HYPERMIND_COLORS=true
while true; do
        pkill -f p2p
        pkill -f run_server
        python -m subnet.cli.run_server bigscience/bloom-petals "$@" 2>&1 | tee log_`date '+%F_%H:%M:%S'`
done
