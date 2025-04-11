import os
import logging
from openai import OpenAI, RateLimitError, APIConnectionError, APIError
from dotenv import load_dotenv
from llama_index.core import VectorStoreIndex, Settings
from llama_index.core.node_parser import SimpleNodeParser
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.readers.file import PDFReader
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.llms.openai import OpenAI
from httpx import HTTPStatusError

# Load environment variables from .env file
load_dotenv()

# Get OpenAI API key from environment variables
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    logging.warning("OpenAI API key not found in environment variables")

# Initialize OpenAI client with retries disabled
client = OpenAI(
    api_key=OPENAI_API_KEY,
    max_retries=0  # Disable retries
)

# Configure OpenAI embeddings with retries disabled
Settings.embed_model = OpenAIEmbedding(
    model="text-embedding-3-small",  # Using a smaller model to reduce token usage
    max_retries=0  # Disable retries
)

def process_pdf(pdf_path):
    """
    Process PDF file and create vector store index
    
    Parameters:
    pdf_path (str): Path to the PDF file
    
    Returns:
    VectorStoreIndex: Index created from the PDF content
    
    Raises:
    Exception: If there's an error processing the PDF
    """
    try:
        # First, check if the file exists and is readable
        if not os.path.exists(pdf_path):
            raise Exception("PDF file not found")
        
        # Check file size
        file_size = os.path.getsize(pdf_path)
        if file_size > 10 * 1024 * 1024:  # 10MB limit
            raise Exception("PDF file is too large (maximum 10MB)")
        
        # Read PDF file using PDFReader
        reader = PDFReader()
        documents = reader.load_data(file=pdf_path)
        
        # Check if we got any content
        if not documents or len(documents) == 0:
            raise Exception("No content found in PDF")
        
        # Chunk the document into smaller sections
        parser = SimpleNodeParser.from_defaults(chunk_size=512)
        nodes = parser.get_nodes_from_documents(documents)
        
        # Check if we got any nodes
        if not nodes or len(nodes) == 0:
            raise Exception("Could not extract text from PDF")
        
        # Create an index from chunked nodes
        index = VectorStoreIndex(nodes)
        
        return index
        
    except (RateLimitError, HTTPStatusError) as e:
        error_msg = "OpenAI API quota exceeded. Please check your billing details and current quota."
        logging.error(f"{error_msg} Error: {str(e)}")
        raise Exception(error_msg)
        
    except APIConnectionError as e:
        error_msg = "Failed to connect to OpenAI API. Please check your internet connection."
        logging.error(f"{error_msg} Error: {str(e)}")
        raise Exception(error_msg)
        
    except APIError as e:
        error_msg = "OpenAI API error. Please check your API key and billing status."
        logging.error(f"{error_msg} Error: {str(e)}")
        raise Exception(error_msg)
        
    except Exception as e:
        error_msg = f"Error processing PDF: {str(e)}"
        logging.error(error_msg)
        raise Exception(error_msg)

def get_answer_from_pdf(question, index):
    """
    Get answer to a question from PDF content using the stored index
    
    Parameters:
    question (str): The question to answer
    index (VectorStoreIndex): The pre-processed index of the PDF
    
    Returns:
    str: The answer to the question
    
    Raises:
    Exception: If there's an error getting the answer
    """
    try:
        # Create query engine from the index
        query_engine = index.as_query_engine()
        
        # Query the index
        response = query_engine.query(question)
        
        return str(response)
        
    except (RateLimitError, HTTPStatusError) as e:
        error_msg = "OpenAI API quota exceeded. Please check your billing details and current quota."
        logging.error(f"{error_msg} Error: {str(e)}")
        raise Exception(error_msg)
        
    except APIConnectionError as e:
        error_msg = "Failed to connect to OpenAI API. Please check your internet connection."
        logging.error(f"{error_msg} Error: {str(e)}")
        raise Exception(error_msg)
        
    except APIError as e:
        error_msg = "OpenAI API error. Please check your API key and billing status."
        logging.error(f"{error_msg} Error: {str(e)}")
        raise Exception(error_msg)
        
    except Exception as e:
        error_msg = f"Error getting answer: {str(e)}"
        logging.error(error_msg)
        raise Exception(error_msg)
