from flask import Flask, render_template, request, jsonify, send_file
try:
    from moviepy.editor import VideoFileClip
except ImportError:
    from moviepy import VideoFileClip
import os
from dotenv import load_dotenv
import time
import requests
import random

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

INDEX_NAME = "video-trimmer-index" + str(random.randrange(1,1000))
index_id = None

def get_or_create_index():
    """Get existing index or create new one"""
    global index_id  # ⭐ CRITICAL - must be here!
    
    # List existing indexes
    response = requests.get(f"{BASE_URL}/indexes", headers=HEADERS)
    
    if response.status_code == 200:
        indexes = response.json().get('data', [])
        for index in indexes:
            name = index.get('index_name') or index.get('name')
            if name == INDEX_NAME:
                index_id = index.get('_id') or index.get('id')  # ⭐ Setting global
                print(f"✓ Using existing index: {index_id}")
                return index_id
    
    # Create new index
    print("Creating new index...")
    payload = {
        "index_name": INDEX_NAME,
        "models": [
            {
                "model_name": "marengo3.0",
                "model_options": ["visual", "audio"]
            }
        ]
    }
    
    response = requests.post(f"{BASE_URL}/indexes", headers=HEADERS, json=payload)
    
    if response.status_code in [200, 201]:
        result = response.json()
        index_id = result.get('_id') or result.get('id')  # ⭐ Setting global
        print("Global Index",index_id)
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
        print("\n📹 Video Info from endpoint:")
        print(f"Full response: {info}")
        return info
    else:
        print(f"Could not get video info: {response.status_code}")
        print(f"Response: {response.text}")
        return None

def wait_for_task(task_id):
    """Wait for video indexing to complete with better error handling"""
    print(f"Waiting for task {task_id} to complete...")
    
    max_attempts = 240  # 40 minutes (10 second intervals)
    attempt = 0
    last_status = None
    status_unchanged_count = 0
    
    while attempt < max_attempts:
        try:
            response = requests.get(
                f"{BASE_URL}/tasks/{task_id}",
                headers={"x-api-key": API_KEY}
            )
            
            if response.status_code != 200:
                print(f"  ⚠️ Error getting task status: {response.status_code}")
                print(f"  Response: {response.text}")
                time.sleep(10)
                attempt += 1
                continue
            
            task_data = response.json()
            status = task_data.get('status')
            
            # Check if status is stuck
            if status == last_status:
                status_unchanged_count += 1
            else:
                status_unchanged_count = 0
            
            last_status = status
            
            # Log every 6 attempts (1 minute)
            if attempt % 6 == 0 or status != 'indexing':
                print(f"\n  Attempt {attempt + 1} ({attempt // 6} min):")
                print(f"  Status: {status}")
                print(f"  Updated: {task_data.get('updated_at')}")
                
                # Show HLS status if available
                if 'hls' in task_data:
                    hls_status = task_data['hls'].get('status')
                    print(f"  HLS: {hls_status}")
            
            # Check if stuck
            if status_unchanged_count > 30:  # 5 minutes with no change
                print(f"\n  ⚠️ WARNING: Status '{status}' hasn't changed in 5 minutes")
                print(f"  This might indicate a problem. Full data:")
                print(f"  {task_data}")
            
            # Success
            if status == 'ready':
                video_id = task_data.get('video_id')
                metadata = task_data.get('system_metadata', {})
                duration = metadata.get('duration', 0)
                
                print(f"\n✓ Task complete!")
                print(f"  Video ID: {video_id}")
                print(f"  Duration: {duration:.2f}s")
                
                return video_id, metadata
            
            # Still processing
            elif status in ['indexing', 'validating', 'processing', 'uploading']:
                pass  # Continue waiting
            
            # Failed
            elif status in ['failed', 'error']:
                print(f"\n❌ Task failed!")
                print(f"  Full response: {task_data}")
                raise Exception(f"Indexing failed with status: {status}")
            
            # Unknown status
            elif status is None or status not in ['ready', 'indexing', 'validating', 'processing', 'uploading']:
                print(f"\n  ⚠️ Unexpected status: {status}")
                print(f"  Full data: {task_data}")
            
        except Exception as e:
            print(f"\n  ❌ Error in wait loop: {e}")
            import traceback
            traceback.print_exc()
        
        time.sleep(10)
        attempt += 1
    
    # Timeout
    print(f"\n❌ Timeout: Video took longer than {max_attempts * 10 / 60:.0f} minutes")
    raise Exception("Video indexing timeout")

