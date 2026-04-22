from flask import Flask, render_template, request, jsonify, send_file
try:
    from moviepy.editor import VideoFileClip
except ImportError:
    from moviepy import VideoFileClip
import os
from dotenv import load_dotenv
import time
import requests

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# Get API key
API_KEY = os.getenv('TWELVE_LABS_API_KEY')

if not API_KEY:
    print("ERROR: TWELVE_LABS_API_KEY not found!")
    print(f"Looking for .env file in: {os.getcwd()}")
    exit(1)

print(f"✓ API Key loaded: {API_KEY[:10]}...")

# Twelve Labs API base URL
BASE_URL = "https://api.twelvelabs.io/v1.3"

# Headers for API requests
HEADERS = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json"
}

INDEX_NAME = "video-trimmer-index"
index_id = None

def get_or_create_index():
    """Get existing index or create new one"""
    global index_id
    
    # List existing indexes
    response = requests.get(f"{BASE_URL}/indexes", headers=HEADERS)
    
    if response.status_code == 200:
        indexes = response.json().get('data', [])
        for index in indexes:
            # Try both possible field names
            name = index.get('index_name') or index.get('name')
            if name == INDEX_NAME:
                index_id = index.get('_id') or index.get('id')
                print(f"✓ Using existing index: {index_id}")
                return index_id
    
    # Create new index
    print("Creating new index...")
    payload = {
        "index_name": INDEX_NAME,
        "models": [
            {
                "model_name": " pegasus1.2",
                "model_options": ["visual", "transcription", "conversation", "text_in_video"]
            }
        ]
    }
    
    response = requests.post(f"{BASE_URL}/indexes", headers=HEADERS, json=payload)
    
    if response.status_code in [200, 201]:
        result = response.json()
        index_id = result.get('_id') or result.get('id')
        print(f"✓ Created new index: {index_id}")
        return index_id
    else:
        print(f"Error creating index: {response.status_code}")
        print(f"Response: {response.text}")
        raise Exception(f"Failed to create index: {response.text}")

def upload_video(video_path):
    """Upload video to Twelve Labs"""
    global index_id
    
    print("Uploading video...")
    
    with open(video_path, 'rb') as video_file:
        files = {
            'video_file': video_file
        }
        data = {
            'index_id': index_id,
            'language': 'en'
        }
        
        # Remove Content-Type from headers for multipart/form-data
        upload_headers = {"x-api-key": API_KEY}
        
        response = requests.post(
            f"{BASE_URL}/tasks",
            headers=upload_headers,
            files=files,
            data=data
        )
    
    if response.status_code in [200, 201]:
        task_id = response.json().get('_id')
        print(f"✓ Upload started, task ID: {task_id}")
        return task_id
    else:
        print(f"Upload error: {response.text}")
        raise Exception(f"Failed to upload video: {response.text}")

def get_video_info(video_id):
    """Get information about what was indexed in the video"""
    response = requests.get(
        f"{BASE_URL}/indexes/{index_id}/videos/{video_id}",
        headers={"x-api-key": API_KEY}
    )
    
    if response.status_code == 200:
        info = response.json()
        print("\n📹 Video Info:")
        print(f"Duration: {info.get('metadata', {}).get('duration')}s")
        print(f"Indexed at: {info.get('created_at')}")
        print(f"Status: {info.get('status')}")
        return info
    return None

def wait_for_task(task_id):
    """Wait for video indexing to complete"""
    print("Waiting for video to be indexed...")
    
    max_attempts = 120  # 10 minutes max
    attempt = 0
    
    while attempt < max_attempts:
        response = requests.get(f"{BASE_URL}/tasks/{task_id}", headers=HEADERS)
        
        if response.status_code == 200:
            task_data = response.json()
            status = task_data.get('status')
            
            print(f"  Status: {status}")
            
            if status == 'ready':
                video_id = task_data.get('video_id')
                print(f"✓ Video indexed! Video ID: {video_id}")
                return video_id
            elif status in ['failed', 'error']:
                raise Exception(f"Video indexing failed: {task_data}")
        
        time.sleep(5)
        attempt += 1
    
    raise Exception("Video indexing timeout")

