from pathlib import Path
import sys
import cv2
import depthai as dai
import numpy as np
import time 
import queue

labelMap = ["background", "aeroplane", "bicycle", "bird", "boat", "bottle", "bus", "car", "cat", "chair", "cow",
            "diningtable", "dog", "horse", "motorbike", "person", "pottedplant", "sheep", "sofa", "train", "tvmonitor"]

ROAD_OBJECTS = {'person', 'car', 'bus', 'truck', 'motorbike', 'bicycle', 'cat', 'dog', 'horse', 'train'}

label_to_id = {i: labelMap[i] for i in range(len(labelMap))}
id_to_label = {labelMap[i]: i for i in range(len(labelMap))}

class RoadCamVideo:

    def __init__(self, blob_path, detections_queue, video_path) -> None:
        self.blob_path = blob_path
        self.sync_nn = True
        self.detectons_queue = detections_queue
        self.video_path = video_path
        # self.color_video = video_folder + '/color.h264'
        # self.left_video = video_folder + '/left.h264'
        # self.right_video = video_folder + '/right.h264'


    def display_frame(self, name, frame, detections):
        for detection in detections:
            bbox = self.frame_norm(frame, (detection.xmin, detection.ymin, detection.xmax, detection.ymax))
            cv2.putText(frame, labelMap[detection.label], (bbox[0] + 10, bbox[1] + 20), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
            cv2.putText(frame, f"{int(detection.confidence * 100)}%", (bbox[0] + 10, bbox[1] + 40), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
            cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (255, 0, 0), 2)
        # Show the frame
        cv2.imshow(name, frame)

    def setup_pipeline(self):
        self.pipeline = dai.Pipeline()

        # self.camRgb = self.pipeline.create(dai.node.ColorCamera)
        self.detectionNetwork = self.pipeline.create(dai.node.MobileNetDetectionNetwork)
        self.xinFrame = self.pipeline.create(dai.node.XLinkIn)
        self.nnOut = self.pipeline.create(dai.node.XLinkOut)
        
        self.xinFrame.setStreamName("inFrame")
        self.nnOut.setStreamName("nn")
        
        self.detectionNetwork.setConfidenceThreshold(0.5)
        self.detectionNetwork.setBlobPath(self.blob_path)
        self.detectionNetwork.setNumInferenceThreads(2)
        self.detectionNetwork.input.setBlocking(False)

        self.xinFrame.out.link(self.detectionNetwork.input)
        self.detectionNetwork.out.link(self.nnOut.input)
       
    # def 
    def frame_norm(self, frame, bbox):
        normVals = np.full(len(bbox), frame.shape[0])
        normVals[::2] = frame.shape[1]
        return (np.clip(np.array(bbox), 0, 1) * normVals).astype(int)

    def to_planar(self, arr: np.ndarray, shape: tuple) -> np.ndarray:
        return cv2.resize(arr, shape).transpose(2, 0, 1).flatten()
    
    def display_frame(self, name, frame, detections):
        for detection in detections:
            bbox = self.frame_norm(frame, (detection.xmin, detection.ymin, detection.xmax, detection.ymax))
            cv2.putText(frame, labelMap[detection.label], (bbox[0] + 10, bbox[1] + 20), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
            cv2.putText(frame, f"{int(detection.confidence * 100)}%", (bbox[0] + 10, bbox[1] + 40), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
            cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (255, 0, 0), 2)
        # Show the frame
        cv2.imshow(name, frame)

    def run(self, demo=False):
        with dai.Device(self.pipeline) as pipeline:
            # Output queues will be used to get the rgb frames and nn data from the outputs defined above
            # qDet = pipeline.getOutputQueue(name="nn", maxSize=4, blocking=False)   
            qIn = pipeline.getInputQueue(name="inFrame")
            qDet = pipeline.getOutputQueue(name="nn", maxSize=4, blocking=False)
            detections = []
            frame = None

            cap = cv2.VideoCapture(self.video_path)
            while cap.isOpened():
                read_correctly, frame = cap.read()
                if not read_correctly:
                    break

                img = dai.ImgFrame()
                img.setData(self.to_planar(frame, (300, 300)))
                img.setTimestamp(time.monotonic())
                img.setWidth(300)
                img.setHeight(300)
                qIn.send(img)

                inDet = qDet.tryGet()
                
                if inDet is not None:
                    detections = inDet.detections
                if frame is not None:
                    # frame_detections = []
                    self.display_frame("preview", frame, detections)
                if cv2.waitKey(1) == ord('q'):
                    break    




if __name__ == "__main__":
    blob_path = './blobconverter/mobilenet-ssd_openvino_2021.4_6shave.blob'
    video_path = '../color.mp4'
    detections_queue = queue.Queue()
    road_cam = RoadCamVideo(blob_path, detections_queue=detections_queue, video_path=video_path)

    road_cam.setup_pipeline()
    road_cam.run(demo=True)
    cv2.destroyAllWindows()    
    sys.exit(0)
