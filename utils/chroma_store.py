import chromadb
import logging
from datetime import datetime

class ChromaStore:
    def __init__(self):
        """Initialize ChromaDB client and collection"""
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.collection = self.client.get_or_create_collection(
            name="pdf_embeddings",
            metadata={"description": "Store PDF embeddings and related data"}
        )
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        logging.info("ChromaDB initialized successfully")

    def store_pdf_data(self, file_name, chunks, embeddings, metadata=None):
        """
        Store PDF data in ChromaDB
        
        Parameters:
        file_name (str): Name of the PDF file
        chunks (list): List of text chunks
        embeddings (list): List of embeddings for each chunk
        metadata (dict): Additional metadata about the PDF
        """
        try:
            # Generate unique IDs for each chunk
            ids = [f"{file_name}_{i}" for i in range(len(chunks))]
            
            # Get current timestamp
            timestamp = datetime.now().isoformat()
            
            # Prepare metadata for each chunk
            metadatas = [{
                "file_name": file_name,
                "chunk_index": i,
                "timestamp": timestamp,  # Same timestamp for all chunks of a file
                "total_chunks": len(chunks),
                "chunk_size": len(chunk)
            } for i, chunk in enumerate(chunks)]
            
            # Delete existing data for this file if it exists
            try:
                self.delete_file_data(file_name)
                logging.info(f"Deleted existing data for {file_name}")
            except Exception:
                pass  # Ignore if file doesn't exist
            
            # Store in ChromaDB
            self.collection.add(
                ids=ids,
                documents=chunks,
                embeddings=embeddings,
                metadatas=metadatas
            )
            logging.info(f"Successfully stored {len(chunks)} chunks for {file_name}")
            
        except Exception as e:
            logging.error(f"Error storing PDF data: {str(e)}")
            raise

    def get_similar_chunks(self, query_embedding, n_results=5, file_name=None):
        """
        Get similar chunks based on query embedding
        
        Parameters:
        query_embedding (list): Embedding vector for the query
        n_results (int): Number of similar chunks to return
        file_name (str, optional): Name of the PDF file to search within
        
        Returns:
        list: List of similar chunks with their metadata
        """
        try:
            # If file_name is provided, only search within that file's chunks
            where = {"file_name": file_name} if file_name else None
            
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where  # Filter by file_name if provided
            )
            
            # Format results
            similar_chunks = []
            for i in range(len(results['ids'][0])):
                similar_chunks.append({
                    'id': results['ids'][0][i],
                    'document': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i]
                })
            
            return similar_chunks
            
        except Exception as e:
            logging.error(f"Error getting similar chunks: {str(e)}")
            raise

    def get_file_chunks(self, file_name):
        """
        Get all chunks for a specific file
        
        Parameters:
        file_name (str): Name of the PDF file
        
        Returns:
        list: List of chunks with their metadata
        """
        try:
            results = self.collection.get(
                where={"file_name": file_name}
            )
            
            # Format results
            chunks = []
            for i in range(len(results['ids'])):
                chunks.append({
                    'id': results['ids'][i],
                    'document': results['documents'][i],
                    'metadata': results['metadatas'][i]
                })
            
            return chunks
            
        except Exception as e:
            logging.error(f"Error getting file chunks: {str(e)}")
            raise

    def delete_file_data(self, file_name):
        """
        Delete all data for a specific file
        
        Parameters:
        file_name (str): Name of the PDF file
        """
        try:
            self.collection.delete(
                where={"file_name": file_name}
            )
            logging.info(f"Successfully deleted data for {file_name}")
            
        except Exception as e:
            logging.error(f"Error deleting file data: {str(e)}")
            raise

    def list_available_pdfs(self):
        """
        List all available PDF documents with their metadata
        
        Returns:
        list: List of PDF documents with their metadata
        """
        try:
            # Get all documents from the collection
            results = self.collection.get()
            
            # If no documents exist, return empty list
            if not results or not results.get('metadatas') or len(results['metadatas']) == 0:
                logging.info("No PDFs found in ChromaDB")
                return []
                
            # Create a dictionary to store unique files with their metadata
            pdf_files = {}
            for metadata in results['metadatas']:
                file_name = metadata['file_name']
                if file_name not in pdf_files:
                    pdf_files[file_name] = {
                        'file_name': file_name,
                        'total_chunks': metadata['total_chunks'],
                        'upload_time': metadata['timestamp'],  # Use timestamp as upload time
                        'chunk_count': metadata['total_chunks']
                    }
            
            # Convert to list and sort by upload time (most recent first)
            pdf_list = list(pdf_files.values())
            pdf_list.sort(key=lambda x: x['upload_time'], reverse=True)
            
            logging.info(f"Found {len(pdf_list)} PDFs in ChromaDB")
            return pdf_list
            
        except Exception as e:
            logging.error(f"Error listing available PDFs: {str(e)}")
            raise

    def embeddings_exist(self, file_name: str) -> bool:
        """Check if embeddings exist for a file"""
        try:
            results = self.collection.get(
                where={"file_name": file_name},
                limit=1
            )
            return len(results['ids']) > 0
        except Exception as e:
            self.logger.error(f"Error checking embeddings existence: {str(e)}")
            return False

    def get_embeddings(self, file_name: str) -> dict:
        """Get embeddings and chunks for a file"""
        try:
            results = self.collection.get(
                where={"file_name": file_name}
            )
            return {
                'ids': results['ids'],
                'embeddings': results['embeddings'],
                'documents': results['documents'],
                'metadatas': results['metadatas']
            }
        except Exception as e:
            self.logger.error(f"Error getting embeddings: {str(e)}")
            return None 