import json
import os
import random
import threading

import requests
from paho.mqtt import client as mqtt_client

STATUS_CONFIG_URL = os.getenv('STATUS_CONFIG_URL', 'http://quarkus-backend-loremipsum.apps.i0xha38k.eastus.aroapp.io/api/configuration/')

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
    # url = STATUS_CONFIG_URL + requests.utils.quote(id)
    # print(url)
    # try:
    #     response = requests.get(url).json()
    #     print(json.dumps(response, indent=1))
    #     return response['enabled']
    # except Exception as e:
    #     print(e)
    #     return False
    return True


def subscribe(client: mqtt_client, lock: threading.Lock, id):
    def on_message(client, userdata, msg):
        temp = json.loads(msg.payload.decode())

        #HERE IS A BIG BUG!!!

        print(temp["enabled"])
        print(temp["deviceIdentifier"])
        print({temp["deviceIdentifier"]: temp["enabled"]}[id])
        if {temp["deviceIdentifier"]: temp["enabled"]}[id]:
            try:
                lock.release()
                print("DEVICE ENABLED BY MQTT")
            except:
                pass
        else:
            try:
                lock.acquire(blocking=True)
                print("DEVICE DISABLED BY MQTT")
            except:
                pass

    if is_iotdev_enabled(id):
        try:
            lock.release()
            print("DEVICE ENABLED BY STATUS")
        except:
            pass
    else:
        try:
            lock.acquire(blocking=True)
            print("DEVICE DISABLED BY STATUS")
        except:
            pass

    client.subscribe(topic)
    client.on_message = on_message


if __name__ == '__main__':
    print(is_iotdev_enabled('7b:ed:b4:d3:4d:34'))
