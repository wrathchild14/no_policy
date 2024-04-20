from depthai_sdk import OakCamera
import depthai as dai
with OakCamera(replay='17-18443010F1DA6C1200') as oak:
    # Created CameraComponent/StereoComponent will use streams from the recording
    camera = oak.create_camera('color')
    # left = oak.create_camera('left')
    # right = oak.create_camera('right')
    # depth = oak.create_stereo('depth')
    # depth = oak.create_stereo('depth',)
    nn = oak.create_nn('mobilenet-ssd', camera, spatial=False)
    # print(nn.detections)
    oak.visualize([camera.out.camera], scale=2/3, fps=True)
    oak.start(blocking=True)