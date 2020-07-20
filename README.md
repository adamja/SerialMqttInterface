# SerialMqttInterface

This project was designed to utilise the serial port of a raspberry pi and pass commands received from an mqtt broker through to the serial device.

#### COMMAND UPDATES
-> listen to mqtt broker for command<br>
-> pass command through to serial device<br>
-> serial device replies that command is received<br>
-> pass received acknowledgement to mqtt broker<br>

#### STATUS UPDATES
-> serial device will update status changes<br>
-> pass changes through to mqtt broker<br>
