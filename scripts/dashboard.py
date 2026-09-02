#!/bin/bash
while true; do
  echo "<h1>Healthcare Lab</h1><p>$(uptime)</p><pre>$(ls -lh /backup/database/ | tail)<br>$(sudo monit summary)</pre><iframe src=http://localhost:19999 width=100% height=400></iframe>"
  sleep 30
done | nc -l 5000
