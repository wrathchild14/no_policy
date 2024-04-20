package com.example.safety;

import android.Manifest;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.ImageFormat;
import android.graphics.SurfaceTexture;
import android.hardware.camera2.CameraAccessException;
import android.hardware.camera2.CameraCaptureSession;
import android.hardware.camera2.CameraCharacteristics;
import android.hardware.camera2.CameraDevice;
import android.hardware.camera2.CameraManager;
import android.hardware.camera2.CaptureRequest;
import android.hardware.camera2.params.StreamConfigurationMap;
import android.media.Image;
import android.media.ImageReader;
import android.media.MediaPlayer;
import android.os.Bundle;
import android.os.Handler;
import android.os.HandlerThread;
import android.util.Log;
import android.util.Size;
import android.view.Surface;
import android.view.TextureView;
import android.view.View;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Timer;
import java.util.TimerTask;

import okhttp3.Call;
import okhttp3.Callback;
import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;

public class MainActivity extends AppCompatActivity {
    private static final int REQUEST_CAMERA_PERMISSION = 100;
    private static final String TAG = "MainActivity";
    private static final long CAPTURE_INTERVAL = 500; // milliseconds
    private TextureView textureView;
    private Button startStopButton;
    private TextView warningView;
    private CameraManager cameraManager;
    private String cameraId;
    private CameraDevice cameraDevice;
    private CameraCaptureSession cameraCaptureSession;
    private CaptureRequest.Builder captureRequestBuilder;
    private Size previewSize;

    private boolean isCapturing = false;

    private Timer timer;
    private HandlerThread backgroundThread;
    private Handler backgroundHandler;
    private MediaPlayer mediaPlayer;
    private OkHttpClient client;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        client = new OkHttpClient();

        // Screen doesn't sleep
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);

        textureView = findViewById(R.id.textureView);
        startStopButton = findViewById(R.id.startStopButton);

        warningView = findViewById(R.id.warningTextView);

        startStopButton.setOnClickListener(v -> onStartStopButtonClick());

        cameraManager = (CameraManager) getSystemService(CAMERA_SERVICE);
        textureView.setSurfaceTextureListener(textureListener);

        previewSize = new Size(400, 400); // Set your desired preview size here

        mediaPlayer = new MediaPlayer();
        mediaPlayer = MediaPlayer.create(this, R.raw.beep2);
