import os
import cv2
import numpy as np
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from ultralytics import YOLO
import uuid

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'static/uploads'
RESULT_FOLDER = 'static/results'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULT_FOLDER'] = RESULT_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

MODEL = None

def load_model():
    global MODEL
    print("Loading YOLO model...")
    MODEL = YOLO('yolov8n.pt')
    print("YOLO model loaded!")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def detect_animals(image_path, conf_threshold=0.3):
    global MODEL
    if MODEL is None:
        load_model()

    img = cv2.imread(image_path)
    if img is None:
        return None

    results = MODEL(image_path, conf=conf_threshold, verbose=False)

    # Animal classes in COCO dataset
    ANIMAL_CLASSES = {
        15: 'bird', 16: 'cat', 17: 'dog', 18: 'horse',
        19: 'sheep', 20: 'cow', 21: 'elephant', 22: 'bear',
        23: 'zebra', 24: 'giraffe'
    }

    detections = []
    annotated_img = img.copy()

    for result in results:
        boxes = result.boxes
        for box in boxes:
            class_id = int(box.cls[0])
            if class_id in ANIMAL_CLASSES:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                confidence = float(box.conf[0])
                class_name = result.names[class_id]
                center_x = int((x1 + x2) / 2)
                center_y = int((y1 + y2) / 2)

                detections.append({
                    'class': class_name,
                    'confidence': round(confidence, 2),
                    'bbox': [int(x1), int(y1), int(x2), int(y2)],
                    'center': [center_x, center_y]
                })

                # Draw bounding box
                cv2.rectangle(annotated_img, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 100), 2)
                # Draw label background
                label = f"{class_name}: {confidence:.2f}"
                (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
                cv2.rectangle(annotated_img, (int(x1), int(y1) - lh - 10), (int(x1) + lw + 4, int(y1)), (0, 255, 100), -1)
                cv2.putText(annotated_img, label, (int(x1) + 2, int(y1) - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2)
                # Draw center dot
                cv2.circle(annotated_img, (center_x, center_y), 5, (255, 50, 50), -1)

    herds = group_into_herds(detections)

    # Draw herd circles on image
    for herd in herds:
        if herd['count'] > 1:
            cx, cy = herd['center']
            cv2.circle(annotated_img, (cx, cy), 20, (255, 200, 0), 2)
            cv2.putText(annotated_img, f"Herd {herd['id']} ({herd['count']})", (cx - 30, cy - 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 200, 0), 2)

    result_filename = f"result_{uuid.uuid4().hex[:8]}.jpg"
    result_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)
    cv2.imwrite(result_path, annotated_img)

    return {
        'total_animals': len(detections),
        'detections': detections,
        'herds': herds,
        'annotated_image': result_filename
    }

def group_into_herds(detections, herd_threshold=150):
    if not detections:
        return []

    n = len(detections)
    adj = [[] for _ in range(n)]

    for i in range(n):
        for j in range(i + 1, n):
            dx = detections[i]['center'][0] - detections[j]['center'][0]
            dy = detections[i]['center'][1] - detections[j]['center'][1]
            distance = np.sqrt(dx * dx + dy * dy)
            if distance < herd_threshold:
                adj[i].append(j)
                adj[j].append(i)

    visited = [False] * n
    herds = []

    for i in range(n):
        if not visited[i]:
            herd = []
            stack = [i]
            visited[i] = True
            while stack:
                node = stack.pop()
                herd.append(detections[node])
                for neighbor in adj[node]:
                    if not visited[neighbor]:
                        visited[neighbor] = True
                        stack.append(neighbor)

            if herd:
                avg_x = int(np.mean([d['center'][0] for d in herd]))
                avg_y = int(np.mean([d['center'][1] for d in herd]))
                herds.append({
                    'id': len(herds) + 1,
                    'animals': herd,
                    'count': len(herd),
                    'center': [avg_x, avg_y],
                    'types': list(set([d['class'] for d in herd]))
                })

    return herds

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if file and allowed_file(file.filename):
        filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        latitude = request.form.get('latitude', type=float)
        longitude = request.form.get('longitude', type=float)

        try:
            result = detect_animals(filepath)
            if result is None:
                return jsonify({'error': 'Could not read image'}), 400

            # FIX: use correct result image URL from results folder
            result_image_url = f"/static/results/{result['annotated_image']}"
            original_image_url = f"/{filepath}"

            if latitude is not None and longitude is not None:
                result['location'] = {'latitude': latitude, 'longitude': longitude}

            return jsonify({
                'success': True,
                'original_url': original_image_url,
                'result_url': result_image_url,
                'result': result
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

if __name__ == '__main__':
    load_model()
    print("\n" + "=" * 50)
    print("  Animal Herd Detection System")
    print("  Open: http://localhost:5000")
    print("=" * 50 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
