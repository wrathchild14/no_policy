from flask import Flask, request, jsonify
from PIL import Image

app = Flask(__name__)


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
