import asyncio
import os
import uuid
from flask import Flask, request, jsonify, send_file, send_from_directory
import edge_tts

# Windows asyncio fix
if os.name == 'nt':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

app = Flask(__name__, static_folder='static')
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'outputs')
os.makedirs(OUTPUT_DIR, exist_ok=True)

VOICES = {
    "English (US)": [
        {"id": "en-US-AriaNeural",       "name": "Aria",        "gender": "Female", "style": "Conversational"},
        {"id": "en-US-JennyNeural",       "name": "Jenny",       "gender": "Female", "style": "Friendly"},
        {"id": "en-US-GuyNeural",         "name": "Guy",         "gender": "Male",   "style": "News"},
        {"id": "en-US-AnaNeural",         "name": "Ana",         "gender": "Female", "style": "Cute"},
        {"id": "en-US-ChristopherNeural", "name": "Christopher", "gender": "Male",   "style": "Reliable"},
        {"id": "en-US-EricNeural",        "name": "Eric",        "gender": "Male",   "style": "Rational"},
        {"id": "en-US-MichelleNeural",    "name": "Michelle",    "gender": "Female", "style": "Friendly"},
        {"id": "en-US-RogerNeural",       "name": "Roger",       "gender": "Male",   "style": "Lively"},
        {"id": "en-US-SteffanNeural",     "name": "Steffan",     "gender": "Male",   "style": "Narrative"},
    ],
    "English (UK)": [
        {"id": "en-GB-SoniaNeural",  "name": "Sonia",  "gender": "Female", "style": "Bright"},
        {"id": "en-GB-RyanNeural",   "name": "Ryan",   "gender": "Male",   "style": "Newscast"},
        {"id": "en-GB-LibbyNeural",  "name": "Libby",  "gender": "Female", "style": "Friendly"},
        {"id": "en-GB-MaisieNeural", "name": "Maisie", "gender": "Female", "style": "Cheerful"},
        {"id": "en-GB-ThomasNeural", "name": "Thomas", "gender": "Male",   "style": "Calm"},
    ],
    "English (AU)": [
        {"id": "en-AU-NatashaNeural", "name": "Natasha", "gender": "Female", "style": "Natural"},
        {"id": "en-AU-WilliamNeural", "name": "William", "gender": "Male",   "style": "Natural"},
    ],
    "Urdu (Pakistan)": [
        {"id": "ur-PK-AsadNeural", "name": "Asad", "gender": "Male",   "style": "Natural"},
        {"id": "ur-PK-UzmaNeural", "name": "Uzma", "gender": "Female", "style": "Natural"},
    ],
    "Hindi": [
        {"id": "hi-IN-SwaraNeural",  "name": "Swara",  "gender": "Female", "style": "Natural"},
        {"id": "hi-IN-MadhurNeural", "name": "Madhur", "gender": "Male",   "style": "Natural"},
    ],
    "Arabic": [
        {"id": "ar-SA-ZariyahNeural", "name": "Zariyah", "gender": "Female", "style": "Saudi"},
        {"id": "ar-SA-HamedNeural",   "name": "Hamed",   "gender": "Male",   "style": "Saudi"},
        {"id": "ar-EG-SalmaNeural",   "name": "Salma",   "gender": "Female", "style": "Egyptian"},
        {"id": "ar-EG-ShakirNeural",  "name": "Shakir",  "gender": "Male",   "style": "Egyptian"},
    ],
}

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/manifest.json')
def manifest():
    return send_from_directory('static', 'manifest.json')

@app.route('/sw.js')
def sw():
    return send_from_directory('static', 'sw.js')

@app.route('/api/voices')
def get_voices():
    return jsonify(VOICES)

@app.route('/api/generate', methods=['POST'])
def generate():
    data  = request.json or {}
    text  = (data.get('text') or '').strip()
    voice = data.get('voice', 'en-US-AriaNeural')
    rate  = data.get('rate', '+0%')
    pitch = data.get('pitch', '+0Hz')

    if not text:
        return jsonify({'error': 'Text khali hai!'}), 400
    if len(text) > 50000:
        return jsonify({'error': 'Text 50,000 characters se zyada hai!'}), 400

    filename = f"{uuid.uuid4()}.mp3"
    filepath = os.path.join(OUTPUT_DIR, filename)

    async def _gen():
        communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
        await communicate.save(filepath)

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_gen())
        loop.close()
    except Exception as e:
        return jsonify({'error': f'Generation failed: {str(e)}'}), 500

    if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
        return jsonify({'error': 'Audio generate nahi hua!'}), 500

    size = os.path.getsize(filepath)
    return jsonify({'file': filename, 'size': size, 'download_url': f'/api/download/{filename}'})

@app.route('/api/download/<filename>')
def download(filename):
    if not filename.endswith('.mp3') or '/' in filename or '..' in filename:
        return 'Not found', 404
    path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(path):
        return 'File not found', 404
    return send_file(path, as_attachment=True, download_name='voiceover.mp3', mimetype='audio/mpeg')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"\n✅ VoiceOver Studio chal raha hai!")
    print(f"🌐 Browser mein kholein: http://localhost:{port}\n")
    app.run(host='0.0.0.0', port=port, debug=False)
