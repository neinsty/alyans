#!/usr/bin/env bash
# play_viz.sh — проигрывание rosbag Go2 в RViz (внутри контейнера)
# Только лидар + одометрия + TF + /lowstate, RealSense не используется.
#
# Использование (баг должен лежать в смонтированной папке /ros2_ws):
#   ./play_viz.sh /ros2_ws/go2_realsense_session_01
#   ./play_viz.sh /ros2_ws/bag 2.0
#   ./play_viz.sh /ros2_ws/bag 1.0 --loop
set -euo pipefail

BAG=${1:?"Укажи путь к rosbag: ./play_viz.sh /ros2_ws/<bag> [rate]"}
RATE=${2:-1.0}
EXTRA=${3:-}

# --- Проигрывание бага ------------------------------------------------------
ros2 bag play "$BAG" --clock 100 --rate "$RATE" $EXTRA &
BAG_PID=$!

# --- RViz ------------------------------------------------------------------
ros2 run rviz2 rviz2 -d /opt/go2_playback/go2.rviz \
  --ros-args -p use_sim_time:=true
RVIZ_PID=$!

trap 'kill $BAG_PID $RVIZ_PID 2>/dev/null || true' EXIT INT TERM
wait $RVIZ_PID
