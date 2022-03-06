import threading
import time
from time import sleep
import jetson.inference
import jetson.utils
import cv2
import dlib
import face_recognition

from face_auth_ipc import mqtt_consumer
from face_auth_ipc.utils import is_cam_aligned, find_valid_encoding_identity, allow_admission, \
    get_iotdev_id

print('dlib.DLIB_USE_CUDA: ', dlib.DLIB_USE_CUDA)

# def frame_face_coords(frame):
#     face_bounding_boxes = face_recognition.face_locations(frame, model='cnn')
#     if len(face_bounding_boxes) >= 1:
#         return face_bounding_boxes[0]
#     return None

face_model = jetson.inference.detectNet("facenet-120", threshold=0.05)
camera = jetson.utils.videoSource("test.mp4")#("/dev/video0")
display = jetson.utils.videoOutput("rtp://192.168.12.33:1234", "--headless")


def frame_face_coords(frame):
    print("frame_face_coords")
    detections = face_model.Detect(frame)
    print(detections)
    if len(detections) >= 1:
        t = int(detections[0].Top)
        r = int(detections[0].Right)
        b = int(detections[0].Bottom)
        l = int(detections[0].Left)
        print((t, r, b, l))
        return (t, r, b, l)
    return None

    # face_bounding_boxes = face_recognition.face_locations(frame, model='cnn')
    # if len(face_bounding_boxes) >= 1:
    #     return face_bounding_boxes[0]
    # return None


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


def process_frame(frame):
    t = time.time()
    image, face_coords = find_face(frame)
    print(face_coords)
    dx, dy = frame_face_shift(image, face_coords)
    if is_cam_aligned(dx, dy):
        identity = find_valid_encoding_identity(encode_face(image, face_coords))
        if identity:
            allow_admission(identity)
    print(time.time() - t)


enabled_lock = threading.Lock()


def loop():
    # cap = cv2.VideoCapture(-1)
    client = mqtt_consumer.connect_mqtt()
    mqtt_consumer.subscribe(client, lock=enabled_lock, id=get_iotdev_id())
    threading.Thread(target=client.loop_forever).start()
    while True:
        print('In Loop...')
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


if __name__ == '__main__':
    loop()
