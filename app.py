import os
import logging
from flask import Flask, render_template, request, jsonify, session
from werkzeug.utils import secure_filename
from utils.pdf_processor import process_pdf, get_answer_from_pdf
from openai import RateLimitError
from dotenv import load_dotenv
from utils.chroma_store import ChromaStore

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "your-secret-key-here")  # Required for session

# Configure upload settings
UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "./uploads")
ALLOWED_EXTENSIONS = set(os.environ.get("ALLOWED_EXTENSIONS", "pdf").split(','))

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get("MAX_CONTENT_LENGTH", 10 * 1024 * 1024))  # Default: 10MB

# Initialize ChromaStore
chroma_store = ChromaStore()

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
        logger.error("No file part in request")
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['pdfFile']
    
    # If user does not select file, browser also
    # submit an empty part without filename
    if file.filename == '':
        logger.error("No file selected")
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        try:
            logger.info(f"Processing file: {file.filename}")
            
            # First, validate the file size
            file_size = len(file.read())
            file.seek(0)  # Reset file pointer
            
            logger.info(f"File size: {file_size} bytes ({file_size / (1024 * 1024):.2f} MB)")
            
            if file_size > app.config['MAX_CONTENT_LENGTH']:
                logger.error(f"File too large: {file_size} bytes ({file_size / (1024 * 1024):.2f} MB)")
                return jsonify({
                    'error': f'File too large. Maximum size is {app.config["MAX_CONTENT_LENGTH"] / (1024 * 1024):.1f}MB',
                    'status': 'error'
                }), 400
            
            # Save the file temporarily
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            logger.info(f"File saved to: {filepath}")
            
            try:
                # Process PDF and create index
                logger.info("Starting PDF processing...")
                index = process_pdf(filepath)
                logger.info("PDF processed successfully")
                
                # Store the filepath in session and index in global variable
                session['current_pdf_path'] = filepath
                print ("index on upload", index)
                current_index = index
                logger.info("PDF path and index stored")
                
                return jsonify({
                    'success': True, 
                    'message': 'PDF processed successfully',
                    'status': 'completed'
                })
            except RateLimitError as e:
                logger.error(f"Rate limit error: {str(e)}")
                # Clean up the file if processing fails
                if os.path.exists(filepath):
                    os.remove(filepath)
                return jsonify({
                    'error': 'OpenAI API quota exceeded. Please try again later or check your billing details.',
                    'status': 'rate_limit'
                }), 429
            except Exception as e:
                logger.error(f"Error processing PDF: {str(e)}")
                # Clean up the file if processing fails
                if os.path.exists(filepath):
                    os.remove(filepath)
                raise e
                
        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            # Clean up any temporary files
            if 'filepath' in locals() and os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({
                'error': f'Error processing PDF: {str(e)}',
                'status': 'error'
            }), 500
    else:
        logger.error(f"Invalid file type: {file.filename if file else 'No file'}")
        return jsonify({
            'error': 'File type not allowed. Please upload a PDF.',
            'status': 'error'
        }), 400

@app.route('/ask', methods=['POST'])
def ask_question():
    global current_index
    
    data = request.get_json()
    question = data.get('question')
    
    logger.info(f"Received question: {question}")
    
    if not question:
        logger.error("No question provided")
        return jsonify({'error': 'No question provided'}), 400
    
    # Get the PDF path from session
    pdf_path = session.get('current_pdf_path')
    if not pdf_path:
        logger.error("No PDF path in session")
        return jsonify({'error': 'No PDF content available. Please upload a PDF first.'}), 400
    
    try:
        logger.info(f"PDF path from session: {pdf_path}")
        file_name = os.path.basename(pdf_path)
        
        current_index = process_pdf(pdf_path)
        logger.info("Index recreated successfully")
        
        # Get answer using the index and file name
        logger.info("Getting answer from PDF...")
        answer = get_answer_from_pdf(question, current_index, file_name)
        logger.info("Answer generated successfully")
        
        return jsonify({'answer': answer})
        
    except Exception as e:
        logger.error(f"Error getting answer: {str(e)}")
        return jsonify({'error': f'Error getting answer: {str(e)}'}), 500

@app.route('/list-pdfs', methods=['GET'])
def list_pdfs():
    try:
        pdfs = chroma_store.list_available_pdfs()
        return jsonify(pdfs)
    except Exception as e:
        logger.error(f"Error listing PDFs: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/load-pdf', methods=['POST'])
def load_pdf():
    try:
        file_name = request.json.get('file_name')
        if not file_name:
            logger.error("No file name provided")
            return jsonify({'error': 'No file name provided'}), 400
        
        # Check if file exists
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_name)
        if not os.path.exists(file_path):
            logger.error(f"PDF file not found: {file_path}")
            return jsonify({'error': 'PDF file not found'}), 404
        
        # Store file path in session
        session['current_pdf_path'] = file_path
        logger.info(f"PDF loaded into session: {file_name}")
        
        # Process PDF and create index
        try:
            logger.info("Processing PDF...")
            current_index = process_pdf(file_path)
            logger.info("PDF processed successfully")
            return jsonify({'message': 'PDF loaded successfully'})
            
        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            return jsonify({'error': str(e)}), 500
            
    except Exception as e:
        logger.error(f"Error loading PDF: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/delete-pdf', methods=['POST'])
def delete_pdf():
    try:
        file_name = request.json.get('file_name')
        if not file_name:
            logger.error("No file name provided")
            return jsonify({'error': 'No file name provided'}), 400
        
        # Delete from ChromaDB
        chroma_store.delete_file_data(file_name)
        logger.info(f"Deleted PDF data from ChromaDB: {file_name}")
        
        # Delete the file if it exists
        file_path = os.path.join('uploads', file_name)
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Deleted PDF file: {file_path}")
        
        # Clear session if the deleted file was the current one
        if session.get('current_pdf_path') == file_path:
            session.pop('current_pdf_path', None)
            logger.info("Cleared PDF path from session")
        
        return jsonify({'message': 'PDF deleted successfully'})
    except Exception as e:
        logger.error(f"Error deleting PDF: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
