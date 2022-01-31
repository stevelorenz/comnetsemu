import paho.mqtt.client as mqtt
import random
import time
import _thread as thread
import socket
from json import dumps

# This MQTT client represents a drone with the following ID.
id = socket.gethostname()

# This MQTT client has the following topics:
# - "log": to publish debug logs;
# - "positions": to publish updates on position;
# - "command_" + id: to subscribe to receive commands from the server.
topic_log = "log"
topic_positions = "positions"
topic_server_commands = "command_" + id
topic_current_position = "current_position"

# GPS coordinate boundaries for Trento
maxLat = 46.096244200191684
minLat = 46.040603518369856
maxLon = 11.139450300806237
minLon = 11.108262519974287

# The speed "0.00002384598" correspond to around 3m/s (~10km/h), but it is way too slow for testing.
# Therefore, the speed is "0.00102384598" (around 130m/s)
droneSpeed = 0.00102384598 

# The current position and the position to reach (given from the server).
posCurrent = [0, 0]


# The callback for when a PUBLISH message is received from the server.
# As this client is subscribed to his command topic only, simply launch
# a new thread to allow the drone to reach the new position.
def on_message(client, userdata, msg):
    print("RECEIVED MESSAGE " + str(msg.topic))
    if msg.topic == topic_current_position:
    	thread.start_new_thread( send_cur_position, () )
    else:
    	thread.start_new_thread( reach_new_position, (str(msg.payload), ) )

def send_cur_position():	
	client.publish(topic_positions, dumps({"id": id, "latitude": posCurrent[0], "longitude": posCurrent[1]}))
	
# Move from the current position to the given one.
def reach_new_position(msg):
    global posCurrent
    posToReach = get_position_from_message(msg)
    client.publish(topic_log, (id + ": new position to reach is latitude " + str(posToReach[0]) + ", longitude " + str(posToReach[1])))

    while (posCurrent[0] != posToReach[0] or posCurrent[1] != posToReach[1]):
        for i in range(0, 2):
            if (posCurrent[i] == posToReach[i]):
                latlon = ""
                if (i==0): 
                    latlon = "latitude" 
                else:
                    latlon = "longitude"
                client.publish(topic_log, (id + ": position for " + latlon + " reached"))
            elif (abs(posCurrent[i] - posToReach[i]) < droneSpeed):
                posCurrent[i] = posToReach[i]
            elif (posCurrent[i] < posToReach[i]):
                posCurrent[i] = posCurrent[i] + droneSpeed
            elif (posCurrent[i] > posToReach[i]):
                posCurrent[i] = posCurrent[i] - droneSpeed
            else:
                client.publish(topic_log, (id + ": error, should not be here"))
            #client.publish(topic_positions, dumps({"id": id, "latitude": posCurrent[0], "longitude": posCurrent[1]}))
        time.sleep(1)

    client.publish("destination_reached", (id + " has reached the new destination!"))        

# Generate a random position in Trento.
def generate_starting_position():
    posCurrent = [(random.random()%(maxLat - minLat) + minLat), (random.random()%(maxLon - minLon) + minLon)]
    client.publish(topic_log, (id + ": generated starting position, latitude " + str(posCurrent[0]) + ", longitude " + str(posCurrent[1])))
    return posCurrent

# Generate a message to publish from a position.
def get_message_from_position(pos):
    return id + "_" + str(pos[0]) + "_" + str(pos[1])

# Get a position from a message.
def get_position_from_message(msg):
    msgSplit = msg.split("_")
    return [float(msgSplit[1]), float(msgSplit[2])]



# Create the MQTT client and define callbacks for connection and messages.
client = mqtt.Client(id)
client.on_message = on_message

# Blocking call to connect to the broker.
# The arguments are the hostname/IP, port, keepalive and bind_address (optional, here omitted)
client.connect("10.0.0.7", 1883, 60)

# Generate the starting position and publish it.
posCurrent = generate_starting_position()
client.publish(topic_positions, get_message_from_position(posCurrent))

# Subscribe to the command server
client.subscribe(topic_server_commands)
client.subscribe(topic_current_position)


# Blocking call that processes network traffic, dispatches callbacks and handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a manual interface.
client.loop_forever()
