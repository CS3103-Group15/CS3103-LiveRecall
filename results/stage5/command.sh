
python3 run_demo.py \
  --clients 20 \
  --duration 8 \
  --output-stem results/stage5/stage5_normal


python3 run_demo.py \
  --clients 20 \
  --duration 12 \
  --disconnect-percent 20 \
  --disconnect-at 3 \
  --disconnect-seconds 2 \
  --late-percent 10 \
  --late-seconds 4 \
  --output-stem results/stage5/stage5_recovery


python3 run_demo.py \
  --clients 100 \
  --duration 12 \
  --slow-percent 10 \
  --slow-ms 500 \
  --output-stem results/stage5/stage5_slow


python3 run_demo.py \
  --clients 100 \
  --duration 14 \
  --source-segments 8 \
  --slow-percent 10 \
  --slow-ms 500 \
  --output-stem results/stage5/stage5_slow_drain