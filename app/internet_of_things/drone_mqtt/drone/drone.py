import paho.mqtt.client as mqtt
from argparse import ArgumentParser
from datetime import datetime
from time import sleep
from json import dumps

from GPSGenerator import GPSGenerator
from WeatherGenerator import WeatherGenerator


def log(text, debug):
    ''' Print given text if program is run in debug mode

        Parameters:
            text (string) : text to print
            debug (bool)  : program in debug mode     
    '''
    if debug:
        print(text)


def on_connect(client, userdata, flags, rc):
    ''' Callback function when the client receives a CONNACK response from the server
    '''
    print("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("$SYS/#")


def on_message(client, userdata, msg):
    ''' Callback function when a message is received
    '''
    print(msg.topic+" "+str(msg.payload))


def main():
    # Parse arguments
    parser = ArgumentParser(description="Drone script. Connect to the MQTT broker and send position and sensor data")
    parser.add_argument('--ip', help='IP of the MQTT broker', required=True)
    parser.add_argument('--port', help='Port of the MQTT broker', type=int, default=1883)
    parser.add_argument('--freq', help='Update frequency, in milliseconds', type=int, default=1000)
    parser.add_argument('--lat', help='Starting latitude', type=float, default=46.067012)
    parser.add_argument('--lon', help='Starting longitude', type=float, default=11.150448)
    parser.add_argument('--lat_end', help='Target latitude', type=float, default=45.893944)
    parser.add_argument('--lon_end', help='Target longitude', type=float, default=11.043585)
    parser.add_argument('--n_pos', help='Number of sampled positions between start and target positions', 
        type=int, default=20)
    parser.add_argument('--debug', help="Debug mode. Print extra informations", action='store_true')
    args = parser.parse_args()


    ''' ------------------------------------------------------------------------------------
    Connect to the MQTT broker
    '''
    # Try connection
    client = mqtt.Client()
    client.connect(args.ip, args.port, 60)
    
    # Set callback functions
    client.on_connect = on_connect
    client.on_message = on_message

    # Loop function to make the client listen in the background
    client.loop_start()


    ''' ------------------------------------------------------------------------------------
    Build GPS and wheater generators
    '''
    # Create the GPS data generator
    gps_generator = GPSGenerator([args.lat, args.lon], [args.lat_end, args.lon_end], args.n_pos)

    # Create the weather data generator
    weather_generator = WeatherGenerator()


    ''' -------------------------------------------------------------------------------------
    Main simulation loop
    '''
    while True:
        # --------------------------- START MEASURE TIME
        start_t = datetime.now()
        
        # Get GPS and weather info
        target_reached, position_json = gps_generator.next_pos_on_line()
        wind = weather_generator.measure_wind([5,50])
        temperature = weather_generator.measure_temperature([0,30])
        log("Wind speed: {}, Temperature: {}, GPS: {}".format(wind, temperature, position_json), args.debug)

        # Emit message
        client.publish("sensor", dumps({'gps': position_json, 'wind': wind, 'temperature': temperature}))

        # If we reached the target position, exit
        if target_reached:
            break

        end_t = datetime.now()
        # --------------------------- END MEASURE TIME

        # Sleep to match target frequency
        elapsed_time_ms = ((end_t - start_t).microseconds) / 1e3
        if elapsed_time_ms > 0:
            sleep((args.freq - elapsed_time_ms) /1e3)


    # Stop client listening loop
    client.loop_stop()
    client.disconnect()


if __name__ == '__main__':
    main()