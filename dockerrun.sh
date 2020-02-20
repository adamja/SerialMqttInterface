docker run -d \
  --name serialmqttinterface \
  --restart unless-stopped \
  --device=/dev/ttyS0:/dev/ttyS0 \
  -v /home/pi/docker/serialmqttinterface/config:/app \
  --log-opt max-size=10m \
  serialmqttinterface:1.0.0