def check_index_details():
    """Check what engines are enabled on the index"""
    global index_id
    
    response = requests.get(
        f"{BASE_URL}/indexes/{index_id}",
        headers={"x-api-key": API_KEY}
    )
    
    if response.status_code == 200:
        index_info = response.json()
        print(f"\n🔍 Index Details:")
        print(f"Index ID: {index_id}")
        print(f"Name: {index_info.get('index_name')}")
        print(f"Models: {index_info.get('models')}")
        print(f"Engines: {index_info.get('engines')}")
        return index_info
    else:
        print(f"Could not get index info: {response.text}")
        return None

def get_video_transcript(video_id):
    """Get what conversation/audio was detected"""
    
    response = requests.get(
        f"{BASE_URL}/indexes/{index_id}/videos/{video_id}/transcription",
        headers={"x-api-key": API_KEY}
    )
    
    print(f"\n📝 Video Transcription:")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        transcript = response.json()
        print(f"Transcript data: {transcript}")
        return transcript
    else:
        print(f"No transcription available: {response.text}")
    
    return None

def search_video(query_text):
    """Search with better options and fallbacks"""
    global index_id
    
    search_headers = {"x-api-key": API_KEY}
    
    # Try multiple search strategies
    files = {
        'index_id': (None, index_id),
        'query_text': (None, query_text),
        'search_options': (None, 'visual'),
        'search_options': (None, 'audio'),
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
        result = response.json()
        all_results = result.get('data', [])
        
        print(f"✓ API returned {len(all_results)} results")
        
        # If no results, try visual only
        if len(all_results) == 0:
            print("  No results with conversation, trying visual only...")
            
            data_visual = [
                ('index_id', index_id),
                ('query_text', query_text),
                ('search_options', 'visual'),
                ('page_limit', '20')
            ]
            
            response = requests.post(f"{BASE_URL}/search", headers={"x-api-key": API_KEY}, files=data_visual)
            if response.status_code == 200:
                all_results = response.json().get('data', [])
                print(f"  Visual-only search found {len(all_results)} results")
        
        # Show all results with scores
        print(f"\n📊 Results breakdown:")
        for i, res in enumerate(all_results[:10]):
            start = res.get('start', 0)
            end = res.get('end', 0)
            score = res.get('score', 0)
            confidence = res.get('confidence', 'N/A')
            
            # Show what matched
            metadata = res.get('metadata', {})
            
            print(f"\n  Result {i+1}:")
            print(f"    Time: {start:.1f}s - {end:.1f}s ({end-start:.1f}s clip)")
            print(f"    Score: {score}")
            print(f"    Confidence: {confidence}")
            if metadata:
                print(f"    Match type: {metadata}")
        
        # Filter results - take ANY result, even with low scores
        # For CNN news, even low scores might be relevant
        return all_results[:5]  # Top 5 regardless of score
        
    else:
        print(f"Search failed: {response.status_code}")
        print(f"Response: {response.text}")
        return []

def search_video_semantic(query_text):
    """Try semantic search instead"""
    global index_id
    
    print(f"Trying semantic search for: '{query_text}'")
    
    search_headers = {"x-api-key": API_KEY}
    
    # Different endpoint format
    data = {
        'index_id': (None, index_id),
        'query': (None, query_text),
        'search_options': (None, 'visual'),
        'group_by': (None, 'video'),
        'threshold': (None, 'low'),
        'page_limit': (None, '10')
    }
    
    response = requests.post(
        f"{BASE_URL}/search",
        headers=search_headers,
        files=data
    )
    
    print(f"Response status: {response.status_code}")
    print(f"Response body: {response.text}")
    
    return response

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
        
        # delete_index()

        # Get or create index
        get_or_create_index()
        
        # Upload video
        task_id = upload_video(video_path)
        

        # After wait_for_task
        video_id, video_metadata = wait_for_task(task_id)
        idx = get_video_transcript(video_id) 

        # Show video details
        print(f"\n📹 Video Successfully Indexed:")
        print(f"  Video ID: {video_id}")
        print(f"  Duration: {video_metadata.get('duration', 0):.1f}s")
        print(f"  Filename: {video_metadata.get('filename')}")

        # get_video_info(video_id)
        
        # Search for relevant moments
        check_index_details()
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