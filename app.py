import os
import logging
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from utils.pdf_processor import extract_text_from_pdf, get_answer_from_openai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG if os.environ.get("DEBUG", "False").lower() == "true" else logging.INFO)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

# Configure upload settings
UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "./uploads")
ALLOWED_EXTENSIONS = set(os.environ.get("ALLOWED_EXTENSIONS", "pdf").split(','))

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))  # Default: 16MB

# Check if file has an allowed extension
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    # Check if the post request has the file part
    if 'pdfFile' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['pdfFile']
    
    # If user does not select file, browser also
    # submit an empty part without filename
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        try:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Extract text from PDF
            pdf_text = extract_text_from_pdf(filepath)
            
            # Clean up - remove the file after processing
            os.remove(filepath)
            
            return jsonify({'success': True, 'text': pdf_text})
        except Exception as e:
            logging.error(f"Error processing PDF: {str(e)}")
            return jsonify({'error': f'Error processing PDF: {str(e)}'}), 500
    else:
        return jsonify({'error': 'File type not allowed. Please upload a PDF.'}), 400

@app.route('/ask', methods=['POST'])
def ask_question():
    try:
        data = request.get_json()
        
        if not data or 'question' not in data or 'pdfText' not in data:
            return jsonify({'error': 'Missing question or PDF text'}), 400
        
        question = data['question']
        pdf_text = data['pdfText']
        
        # Get answer from OpenAI
        answer = get_answer_from_openai(pdf_text, question)
        
        return jsonify({'answer': answer})
    except Exception as e:
        logging.error(f"Error getting answer: {str(e)}")
        return jsonify({'error': f'Error getting answer: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