def search_video(query_text):
    """Search for moments in the video"""
    global index_id
    
    print(f"Searching for: '{query_text}'")
    
    search_headers = {"x-api-key": API_KEY}
    
    # Try multiple search strategies
    files = {
        'index_id': (None, index_id),
        'query_text': (None, query_text),
        'search_options': (None, 'visual'),
        'search_options': (None, 'conversation'),
        'search_options': (None, 'text_in_video'),
        'search_options': (None, 'transcription'),  # Add both options
        'page_limit': (None, '20'),
        'threshold': (None, 'low'),  # Lower threshold to get more results
        'adjust_confidence_level': (None, '0.5')  # Adjust confidence
    }
    
    response = requests.post(
        f"{BASE_URL}/search",
        headers=search_headers,
        files=files
    )
    
    if response.status_code == 200:
        all_results = response.json().get('data', [])
        
        # Debug - print ALL results with scores
        print(f"\n📊 Search Results ({len(all_results)} found):")
        for i, result in enumerate(all_results[:10]):
            start = result.get('start', 0)
            end = result.get('end', 0)
            score = result.get('score', 0)
            confidence = result.get('confidence', 'N/A')
            print(f"  {i+1}. {start:.1f}s - {end:.1f}s | Score: {score:.2%} | Confidence: {confidence}")
        
        # Return all results even with low scores
        return all_results[:5]
    else:
        print(f"Search error: {response.status_code}")
        print(f"Response: {response.text}")
        return []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_video():
    if 'video' not in request.files:
        return jsonify({'error': 'No video file'}), 400
    
    video_file = request.files['video']
    prompt = request.form.get('prompt', '')
    
    if not prompt:
        return jsonify({'error': 'No prompt provided'}), 400
    
    # Save uploaded video
    video_path = os.path.join(app.config['UPLOAD_FOLDER'], video_file.filename)
    video_file.save(video_path)
    
    try:
        # Get or create index
        get_or_create_index()
        
        # Upload video
        task_id = upload_video(video_path)
        
        # Wait for indexing
        video_id = wait_for_task(task_id)
        # After wait_for_task
        video_id = wait_for_task(task_id)
        get_video_info(video_id)
        
        # Search for relevant moments
        search_results = search_video(prompt)
        
        if not search_results:
            return jsonify({'error': 'No relevant moments found'}), 404
        
        # Extract clips
        clips = []
        for result in search_results:
            if 'start' in result and 'end' in result:
                clips.append({
                    'start': result['start'],
                    'end': result['end'],
                    'score': result.get('score', 0.0),
                    'confidence': result.get('confidence', 'unknown')
                })
                print(f"  Clip: {result['start']}s - {result['end']}s")
        
        if not clips:
            return jsonify({'error': 'No clips with timestamps found'}), 404
        
        print(f"✓ Creating {len(clips)} video clips...")
        
        # Trim video
        output_clips = []
        video_clip = VideoFileClip(video_path)
        
        for i, clip_info in enumerate(clips):
            start_time = clip_info['start']
            end_time = clip_info['end']
            
            print(f"  Trimming clip {i+1}: {start_time}s - {end_time}s")
            
            trimmed = video_clip.subclipped(start_time, end_time)
            output_filename = f"clip_{i}_{video_file.filename}"
            output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
            
            trimmed.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                logger=None
            )
            
            output_clips.append({
                'filename': output_filename,
                'start': start_time,
                'end': end_time,
                'score': clip_info['score']
            })
        
        video_clip.close()
        print(f"✓ Successfully created {len(output_clips)} clips!")
        
        return jsonify({
            'success': True,
            'clips': output_clips
        })
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def download(filename):
    return send_file(
        os.path.join(app.config['OUTPUT_FOLDER'], filename),
        as_attachment=True
    )

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🎬 Video Trimmer Server Starting...")
    print("="*50 + "\n")
    app.run(debug=True, port=5000)