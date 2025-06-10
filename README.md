# ChatWithPDF 🧠📄

ChatWithPDF is a Python and web-based application that allows users to upload a PDF file and interact with it using natural language queries. This project uses AI to understand and retrieve relevant information from the PDF documents, making reading and extracting insights easier and faster.

## 🚀 Features

- Upload and parse PDF files
- Ask questions in natural language
- Get accurate and context-aware answers from the uploaded PDF
- User-friendly web interface

  ## 🛠️ Tech Stack

- **Backend:** Python, LangChain, PyPDF2/pdfplumber, OpenAI (or any LLM)
- **Frontend:** HTML/CSS/JavaScript or Flask
- **Others:** FAISS or ChromaDB for semantic search, OpenAI API

## 📦 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/chat_with_pdf.git
cd chat_with_pdf
```

### 2. Setup Virtual Environment
```bash
# Creating Virtual Environment as myenv
pip install virtualenv
virtualenv myenv
myenv\Scripts\activate.bat
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Create .env File
Create a file named .env in the root directory and add the following content:
```bash
# Environment variables for PDF Question Answering app

# API Keys
OPENAI_API_KEY=API-KEY

# Application settings
DEBUG=True
MAX_CONTENT_LENGTH=16777216  # 16MB max upload size
UPLOAD_FOLDER=./uploads
ALLOWED_EXTENSIONS=pdf
```
⚠️ Replace API-KEY with your actual OpenAI API key.

### 5. Run the App
```bash
python main.py
```
Then open your browser at http://localhost:8080 depending on your framework.


