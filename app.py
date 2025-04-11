import os
import logging
from flask import Flask, render_template, request, jsonify, session
from werkzeug.utils import secure_filename
from utils.pdf_processor import process_pdf, get_answer_from_pdf
from openai import RateLimitError
from dotenv import load_dotenv
from flask_session import Session

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
app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get("MAX_CONTENT_LENGTH", 10 * 1024 * 1024))  # Default: 10MB
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "your-secret-key-here")  # Required for session
app.config['SESSION_TYPE'] = 'filesystem'  # Store sessions on filesystem
app.config['SESSION_FILE_DIR'] = os.path.join(os.getcwd(), 'flask_session')  # Store session files in a dedicated directory

# Create session directory if it doesn't exist
os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)

# Initialize session
Session(app)

# Global variable to store the index
current_index = None

# Check if file has an allowed extension
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    global current_index
    
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
            # First, validate the file size
            file_size = len(file.read())
            file.seek(0)  # Reset file pointer
            
            if file_size > app.config['MAX_CONTENT_LENGTH']:
                return jsonify({
                    'error': f'File too large. Maximum size is {app.config["MAX_CONTENT_LENGTH"] / (1024 * 1024):.1f}MB',
                    'status': 'error'
                }), 400
            
            # Save the file temporarily
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            try:
                # Process PDF and create index
                index = process_pdf(filepath)
                
                # Store the filepath in session and index in global variable
                session['current_pdf_path'] = filepath
                current_index = index
                
                return jsonify({
                    'success': True, 
                    'message': 'PDF processed successfully',
                    'status': 'completed'
                })
            except RateLimitError as e:
                # Clean up the file if processing fails
                if os.path.exists(filepath):
                    os.remove(filepath)
                return jsonify({
                    'error': 'OpenAI API quota exceeded. Please try again later or check your billing details.',
                    'status': 'rate_limit'
                }), 429
            except Exception as e:
                # Clean up the file if processing fails
                if os.path.exists(filepath):
                    os.remove(filepath)
                raise e
                
        except Exception as e:
            logging.error(f"Error processing PDF: {str(e)}")
            # Clean up any temporary files
            if 'filepath' in locals() and os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({
                'error': f'Error processing PDF: {str(e)}',
                'status': 'error'
            }), 500
    else:
        return jsonify({
            'error': 'File type not allowed. Please upload a PDF.',
            'status': 'error'
        }), 400

@app.route('/ask', methods=['POST'])
def ask_question():
    global current_index
    
    data = request.get_json()
    question = data.get('question')
    
    if not question:
        return jsonify({'error': 'No question provided'}), 400
    
    # Get the PDF path from session
    pdf_path = session.get('current_pdf_path')
    if not pdf_path:
        return jsonify({'error': 'No PDF content available. Please upload a PDF first.'}), 400
    
    try:
        # Use the global index
        if not current_index:
            # If index is not available, recreate it
            current_index = process_pdf(pdf_path)
        
        # Get answer using the index
        answer = get_answer_from_pdf(question, current_index)
        return jsonify({'answer': answer})
        
    except Exception as e:
        logging.error(f"Error getting answer: {str(e)}")
        return jsonify({'error': f'Error getting answer: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
