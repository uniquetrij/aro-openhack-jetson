import json
import os
import time
import uuid
import logging

import cv2
import numpy as np
import redis

import pickle

import face_recognition
from kafka import KafkaProducer

REDIS_PORT = os.getenv('REDIS_PORT', 6379)
REDIS_SERVER = os.getenv('REDIS_SERVER', 'localhost')

BOOTSTRAP_SERVERS = os.getenv('KAFKA_BS_URL',
                              'kf-cluster-kafka-bootstrap-loremipsum.apps.i0xha38k.eastus.aroapp.io:443')
ADMISSION_TOPIC = os.getenv('KAFKA_TOPIC_ADMISSION',
                            'test')
KAFKA_PRODUCER = KafkaProducer(bootstrap_servers=BOOTSTRAP_SERVERS, ssl_cafile='./ca.crt', security_protocol="SSL")


def allow_admission(identity):
    def on_success(record_metadata, msg):
        print(record_metadata)
        print(msg)

    def on_error(exerr, message):
        print(exerr)
        print(message)

    message = {
        'type': 'allow_admission',
        'utc_time': time.time(),
        'utc_offset': time.timezone,
        'data': {
            'identity': identity,
            'body_temp': read_body_temp(),
        },
        'device_mac': get_iotdev_id()
    }
    KAFKA_PRODUCER.send(ADMISSION_TOPIC, json.dumps(message).encode('utf-8')) \
        .add_callback(on_success, message=message) \
        .add_errback(on_error, message=message)


def get_iotdev_id():
    return (':'.join(
        ['{:02x}'.format((uuid.getnode() >> elements) & 0xff)
         for elements in range(0, 2 * 6, 2)][::-1]
    ))


def get_encodings():
    redis_cache = redis.Redis(host=REDIS_SERVER, port=REDIS_PORT)
    keys = []
    encs = []
    for k in redis_cache.scan_iter("enc_*"):
        entry = pickle.loads(redis_cache.get(k))
        for e in entry:
            if isinstance(k, bytes):
                k = k.decode()
            keys.append(k)
            encs.append(e)
    return keys, encs


def find_valid_encoding_identity(encoding):
    if encoding is None:
        return None
    keys, encs = get_encodings()
    matches = face_recognition.compare_faces(encs, encoding)
    matches = set([x for x, y in zip(keys, matches) if y])
    if len(matches) == 1:
        return matches.pop()
    return None


def is_cam_aligned(dx, dy):
    return True


def read_body_temp():
    return 97.6
