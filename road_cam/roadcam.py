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

class RoadCam:

    def __init__(self, blob_path, detections_queue) -> None:
        self.blob_path = blob_path
        self.sync_nn = True
        self.detectons_queue = detections_queue


    def setup_pipeline(self):
        self.pipeline = dai.Pipeline()
        self.camRgb = self.pipeline.create(dai.node.ColorCamera)
        self.spatialDetectionNetwork = self.pipeline.create(dai.node.MobileNetSpatialDetectionNetwork)
        mono_left = self.pipeline.create(dai.node.MonoCamera)
        mono_right = self.pipeline.create(dai.node.MonoCamera)
        self.stereo = self.pipeline.create(dai.node.StereoDepth)
        self.xoutRgb = self.pipeline.create(dai.node.XLinkOut)
        self.xoutNN = self.pipeline.create(dai.node.XLinkOut)
        self.xoutDepth = self.pipeline.create(dai.node.XLinkOut)
        self.xoutRgb.setStreamName("rgb")
        self.xoutNN.setStreamName("detections")
        self.xoutDepth.setStreamName("depth")
        self.camRgb.setPreviewSize(300, 300)
        self.camRgb.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)
        self.camRgb.setInterleaved(False)
        self.camRgb.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR)
        mono_left.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
        mono_left.setCamera("left")
        mono_right.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
        mono_right.setCamera("right")
        self.stereo.setDefaultProfilePreset(dai.node.StereoDepth.PresetMode.HIGH_DENSITY)
        self.stereo.setDepthAlign(dai.CameraBoardSocket.CAM_A)
        self.stereo.setSubpixel(True)
        self.stereo.setOutputSize(mono_left.getResolutionWidth(), mono_left.getResolutionHeight())
        self.spatialDetectionNetwork.setBlobPath(self.blob_path)
        self.spatialDetectionNetwork.setConfidenceThreshold(0.5)
        self.spatialDetectionNetwork.input.setBlocking(False)
        self.spatialDetectionNetwork.setBoundingBoxScaleFactor(0.5)
        self.spatialDetectionNetwork.setDepthLowerThreshold(100)
        self.spatialDetectionNetwork.setDepthUpperThreshold(5000)
        mono_left.out.link(self.stereo.left)
        mono_right.out.link(self.stereo.right)
        self.camRgb.preview.link(self.spatialDetectionNetwork.input)
        if self.sync_nn:
            self.spatialDetectionNetwork.passthrough.link(self.xoutRgb.input)
        else:
            self.camRgb.preview.link(self.xoutRgb.input)
        self.spatialDetectionNetwork.out.link(self.xoutNN.input)
        self.stereo.depth.link(self.spatialDetectionNetwork.inputDepth)
        self.spatialDetectionNetwork.passthroughDepth.link(self.xoutDepth.input)
        

    # def 

    def run(self, demo=False):
        with dai.Device(self.pipeline) as pipeline:
            # Output queues will be used to get the rgb frames and nn data from the outputs defined above
            previewQueue = pipeline.getOutputQueue(name="rgb", maxSize=4, blocking=False)
            detectionNNQueue = pipeline.getOutputQueue(name="detections", maxSize=4, blocking=False)
            depthQueue = pipeline.getOutputQueue(name="depth", maxSize=4, blocking=False)

            frame = None
            detections = []
            startTime = time.monotonic()
            counter = 0
            # self.detectons = queue.Queue()
            while True:
                inPreview = previewQueue.get()
                inDet = detectionNNQueue.get()
                depth = depthQueue.get()

                counter+=1
                current_time = time.monotonic()
                if (current_time - startTime) > 1 :
                    fps = counter / (current_time - startTime)
                    counter = 0
                    startTime = current_time

                frame = inPreview.getCvFrame()

                if demo:
                    depthFrame = depth.getFrame() # depthFrame values are in millimeters

                    depth_downscaled = depthFrame[::4]
                    if np.all(depth_downscaled == 0):
                        min_depth = 0  # Set a default minimum depth value when all elements are zero
                    else:
                        min_depth = np.percentile(depth_downscaled[depth_downscaled != 0], 1)
                    max_depth = np.percentile(depth_downscaled, 99)
                    depthFrameColor = np.interp(depthFrame, (min_depth, max_depth), (0, 255)).astype(np.uint8)
                    depthFrameColor = cv2.applyColorMap(depthFrameColor, cv2.COLORMAP_HOT)

                detections = inDet.detections
                if frame is not None:
                    frame_detections = []
                    for detection in detections:
                        label = detection.label
                        if label_to_id[detection.label] not in ROAD_OBJECTS:
                            continue
                        x1 = int(detection.xmin * frame.shape[1])
                        y1 = int(detection.ymin * frame.shape[0])
                        x2 = int(detection.xmax * frame.shape[1])
                        y2 = int(detection.ymax * frame.shape[0])
                        if demo:
                            try:
                                cv2.putText(frame, str(label), (x1 + 10, y1 + 20), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
                                cv2.putText(frame, "{:.2f}".format(detection.confidence*100), (x1 + 10, y1 + 35), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
                                cv2.putText(frame, f"X: {int(detection.spatialCoordinates.x)} mm", (x1 + 10, y1 + 50), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
                                cv2.putText(frame, f"Y: {int(detection.spatialCoordinates.y)} mm", (x1 + 10, y1 + 65), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
                                cv2.putText(frame, f"Z: {int(detection.spatialCoordinates.z)} mm", (x1 + 10, y1 + 80), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
                                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), cv2.FONT_HERSHEY_SIMPLEX)
                            except:
                                pass

                            
                            frame_dict = {'label': label_to_id[detection.label],
                                                'depth': detection.spatialCoordinates.z,
                                                'bbox': [detection.xmin, detection.ymin, detection.xmax, detection.ymax]
                                        }
                            
                            frame_detections.append(frame_dict)
                        
                    if demo:
                        # cv2.putText(frame, "NN fps: {:.2f}".format(fps), (2, frame.shape[0] - 4), cv2.FONT_HERSHEY_TRIPLEX, 0.4, (255,255,255))
                        cv2.imshow("depth", depthFrameColor)
                        cv2.imshow("preview", frame)
                        if cv2.waitKey(1) == ord('q'):
                            break    
                # print(frame_detections)
                # print("UNATRE")
                # print(self.detectons_queue.qsize())
                # self.detectons_queue = queue.Queue([1, 2, 3])
                self.detectons_queue.put(frame_detections)
                # self.detectons_queue.put("GJUPTIN")
                # print(self.detectons_queue.get())
                # self.detectons.put(frame_detections)

                        




if __name__ == "__main__":
    blob_path = './blobconverter/mobilenet-ssd_openvino_2021.4_6shave.blob'
    detections_queue = queue.Queue()
    road_cam = RoadCam(blob_path, detections_queue= detections_queue)
    road_cam.setup_pipeline()
    road_cam.run(demo=True)
    cv2.destroyAllWindows()    
    sys.exit(0)