//        mediaPlayer.setLooping(true);

        mediaPlayer.setOnCompletionListener(mp -> Log.d(TAG, "Playback completed"));

        mediaPlayer.setOnErrorListener((mp, what, extra) -> {
            Log.e(TAG, "MediaPlayer error: " + what + ", " + extra);
            return false;
        });
    }

    private void openCamera() {
        try {
            String[] cameraIdList = cameraManager.getCameraIdList();
            if (cameraIdList.length == 0) {
                // No cameras found
                Toast.makeText(this, "No cameras found", Toast.LENGTH_SHORT).show();
                return;
            }
            // Iterate through the list of camera IDs and choose the front-facing camera
            for (String id : cameraIdList) {
                CameraCharacteristics characteristics = cameraManager.getCameraCharacteristics(id);
                // Check if the camera is facing front
                Integer facing = characteristics.get(CameraCharacteristics.LENS_FACING);
                if (facing != null && facing == CameraCharacteristics.LENS_FACING_FRONT) {
                    cameraId = id;
                    break;
                }
            }
            // If no front-facing camera is found, just use the first available camera
            if (cameraId == null) {
                cameraId = cameraIdList[0];
            }
            // Check camera permission before opening the camera
            if (ActivityCompat.checkSelfPermission(this, Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
                ActivityCompat.requestPermissions(this, new String[]{Manifest.permission.CAMERA}, REQUEST_CAMERA_PERMISSION);
                return;
            }
            cameraManager.openCamera(cameraId, stateCallback, null);
        } catch (CameraAccessException e) {
            e.printStackTrace();
        }
    }

    private CameraDevice.StateCallback stateCallback = new CameraDevice.StateCallback() {
        @Override
        public void onOpened(@NonNull CameraDevice camera) {
            cameraDevice = camera;
            createCameraPreview();
        }

        @Override
        public void onDisconnected(@NonNull CameraDevice camera) {
            if (cameraDevice != null) {
                cameraDevice.close();
                cameraDevice = null;
            }
        }

        @Override
        public void onError(@NonNull CameraDevice camera, int error) {
            if (cameraDevice != null) {
                cameraDevice.close();
                cameraDevice = null;
            }
        }
    };

    private void createCameraPreview() {
        SurfaceTexture texture = textureView.getSurfaceTexture();
        if (texture == null) {
            return;
        }
        texture.setDefaultBufferSize(previewSize.getWidth(), previewSize.getHeight());
        Surface surface = new Surface(texture);

        try {
            captureRequestBuilder = cameraDevice.createCaptureRequest(CameraDevice.TEMPLATE_PREVIEW);
            captureRequestBuilder.addTarget(surface);

            cameraDevice.createCaptureSession(Arrays.asList(surface), new CameraCaptureSession.StateCallback() {
                @Override
                public void onConfigured(@NonNull CameraCaptureSession session) {
                    if (cameraDevice == null) {
                        return;
                    }

                    cameraCaptureSession = session;
                    try {
                        captureRequestBuilder.set(CaptureRequest.CONTROL_AF_MODE, CaptureRequest.CONTROL_AF_MODE_CONTINUOUS_PICTURE);
                        cameraCaptureSession.setRepeatingRequest(captureRequestBuilder.build(), null, null);
                    } catch (CameraAccessException e) {
                        e.printStackTrace();
                    }
                }

                @Override
                public void onConfigureFailed(@NonNull CameraCaptureSession session) {
                    Toast.makeText(MainActivity.this, "Configuration change", Toast.LENGTH_SHORT).show();
                }
            }, null);
        } catch (CameraAccessException e) {
            e.printStackTrace();
        }
    }


    private void startCapturing() {
        if (!isCapturing) {
            isCapturing = true;
            timer = new Timer();
            timer.schedule(new TimerTask() {
                @Override
                public void run() {
                    captureImage();
                }
            }, 0, CAPTURE_INTERVAL); // Capture image every specified interval
        }
    }

    private void stopCapturing() {
        if (isCapturing) {
            isCapturing = false;
            if (timer != null) {
                timer.cancel();
                timer = null;
            }
        }
    }

    private void captureImage() {
        if (cameraDevice == null) {
            Log.e(TAG, "Camera device is null");
            return;
        }

        // Create a new background thread only if it's null or not alive
        if (backgroundThread == null || !backgroundThread.isAlive()) {
            backgroundThread = new HandlerThread("ImageReaderHandlerThread");
            backgroundThread.start();
            backgroundHandler = new Handler(backgroundThread.getLooper());
        }

        // Use the backgroundHandler to execute the image capture logic
        backgroundHandler.post(() -> {
            // Create an image reader to capture the image
            ImageReader imageReader = ImageReader.newInstance(
                    previewSize.getWidth(), previewSize.getHeight(),
                    ImageFormat.JPEG, 1);

            // Set up an image available listener to handle captured images
            imageReader.setOnImageAvailableListener(reader -> {
                Image image = null;
                try {
                    image = reader.acquireLatestImage();
                    if (image != null) {
                        // Convert the captured image to byte array
                        ByteBuffer buffer = image.getPlanes()[0].getBuffer();
                        byte[] bytes = new byte[buffer.remaining()];
                        buffer.get(bytes);

                        // Send the image data via POST request
                        sendImageToServer(bytes);
                    }
                } finally {
                    if (image != null) {
                        image.close();
                    }
                    if (imageReader != null) {
                        imageReader.close();
                    }
                }
            }, backgroundHandler); // Use backgroundHandler for the listener

            // Create a capture session and configure it to capture images
            try {
                List<Surface> outputSurfaces = new ArrayList<>();
                SurfaceTexture surfaceTexture = textureView.getSurfaceTexture();
                surfaceTexture.setDefaultBufferSize(previewSize.getWidth(), previewSize.getHeight());
                Surface previewSurface = new Surface(surfaceTexture);
                outputSurfaces.add(previewSurface);
                outputSurfaces.add(imageReader.getSurface());
                if (cameraDevice != null) {
                    cameraDevice.createCaptureSession(outputSurfaces, new CameraCaptureSession.StateCallback() {
                        @Override
                        public void onConfigured(@NonNull CameraCaptureSession session) {
                            try {
                                // Create a capture request and set it to continuously capture images
                                CaptureRequest.Builder captureRequestBuilder =
                                        cameraDevice.createCaptureRequest(CameraDevice.TEMPLATE_PREVIEW);
                                captureRequestBuilder.addTarget(previewSurface);
                                captureRequestBuilder.addTarget(imageReader.getSurface());
                                session.setRepeatingRequest(captureRequestBuilder.build(), null, backgroundHandler);
                            } catch (CameraAccessException e) {
                                e.printStackTrace();
                            }
                        }

                        @Override
                        public void onConfigureFailed(@NonNull CameraCaptureSession session) {
                            Log.e(TAG, "Capture session configuration failed");
                        }
                    }, backgroundHandler); // Use backgroundHandler for the session creation
                }
            } catch (CameraAccessException e) {
                e.printStackTrace();
            }
        });
    }


    private void closeCamera() {
        if (cameraCaptureSession != null) {
            cameraCaptureSession.close();
            cameraCaptureSession = null;
        }
        if (cameraDevice != null) {
            cameraDevice.close();
            cameraDevice = null;
        }
        if (backgroundThread != null) {
            backgroundThread.quitSafely();
            try {
                backgroundThread.join();
                backgroundThread = null;
                backgroundHandler = null;
            } catch (InterruptedException e) {
                e.printStackTrace();
            }
        }
    }


    private void sendImageToServer(byte[] imageData) {
        // Implement sending the image data via POST request to your server
        // You can use libraries like Retrofit, Volley, or OkHttpClient to make the POST request
        // Example using OkHttpClient:
        ByteArrayOutputStream outputStream = new ByteArrayOutputStream();
        BitmapFactory.Options options = new BitmapFactory.Options();
        options.inSampleSize = 1; // Adjust this value as needed for quality vs. size trade-off
        Bitmap bitmap = BitmapFactory.decodeByteArray(imageData, 0, imageData.length, options);
        bitmap.compress(Bitmap.CompressFormat.JPEG, 50, outputStream); // Adjust the quality (0-100) as needed

        // Get the compressed image data as a byte array
        byte[] compressedData = outputStream.toByteArray();


        // Create the request body with the image data
        RequestBody requestBody = RequestBody.create(compressedData, MediaType.parse("image/jpeg"));

        // Build the POST request
        Request request = new Request.Builder()
                .url("http://192.168.4.38:5000/upload")
                .post(requestBody)
                .build();

        // Execute the request asynchronously
        client.newCall(request).enqueue(new Callback() {
            @Override
            public void onFailure(Call call, IOException e) {
                Log.e(TAG, "IMAGE REQUEST FAILED", e);
            }

            @Override
            public void onResponse(Call call, Response response) throws IOException {
                if (!response.isSuccessful()) {
                    Log.e(TAG, "Unexpected code " + response);
                }
                // Handle the response from the server
                String responseData = response.body().string();
                Log.d(TAG, "Server response: " + responseData);

                // Parse the JSON response to extract the signal value
                try {
                    JSONObject jsonResponse = new JSONObject(responseData);
                    int signal = jsonResponse.getInt("signal");

                    // Check the signal value and trigger a beep sound accordingly
                    if (signal == 1) {
                        playBeepSound();
                        showWarning();
                        System.out.println("BEEEP");
                    } else {
                        if (mediaPlayer != null && mediaPlayer.isPlaying()) {
                            mediaPlayer.stop();
                            mediaPlayer.reset();
                        }
                        hideWarning();
                        System.out.println("NOT BEEP");
                    }
                } catch (JSONException e) {
                    Log.e(TAG, "Error parsing JSON response", e);
                }
                response.close();
            }
        });

    }

    private void playBeepSound() {
        // Stop any ongoing playback
        if (mediaPlayer != null && mediaPlayer.isPlaying()) {
            mediaPlayer.stop();
            mediaPlayer.reset();
        }
        // Start playing the beep sound
        mediaPlayer = MediaPlayer.create(this, R.raw.beep2);
//        mediaPlayer.setOnCompletionListener(mp -> Log.d(TAG, "Playback completed"));
//        mediaPlayer.setOnErrorListener((mp, what, extra) -> {
//            Log.e(TAG, "MediaPlayer error: " + what + ", " + extra);
//            return false;
//        });
        if (mediaPlayer != null) {
            mediaPlayer.start();
        }
    }

    private void onStartStopButtonClick() {
        if (isCapturing) {
            startStopButton.setText("Start");
            stopCapturing();
        } else {
            startStopButton.setText("Stop");
            startCapturing();
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        stopCapturing();
        closeCamera();
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (textureView.isAvailable()) {
            openCamera();
        } else {
            textureView.setSurfaceTextureListener(textureListener);
        }
    }
    private void showWarning() {
        runOnUiThread(() -> {
            warningView.setVisibility(View.VISIBLE);
        });
    }

    private void hideWarning() {
        runOnUiThread(() -> {
            warningView.setVisibility(View.GONE);
        });
    }

    @Override
    protected void onStop() {
        super.onStop();
        closeCamera();
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        closeCamera();
        if (mediaPlayer != null) {
            mediaPlayer.release();
        }
    }

    private TextureView.SurfaceTextureListener textureListener = new TextureView.SurfaceTextureListener() {
        @Override
        public void onSurfaceTextureAvailable(@NonNull SurfaceTexture surface, int width, int height) {
            chooseOptimalPreviewSize(width, height);
            openCamera();
        }

        @Override
        public void onSurfaceTextureSizeChanged(@NonNull SurfaceTexture surface, int width, int height) {
            // No implementation needed
        }

        @Override
        public boolean onSurfaceTextureDestroyed(@NonNull SurfaceTexture surface) {
            return false;
        }

        @Override
        public void onSurfaceTextureUpdated(@NonNull SurfaceTexture surface) {
            // No implementation needed
        }
    };

    private void chooseOptimalPreviewSize(int width, int height) {
        if (cameraId == null) {
            Log.e(TAG, "Camera ID is null");
            return;
        }
        CameraCharacteristics characteristics;
        try {
            characteristics = cameraManager.getCameraCharacteristics(cameraId);
            StreamConfigurationMap map = characteristics.get(CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP);
            Size[] sizes = map.getOutputSizes(SurfaceTexture.class);
            if (sizes == null || sizes.length == 0) {
                return;
            }
            previewSize = sizes[0]; // Initialize previewSize with the first available size
            for (Size size : sizes) {
                if (size.getWidth() <= width && size.getHeight() <= height) {
                    previewSize = size;
                    return;
                }
            }
        } catch (CameraAccessException e) {
            e.printStackTrace();
        }
    }
}
