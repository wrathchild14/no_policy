from flask import Flask, request, jsonify
import numpy as np
import queue
import threading

from drowsiness_detection.detect import *
from road_cam.roadcam import RoadCam

app = Flask(__name__)

drowsy_data = []
DROWSY_THRESHOLD = 3
DETECTIONS = queue.Queue()
blob_path = 'road_cam/blobconverter/mobilenet-ssd_openvino_2021.4_6shave.blob'

detect = dlib.get_frontal_face_detector()
predict = dlib.shape_predictor("drowsiness_detection/shape_predictor_68_face_landmarks.dat")

(lStart, lEnd) = face_utils.FACIAL_LANDMARKS_IDXS["left_eye"]
(rStart, rEnd) = face_utils.FACIAL_LANDMARKS_IDXS["right_eye"]
result = None


@app.route('/detections')
def detections():
    global DETECTIONS
    # detections = []

    # print("FLASK:", DETECTIONS)
    # print(DETECTIONS.get())
    return jsonify(DETECTIONS.get())
        # detections.append(latest_detections.get())
    # return jsonify(detections)



def run_road_cam(road_cam):
    # road_cam = RoadCam(blob_path, detections_queue)  # Pass the shared queue to RoadCam
    # road_cam.setup_pipeline()
    road_cam.run(demo=False)


@app.route('/upload', methods=['POST'])
def upload_file():
    
    # Variables for Drowsiness Detection
    global drowsy_data, DROWSY_THRESHOLD
    global detect, predict, lStart, lEnd, rStart, rEnd
    global result

    try:
        byte_array = request.get_data()

        image_np = np.frombuffer(byte_array, dtype=np.uint8)
        image = cv2.imdecode(image_np, cv2.IMREAD_COLOR)
        image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)

        drowsy_data.append(image)
        if len(drowsy_data) > DROWSY_THRESHOLD:
            result = drowsy_system(drowsy_data, detect, predict, lStart, lEnd, rStart, rEnd)
            drowsy_data = []

        if result is not None:
            return jsonify({'signal': result}), 200
        else:
            return jsonify({'signal': -1, 'message': 'Not enough data for detection'}), 200

    except Exception as e:
        # Handle any errors that occur during image processing
        return jsonify({'error': f'Error processing image: {str(e)}'}), 500



if __name__ == '__main__':
    
    roadcam = RoadCam(blob_path, detections_queue=DETECTIONS)
    roadcam.setup_pipeline()
    cam_thread = threading.Thread(target=run_road_cam, args=(roadcam,))
    cam_thread.daemon = True
    cam_thread.start()
    app.run(debug=True, host='0.0.0.0', port=5000)  # Flask app runs in main thread
