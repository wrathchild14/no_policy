from flask import Flask, request, jsonify
import threading
from PIL import Image
import queue
from road_cam.roadcam import RoadCam
app = Flask(__name__)
DETECTIONS = queue.Queue() 
blob_path = './road_cam/blobconverter/mobilenet-ssd_openvino_2021.4_6shave.blob'

# def run_road_cam():
#       # Path to the blob file
#     road_cam = RoadCam(blob_path)  # Initialize RoadCam with the appropriate blob path
#     road_cam.setup_pipeline()
#     road_cam.run(demo=False)

@app.route('/detections')
def detections():
    global DETECTIONS
    # detections = []
   
    print(DETECTIONS.get())
    return jsonify(DETECTIONS.get())
        # detections.append(latest_detections.get())
    # return jsonify(detections)



def run_road_cam(road_cam):
    # road_cam = RoadCam(blob_path, detections_queue)  # Pass the shared queue to RoadCam
    # road_cam.setup_pipeline()
    road_cam.run(demo=True)

if __name__ == '__main__':
    roadcam = RoadCam(blob_path, detections_queue=DETECTIONS)
    roadcam.setup_pipeline()
    cam_thread = threading.Thread(target=run_road_cam, args=(roadcam,))
    cam_thread.daemon = True
    cam_thread.start()
    app.run(debug=True)  # Flask app runs in main thread

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    
    file = request.files['image']
    
    # Check if the file is an image
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file:
        try:
            # Open the image using Pillow
            image = Image.open(file)
            return jsonify({'image size': image.size}), 200
        
        except Exception as e:
            return jsonify({'error': f'Error processing image: {str(e)}'}), 500





if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
