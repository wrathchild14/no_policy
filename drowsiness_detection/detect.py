from scipy.spatial import distance
from imutils import face_utils
import imutils
import dlib
import cv2
import os

def eye_aspect_ratio(eye):
	A = distance.euclidean(eye[1], eye[5])
	B = distance.euclidean(eye[2], eye[4])
	C = distance.euclidean(eye[0], eye[3])
	ear = (A + B) / (2.0 * C)
	return ear

def drowsy_system(frames,detect, predict, lStart, lEnd, rStart, rEnd):
	# threshold for the 'closed eye'
	thresh = 0.25

	# the number of frames with closed eyes that count as drowsy
	frame_check = 2

	# temporary variable to check the drowsiness
	drowsy_count = 0
	# looping over frames
	for frame in frames:
		# resizing
		frame = imutils.resize(frame, width=450)
		gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
		# detecting faces in the image
		subjects = detect(gray, 0)
		# looping over the faces
		for subject in subjects:
			shape = predict(gray, subject)
			shape = face_utils.shape_to_np(shape)
			leftEye = shape[lStart:lEnd]
			rightEye = shape[rStart:rEnd]
			leftEAR = eye_aspect_ratio(leftEye)
			rightEAR = eye_aspect_ratio(rightEye)
			ear = (leftEAR + rightEAR) / 2.0
			leftEyeHull = cv2.convexHull(leftEye)
			rightEyeHull = cv2.convexHull(rightEye)
			cv2.drawContours(frame, [leftEyeHull], -1, (0, 255, 0), 1)
			cv2.drawContours(frame, [rightEyeHull], -1, (0, 255, 0), 1)
            
            # if the closeness is below 0.25, we count it as 'drowsy'
			if ear < thresh:
                # count the frame as drowsy
				drowsy_count += 1
                
				if drowsy_count > frame_check:
					return 1
			else:
                # if eyes not closed or just blinking, set the drowsy frame count back to 0
				drowsy_count = 0
	return 0
