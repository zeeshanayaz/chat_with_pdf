import os
import logging
from openai import OpenAI, RateLimitError, APIConnectionError, APIError
from dotenv import load_dotenv
from llama_index.core import VectorStoreIndex, Settings, SimpleDirectoryReader, Document, ServiceContext
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.readers.file import PDFReader
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.llms.openai import OpenAI as LlamaOpenAI
from httpx import HTTPStatusError
from utils.chroma_store import ChromaStore
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get OpenAI API key from environment variables
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    logging.warning("OpenAI API key not found in environment variables")

# Initialize OpenAI client with no retries
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    max_retries=0  # Disable retries to show errors immediately
)

# Configure settings
Settings.embed_model = OpenAIEmbedding(
    model="text-embedding-3-small",
    api_key=os.environ.get("OPENAI_API_KEY"),
    max_retries=0  # Disable retries for embeddings too
)

# Initialize LlamaIndex OpenAI client with no retries
llm = LlamaOpenAI(
    model="gpt-3.5-turbo",
    temperature=0.1,
    api_key=os.environ.get("OPENAI_API_KEY"),
    max_retries=0  # Disable retries for completions too
)
Settings.llm = llm

# Initialize ChromaDB
chroma_store = ChromaStore()

def process_pdf(pdf_path: str) -> VectorStoreIndex:
    """Process PDF and return index"""
    try:
        file_name = os.path.basename(pdf_path)
        
        # Check if embeddings already exist
        if chroma_store.embeddings_exist(file_name):
            logging.info(f"Embeddings already exist for {file_name} in ChromaDB")
            return None  # Return None to indicate embeddings exist
            
        logging.info(f"Creating new embeddings for {file_name}")
        # Load and process PDF
        documents = SimpleDirectoryReader(input_files=[pdf_path]).load_data()
        
        # Create index with embeddings
        index = VectorStoreIndex.from_documents(
            documents,
            service_context=ServiceContext.from_defaults(
                embed_model=Settings.embed_model
            )
        )
        
        # Get embeddings and chunks
        nodes = list(index.docstore.docs.values())
        if not nodes:
            raise Exception("No nodes found in the index")
            
        embeddings = []
        chunks = []
        metadatas = []
        
        for i, node in enumerate(nodes):
            # Get embedding for the node text
            embedding = Settings.embed_model.get_text_embedding(node.text)
            embeddings.append(embedding)
            chunks.append(node.text)
            metadatas.append({
                "file_name": file_name,
                "chunk_index": i,
                "timestamp": datetime.now().isoformat(),
                "total_chunks": len(nodes),
                "chunk_size": len(node.text)
            })
        
        if not embeddings:
            raise Exception("No embeddings generated")
            
        # Store in ChromaDB
        chroma_store.store_pdf_data(
            file_name=file_name,
            chunks=chunks,
            embeddings=embeddings,
            metadata=metadatas
        )
        
        return index
        
    except Exception as e:
        logging.error(f"Error processing PDF: {str(e)}")
        raise

def get_answer_from_pdf(question, index=None, file_name=None):
    """
    Get answer to a question from PDF content using the stored embeddings in ChromaDB
    
    Parameters:
    question (str): The question to answer
    index (VectorStoreIndex, optional): The pre-processed index of the PDF
    file_name (str, optional): Name of the PDF file if using stored embeddings
    
    Returns:
    str: The answer to the question
    
    Raises:
    Exception: If there's an error getting the answer
    """
    try:
        logger.info(f"Getting answer for question: {question}")
        
        # Get embeddings for the question
        logger.info("Creating question embedding...")
        question_embedding = Settings.embed_model.get_text_embedding(question)
        
        # If file_name is provided, use stored embeddings from ChromaDB
        if file_name:
            logger.info(f"Using stored embeddings for file: {file_name}")
            # Get similar chunks from ChromaDB
            similar_chunks = chroma_store.get_similar_chunks(question_embedding, n_results=3)
            if not similar_chunks or len(similar_chunks) == 0:
                raise Exception("No relevant content found in PDF")
            
            # Create context from similar chunks
            context = "\n\n".join([chunk['document'] for chunk in similar_chunks])
            logger.info(f"Retrieved {len(similar_chunks)} relevant chunks from ChromaDB")
            
            # Create a simple index from the context
            from llama_index.core import Document
            doc = Document(text=context)
            index = VectorStoreIndex.from_documents([doc])
        
        # If index is provided, use it directly
        elif index:
            logger.info("Using provided index for querying")
            # Get similar chunks from ChromaDB
            similar_chunks = chroma_store.get_similar_chunks(question_embedding, n_results=3)
            if not similar_chunks or len(similar_chunks) == 0:
                raise Exception("No relevant content found in PDF")
            
            # Create context from similar chunks
            context = "\n\n".join([chunk['document'] for chunk in similar_chunks])
            logger.info(f"Retrieved {len(similar_chunks)} relevant chunks")
        
        else:
            raise Exception("Either index or file_name must be provided")
        
        # Create query engine with the context
        logger.info("Creating query engine...")
        query_engine = index.as_query_engine()
        
        # Query with the context
        logger.info("Querying with context...")
        response = query_engine.query(f"Context: {context}\n\nQuestion: {question}")
        
        if not response or str(response).strip() == "":
            raise Exception("No answer could be generated from the PDF content")
            
        logger.info("Answer generated successfully")
        return str(response)
        
    except (RateLimitError, HTTPStatusError) as e:
        error_msg = "OpenAI API quota exceeded. Please check your billing details and current quota."
        logger.error(f"{error_msg} Error: {str(e)}")
        raise Exception(error_msg)
        
    except APIConnectionError as e:
        error_msg = "Failed to connect to OpenAI API. Please check your internet connection."
        logger.error(f"{error_msg} Error: {str(e)}")
        raise Exception(error_msg)
        
    except APIError as e:
        error_msg = "OpenAI API error. Please check your API key and billing status."
        logger.error(f"{error_msg} Error: {str(e)}")
        raise Exception(error_msg)
        
    except Exception as e:
        error_msg = f"Error getting answer: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)
