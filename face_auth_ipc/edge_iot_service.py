import threading
import time
from time import sleep

import cv2
import dlib
import face_recognition

from face_auth_ipc import mqtt_consumer
from face_auth_ipc.utils import is_cam_aligned, find_valid_encoding_identity, allow_admission, \
    get_iotdev_id

print('dlib.DLIB_USE_CUDA: ', dlib.DLIB_USE_CUDA)


def frame_face_coords(frame):
    face_bounding_boxes = face_recognition.face_locations(frame, model='cnn')
    if len(face_bounding_boxes) >= 1:
        return face_bounding_boxes[0]
    return None


def frame_face_shift(frame, face_coords):
    if not face_coords:
        return 0, 0
    cx_frame = frame.shape[1] / 2
    cy_frame = frame.shape[0] / 2
    cy_face = face_coords[2] + (face_coords[0] - face_coords[2]) / 2
    cx_face = face_coords[3] + abs((face_coords[3] - face_coords[1])) / 2
    return cx_frame - cx_face, cy_frame - cy_face


def encode_face(frame, face_coords):
    if not face_coords:
        return None
    face = frame[face_coords[0]:face_coords[2], face_coords[3]:face_coords[1]]
    return \
        face_recognition.face_encodings(face, known_face_locations=[(0, face.shape[1], face.shape[0], 0)],
                                        model='large',
                                        num_jitters=1)[0]


def process_frame(frame):
    t = time.time()
    face_coords = frame_face_coords(frame)
    dx, dy = frame_face_shift(frame, face_coords)
    if is_cam_aligned(dx, dy):
        identity = find_valid_encoding_identity(encode_face(frame, face_coords))
        if identity:
            allow_admission(identity)
    print(time.time()-t)

enabled_lock = threading.Lock()


def loop():
    cap = cv2.VideoCapture(-1)
    client = mqtt_consumer.connect_mqtt()
    mqtt_consumer.subscribe(client, lock=enabled_lock, id=get_iotdev_id())
    threading.Thread(target=client.loop_forever).start()
    while True:
        try:
            enabled_lock.acquire(blocking=True)
        except:
            pass
        ret, frame = cap.read()
        #frame = cv2.imread('/home/developer/PycharmProjects/face_recognition/face_auth/faces/tomholand/1.jpg')
        if ret:
            process_frame(frame)
        try:
            enabled_lock.release()
        except:
            pass
        sleep(0.04)


if __name__ == '__main__':
    loop()
