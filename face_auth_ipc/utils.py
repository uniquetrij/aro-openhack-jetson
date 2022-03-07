import json
import os
import threading
import time
import uuid

import face_recognition
import numpy as np
import redis
from kafka import KafkaProducer

from face_auth_ipc import drive, communication as serial
from face_auth_ipc.communication import master, serial_connect
threading.Thread(target=serial.serial_connect, args=('/dev/ttyACM0',)).start()


REDIS_PORT = os.getenv('REDIS_PORT', 6379)
REDIS_SERVER = os.getenv('REDIS_SERVER', 'localhost')

BOOTSTRAP_SERVERS = os.getenv('KAFKA_BS_URL',
                              'kf-cluster-kafka-bootstrap-loremipsum.apps.i0xha38k.eastus.aroapp.io:443')
ADMISSION_TOPIC = os.getenv('KAFKA_TOPIC_ADMISSION',
                            'topic-attendance-iot')
KAFKA_PRODUCER = KafkaProducer(bootstrap_servers=BOOTSTRAP_SERVERS, ssl_cafile='./resources/ca.crt',
                               security_protocol="SSL")


def allow_admission(identity, score, body_temp, face_identified, allowed):
    def on_success(record_metadata, message, kfq_id):
        print(record_metadata)
        print(message)
        os.remove('kfqueue/' + kfq_id)

    def on_error(exerr, message, kfq_id):
        print(exerr)
        print(message)

    if allowed:
        open_turnstile()

    message = {
        "authenticated": allowed,  # allowed or disallowed
        "deviceIdentifier": get_iotdev_id(),
        "identifier": identity,
        "faceIdentified": face_identified,
        "temperature": body_temp,
        "score": score,
        'createdAt': time.time(),
        'utc_offset': time.timezone,
    }
    message = json.dumps(message).encode('utf-8')
    kfq_id = str(uuid.uuid4())
    kfqueue_write(kfq_id, message)
    KAFKA_PRODUCER.send(ADMISSION_TOPIC, message) \
        .add_callback(on_success, message=message, kfq_id=kfq_id) \
        .add_errback(on_error, message=message, kfq_id=kfq_id)


def kfqueue_update():
    def on_success(record_metadata, message, kfq_id):
        print(record_metadata)
        print(message)
        os.remove('kfqueue/' + kfq_id)

    def on_error(exerr, message, kfq_id):
        print(exerr)
        print(message)

    for kfq_id in os.listdir('kfqueue'):
        message = open('kfqueue/' + kfq_id, "r").readline().encode('utf-8')
        KAFKA_PRODUCER.send(ADMISSION_TOPIC, message) \
            .add_callback(on_success, message=message, kfq_id=kfq_id) \
            .add_errback(on_error, message=message, kfq_id=kfq_id)


def kfqueue_write(kfq_id, message):
    with open('./kfqueue/' + kfq_id, 'w') as f:
        f.write(message.decode())


def get_iotdev_id():
    # return (':'.join(
    #     ['{:02x}'.format((uuid.getnode() >> elements) & 0xff)
    #      for elements in range(0, 2 * 6, 2)][::-1]
    # ))
    return '7b:ed:b4:d3:4d:34'


def get_encodings():
    print('reading redis cache')
    redis_cache = redis.Redis(host=REDIS_SERVER, port=REDIS_PORT)
    keys = []
    encs = []
    for k in redis_cache.scan_iter("*"):
        entry = [json.loads(redis_cache.get(k))]
        print('entry found:', entry)
        for e in entry:
            if isinstance(k, bytes):
                k = k.decode()
            keys.append(k)
            encs.append(e)
    return keys, encs


def find_valid_encoding_identity(encoding):
    print("face encoding:", encoding)
    if encoding is None:
        return None
    keys, encs = get_encodings()
    print('existing keys:', keys)

    scores = list(face_recognition.face_distance(encs, encoding))
    print('distance scores:', scores)
    if len(scores) >= 1:
        score = min(scores)
        index = scores.index(score)
        return keys[index], score

    return None


def is_cam_aligned(dx, dy):
    dx, dy = -dx, -dy
    # print('deciding alignment requirement')
    if (abs(dy) > 10 or abs(dy) > 10):
        panval = np.interp(abs(dx), [0, 640], [0, 75])
        tiltval = np.interp(abs(dy), [0, 360], [0, 60])
        if dx < 0:
            panval = -1 * panval
        if dy < 0:
            tiltval = -1 * tiltval
        # print('actuating pan-tilt', (panval, tiltval))
        drive.panVal = panval
        drive.tiltVal = tiltval
        return False
    else:
        return True


def open_turnstile():
    print("turnstile opened")
    return True


def read_body_temp():
    return round(float(os.read(serial.serial_read('/dev/ttyACM0'), 1000).decode('utf-8').split(';')[0]), 1)
#
threading.Timer(5, kfqueue_update).start()


if __name__ == '__main__':
    allow_admission("103", 0.3, 97, False, False)
    # print(get_encodings())
