#!/bin/sh
# Assemble main.js from the source parts (order matters).
cd "$(dirname "$0")/src" && cat g_head.js g_airport.js g_landmark.js part_poses.js g_radar.js g_tail.js part_light.js part_hud.js g_frame.js > ../main.js
