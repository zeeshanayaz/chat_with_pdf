import os
import PyPDF2
import logging
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get OpenAI API key from environment variables
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    logging.warning("OpenAI API key not found in environment variables")

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

def extract_text_from_pdf(pdf_path):
    """
    Extract text from a PDF file
    
    Parameters:
    pdf_path (str): Path to the PDF file
    
    Returns:
    str: Extracted text from the PDF
    """
    text = ""
    
    # Open the PDF file
    with open(pdf_path, 'rb') as file:
        # Create a PDF reader object
        pdf_reader = PyPDF2.PdfReader(file)
        
        # Get the number of pages in the PDF
        num_pages = len(pdf_reader.pages)
        
        # Extract text from each page
        for page_num in range(num_pages):
            page = pdf_reader.pages[page_num]
            text += page.extract_text()
    
    return text

def chunk_text(text, chunk_size=4000, overlap=200):
    """
    Split text into chunks of specified size with overlap
    
    Parameters:
    text (str): Text to chunk
    chunk_size (int): Maximum chunk size
    overlap (int): Number of characters to overlap between chunks
    
    Returns:
    list: List of text chunks
    """
    chunks = []
    start = 0
    
    while start < len(text):
        end = min(start + chunk_size, len(text))
        
        # Ensure we're not cutting in the middle of a word
        if end < len(text):
            # Find the last space before the end
            while end > start and text[end] != ' ':
                end -= 1
            
            if end == start:  # No space found, use the original end
                end = min(start + chunk_size, len(text))
        
        chunks.append(text[start:end])
        
        # Move start position for next chunk, considering overlap
        start = end - overlap if end < len(text) else len(text)
    
    return chunks

def get_answer_from_openai(pdf_text, question):
    """
    Get an answer from OpenAI based on the PDF text and question
    
    Parameters:
    pdf_text (str): Text extracted from PDF
    question (str): User's question
    
    Returns:
    str: Answer from OpenAI
    """
    # Check if API key is available
    if not OPENAI_API_KEY:
        return "Error: OpenAI API key not found. Please set the OPENAI_API_KEY environment variable."
    
    # Chunk the text to fit within token limits
    chunks = chunk_text(pdf_text)
    
    # Create a context from the chunks - use only the first few chunks to stay within token limits
    # In a more advanced implementation, we would use embeddings to find relevant chunks
    context = "\n\n".join(chunks[:3])
    
    # Truncate if still too long
    if len(context) > 10000:
        context = context[:10000] + "..."
    
    # Create the prompt for OpenAI
    prompt = f"""
    You are an assistant that answers questions based on the provided PDF content.
    
    PDF CONTENT:
    {context}
    
    USER QUESTION:
    {question}
    
    Your task is to answer the user's question based ONLY on the information provided in the PDF content.
    If the answer cannot be found in the PDF content, politely state that the information is not available in the provided document.
    """
    
    try:
        # Get the response from OpenAI
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Using GPT-4o-mini for efficiency and cost
            messages=[
                {"role": "system", "content": "You are a helpful assistant that answers questions based on PDF content."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000
        )
        
        # Extract the answer from the response
        answer = response.choices[0].message.content
        
        return answer
    except Exception as e:
        return f"Error: Failed to get answer from OpenAI: {str(e)}"
