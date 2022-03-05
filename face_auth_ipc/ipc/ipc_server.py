import os
from multiprocessing.connection import Listener
from multiprocessing.dummy.connection import Connection
from threading import Thread

HOST = os.getenv('FACE_ENCODER_HOST', 'localhost')
PORT = os.getenv('FACE_ENCODER_PORT', 7171)

import dlib
print('dlib.DLIB_USE_CUDA: ', dlib.DLIB_USE_CUDA)
print('Listener: ', HOST + ':'+ str(PORT))
# import dlib.cuda as cuda
# print(cuda.get_num_devices())


import base64
import io

import cv2
import face_recognition
import numpy as np
from PIL import Image


def str_to_pil_image(base64_string):
    imgdata = base64.b64decode(base64_string)
    return Image.open(io.BytesIO(imgdata))


def pil_to_cv2_image(pil_image):
    return cv2.cvtColor(np.array(pil_image), cv2.COLOR_BGR2RGB)


def cv2_img_to_encodings(face):
    face_bounding_boxes = face_recognition.face_locations(face, number_of_times_to_upsample=2, model='cnn')
    if len(face_bounding_boxes) == 1:
        return face_recognition.face_encodings(face, known_face_locations=face_bounding_boxes, model='large', num_jitters=1)[0]
    return None

def handle(connection: Connection):
    try:
        while True:
            image = connection.recv()
            image = pil_to_cv2_image(str_to_pil_image(image))
            encoding = cv2_img_to_encodings(image)
            encoding = encoding.tolist()
            connection.send(encoding)
    except:
        connection.close()


listener = Listener((HOST, PORT))
try:
    while True:
        connection = listener.accept()
        print(listener.last_accepted)
        Thread(target=handle, args=(connection,)).start()
except:
    listener.close()




