import wave
import struct
import math
import requests
import time
import os

# 1. Generate dummy wav file (1 sec of 440Hz sine wave)
audio_path = "dummy_test.wav"
sample_rate = 44100
duration = 20.0  # 診断エンジンの最低要件（15秒）をパスするため20秒
freq = 440.0

with wave.open(audio_path, 'w') as f:
    f.setnchannels(1)
    f.setsampwidth(2)
    f.setframerate(sample_rate)
    
    for i in range(int(sample_rate * duration)):
        value = int(32767.0 * math.sin(2.0 * math.pi * freq * i / sample_rate))
        data = struct.pack('<h', value)
        f.writeframesraw(data)

print(f"Generated {audio_path}")

# 2. Upload to API
url = "http://localhost:8000/api/v1/audio/upload"
files = {'file': (audio_path, open(audio_path, 'rb'), 'audio/wav')}
data = {'user_name': 'TestUser', 'gender': 'unknown'}

print("Uploading to API...")
start_time = time.time()
response = requests.post(url, files=files, data=data)

if response.status_code == 200:
    res_data = response.json()
    print("Success!")
    print(f"Session ID: {res_data['session_id']}")
    print(f"Archetype: {res_data['archetype']['name']}")
    
    view_url = "http://localhost:8000" + res_data['report']['view_url']
    download_url = "http://localhost:8000" + res_data['report']['download_url']
    
    print(f"View URL: {view_url}")
    print(f"Download URL: {download_url}")
    
    # 3. Check View URL (HTML)
    r_view = requests.get(view_url)
    if r_view.status_code == 200 and "<html" in r_view.text:
        print("HTML View Endpoint: OK")
    else:
        print("HTML View Endpoint: FAILED")
        
    # 4. Check Download URL (PDF)
    r_dl = requests.get(download_url)
    if r_dl.status_code == 200 and r_dl.headers.get('content-type') == 'application/pdf':
        print(f"PDF Download Endpoint: OK ({len(r_dl.content)} bytes)")
        
        # Save the downloaded PDF to verify it's a real file
        with open("test_download.pdf", "wb") as f:
            f.write(r_dl.content)
        print("Saved test_download.pdf")
    else:
        print("PDF Download Endpoint: FAILED")
        
    print(f"Test finished in {time.time() - start_time:.2f} seconds.")
else:
    print(f"Error: {response.status_code}")
    print(response.text)

# Cleanup（watchfilesによるロックで失敗する場合は無視）
try:
    if os.path.exists(audio_path):
        os.remove(audio_path)
except PermissionError:
    pass  # サーバーのwatchfilesがファイルを監視中の場合は削除をスキップ
