import logging
from include.config import Config
from include.command import Command
import serial
from time import sleep
import paho.mqtt.client as mqtt
import queue


# Logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s:%(name)s:%(levelname)s:%(message)s')
file_handler = logging.FileHandler('debug.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
stream_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# Config
config = Config(config_file_name='config.yaml', logger=logger)

# Queue
serial_command_queue = queue.Queue(maxsize=100)
mqtt_command_queue = queue.Queue(maxsize=100)

port = None  # Serial port
mqttc = None  # MQTT client


def log(msg, level=logging.INFO):
    logger.log(level, msg)


def serial_read():
    rv = ''
    while True:
        try:
            b = port.read()  # Read byte from serial port
            ch = b.decode('utf-8')  # Convert byte to character
        except serial.SerialException as e:
            # There is no new data from serial port
            return None
        except TypeError as e:
            # Disconnect of USB->UART occured
            port.close()
            return None

        if not b:
            break

        log('[SERIAL] Character received: ' + str(b), level=logging.DEBUG)
        rv += ch

    return rv


def process_serial_data(data):
    STX = config.get('serial_STX')
    ETX = config.get('serial_ETX')

    if not data:
        return False
    if not len(data) > 0:
        return False

    start = False
    command = ''
    for c in data:
        if start:
            if c == chr(ETX):  # End of command - ETX
                serial_command_queue.put(command)
                log('[SERIAL] Received command: ' + command)
                command = ''
                start = False
            else:
                command += c

        if c == chr(STX):  # Start of command - STX
            start = True


def command_loop():
    command = serial_command_queue.queue[0]
    mqttc.publish(config.get('mqtt_publish_channel'), command, 0)
    log('[MQTT] Sent command: {} to channel {}'.format(command, config.get('mqtt_publish_channel')))
    pass


def send_to_serial(msg):
    STX = config.get('serial_STX')
    ETX = config.get('serial_ETX')
    msg = (chr(STX) + msg + chr(ETX)).encode('utf-8')  # Add STX and RTX to the message before sending to serial
    port.write(msg)
    log('[SERIAL] Sending command: {}'.format(msg))


def receive_from_serial():
    data = serial_read()
    process_serial_data(data)


def connect_serial():
    # Setup serial port connection
    global port
    while True:
        try:
            log('[SERIAL] Attempting to connect to serial port {}'.format(config.get('serial_port')))
            port = serial.Serial(config.get('serial_port'),
                                 baudrate=config.get('serial_baud'),
                                 timeout=config.get('serial_timeout'))
            break
        except serial.SerialException as e:
            log(e)
            log('[SERIAL] Error creating a serial connection. Trying again in 15 seconds')
            sleep(15)
    log('[SERIAL] Connected')


def on_connect(client, userdata, flags, rc):
    log('[MQTT] Connected')
    log('[MQTT] Connected with result code ' + str(rc))
    log('[MQTT] Attempting to subscribe to channel ' + config.get('mqtt_publish_channel'))
    mqttc.subscribe(config.get('mqtt_subscribe_channel'), 0)


def on_subscribe(client, userdata, mid, granted_qos):
    log('[MQTT] Successfully subscribed to ' + config.get('mqtt_subscribe_channel'))


def on_message(client, userdata, msg):
    payload = msg.payload.decode('utf-8')
    log('[MQTT] Received command: {} from channel {}'.format(payload, msg.topic))

    if len(payload) > 0:
        max_retry_attempts = config.get('max_retry_attempts')
        wait_time_seconds = config.get('wait_time_seconds')
        mqtt_command_queue.put(Command(payload, max_retry_attempts, wait_time_seconds, logger=logger))


def connect_mqtt():
    # Setup MQTT connection - if the broker connection is lost the mqtt package will automatically
    # attempt to reconnect when it is made available again
    global mqttc
    global config
    mqttc = mqtt.Client()
    mqttc.enable_logger(logger=logger)
    mqttc.on_connect = on_connect
    mqttc.on_message = on_message
    mqttc.on_subscribe = on_subscribe
    while True:
        try:
            log('[MQTT] Attempting to connect to broker on {}:{}'.format(config.get('mqtt_ip'), config.get('mqtt_port')))
            mqttc.connect(config.get('mqtt_ip'), config.get('mqtt_port'), config.get('mqtt_timeout'))
            mqttc.loop_start()
            break
        except Exception as e:
            logger.exception(e)
            log('[MQTT] Failed to create a connection. Trying again in 5 seconds...')
            sleep(5)


def main():
    config.load_config_file()
    connect_mqtt()
    connect_serial()

    # Main loop
    while True:
        try:
            receive_from_serial()
            while not serial_command_queue.empty():
                serial_command = serial_command_queue.get()

                if not mqtt_command_queue.empty():
                    mqtt_command = mqtt_command_queue.queue[0]
                    if mqtt_command.success_message(serial_command):
                        mqtt_command_queue.get()  # remove command from the queue
                    if mqtt_command.invalid_message(serial_command):
                        mqtt_command_queue.get()  # remove command from the queue

                mqttc.publish(config.get('mqtt_publish_channel'), serial_command, 0)
                log('[MQTT] Sent command: {} to channel {}'.format(serial_command, config.get('mqtt_publish_channel')))

            if not mqtt_command_queue.empty():
                command = mqtt_command_queue.queue[0]
                if command.attempts_maxed():
                    mqtt_command_queue.get()  # Dropping command, attempts have been maxed
                    mqttc.publish(config.get('mqtt_publish_channel'), 'TIMEOUT', 0)
                elif command.ready_to_send():
                    send_to_serial(command.send_message())
                    log('[SERIAL] Sent command: {}'.format(command.message))

        except serial.serialutil.SerialException as e:
            logger.exception(e)
            port.close()
            connect_serial()
        except Exception as e:
            logger.exception(e)

        sleep(0.1)


if __name__ == '__main__':
    log('App starting...')
    main()
