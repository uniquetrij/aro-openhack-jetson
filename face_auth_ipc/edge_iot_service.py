import threading
import threading
import time
from time import sleep

import cv2
import dlib
import face_recognition
import jetson.inference
import jetson.utils

from face_auth_ipc import edge_iot_status_mqtt
from face_auth_ipc.utils import is_cam_aligned, find_valid_encoding_identity, allow_admission, \
    get_iotdev_id, read_body_temp

print('dlib.DLIB_USE_CUDA: ', str(dlib.DLIB_USE_CUDA))

MULTI_DETECT_THRESHOLD = 5

# def frame_face_coords(frame):
#     face_bounding_boxes = face_recognition.face_locations(frame, model='cnn')
#     if len(face_bounding_boxes) >= 1:
#         return face_bounding_boxes[0]
#     return None

face_model = jetson.inference.detectNet("facenet-120", threshold=0.05)
camera = jetson.utils.videoSource("/dev/video0")
display = jetson.utils.videoOutput("rtp://192.168.1.12:1234", "--headless")


def frame_face_coords(frame):
    detections = face_model.Detect(frame)
    if len(detections) >= 1:
        t = int(detections[0].Top)
        r = int(detections[0].Right)
        b = int(detections[0].Bottom)
        l = int(detections[0].Left)
        return (t, r, b, l)
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


def find_face(frame):
    ringbuffer = jetson.utils.cudaAllocMapped(width=frame.width, height=frame.height, format=frame.format)
    jetson.utils.cudaConvertColor(frame, ringbuffer)
    image = cv2.cvtColor(jetson.utils.cudaToNumpy(ringbuffer), cv2.COLOR_BGR2RGB)
    display.Render(frame)
    face_coords = frame_face_coords(frame)
    return image, face_coords


LAST_TIME = 0


def process_frame(frame):
    global LAST_TIME
    t = time.time()
    image, face_coords = find_face(frame)
    print('face coordinates detected: ', face_coords)
    if face_coords is None:
        return
    # print('face coordinates found', face_coords)
    dx, dy = frame_face_shift(image, face_coords)
    print('face shift calculated: ', (dx,dy))
    if is_cam_aligned(dx, dy):
        print('camera alignment done')
        CURR_TIME = time.time()
        if CURR_TIME - LAST_TIME < MULTI_DETECT_THRESHOLD:
            print('detection too frequent, ignoring')
            return
        LAST_TIME = CURR_TIME
        identity_score = find_valid_encoding_identity(encode_face(image, face_coords))
        print('identity score: ', identity_score)
        if identity_score is None:
            return
        identity, score = identity_score
        face_identified, body_temp, allowed = None, None, None
        if score < 0.6:
            face_identified = True
            body_temp = read_body_temp()
            print('body temperature reading:', body_temp)
            if body_temp < 99:
                allowed = True
            else:
                allowed = False
        else:
            face_identified = False

        allow_admission(identity, score, body_temp, face_identified, allowed)

    # print('frame processing time', time.time() - t)


enabled_lock = threading.Lock()


def loop():
    # cap = cv2.VideoCapture(-1)
    client = edge_iot_status_mqtt.connect_mqtt()
    edge_iot_status_mqtt.subscribe(client, lock=enabled_lock, id=get_iotdev_id())
    threading.Thread(target=client.loop_forever).start()
    while True:
        # print('main loop')
        try:
            enabled_lock.acquire(blocking=True)
        except:
            pass
        # ret, frame = cap.read()
        frame = camera.Capture()
        process_frame(frame)

        try:
            enabled_lock.release()
        except:
            pass
        sleep(0.04)


if __name__ == '__main__':
    loop()
