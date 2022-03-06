import json
import random
import threading

import requests
from paho.mqtt import client as mqtt_client

broker = 'puffin.rmq2.cloudamqp.com'
port = 1883
topic = "configuration-device"
# generate client ID with pub prefix randomly
client_id = f'python-mqtt-{random.randint(0, 100)}'
username = 'prminpda:prminpda'
password = 'WCN11mfCwwxNX1TQ2ys8cAPl3_damTVN'


def connect_mqtt() -> mqtt_client:
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)

    client = mqtt_client.Client(client_id)
    client.username_pw_set(username, password)
    client.on_connect = on_connect
    client.connect(broker, port)
    return client


def is_iotdev_enabled(id: str):
    # url = "http://quarkus-backend-loremipsum.apps.i0xha38k.eastus.aroapp.io/api/configuration/" + requests.utils.quote(id)
    # try:
    #     return requests.get(url).json()['enabled']
    # except:
    #     return False
    return True


def subscribe(client: mqtt_client, lock: threading.Lock, id, requests=None):
    def on_message(client, userdata, msg):
        temp = json.loads(msg.payload.decode())
        print(temp["enabled"])
        print(temp["deviceIdentifier"])
        print({temp["deviceIdentifier"]: temp["enabled"]}[id])
        if {temp["deviceIdentifier"]: temp["enabled"]}[id]:
            try:
                lock.release()
                print("DEVICE ENABLED")
            except:
                pass
        else:
            try:
                lock.acquire(blocking=True)
                print("DEVICE DISABLED")
            except:
                pass

    if is_iotdev_enabled(id):
        try:
            lock.release()
            print("DEVICE ENABLED")
        except:
            pass
    else:
        try:
            lock.acquire(blocking=True)
            print("DEVICE DISABLED")
        except:
            pass

    client.subscribe(topic)
    client.on_message = on_message


if __name__ == '__main__':
    is_iotdev_enabled('7b:ed:b4:d3:4d:34')
