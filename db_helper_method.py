import psycopg2
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
import uuid
import json
from AwsSecretHelper import AwsSecretHelper

class db_helper_method:
    def __init__(self):
        self.db_Url = ""
        # FIX: Actually assign HuggingFaceEmbeddings to the variable!
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    def getDb_ConnectionstringfromAWSSecret(self):
        try:
            Aws_Secret_Helper = AwsSecretHelper()
            raw_Secret_string = Aws_Secret_Helper.get_Secret("VECTORDBConnection")
            db_ConnectionVector = json.loads(raw_Secret_string)
            username = db_ConnectionVector.get("username")
            databaseName = db_ConnectionVector.get("dbname")
            password = db_ConnectionVector.get("password")
            host = db_ConnectionVector.get("host")
            port = db_ConnectionVector.get("port")
            self.db_Url = f"postgresql://{username}:{password}@{host}:{port}/{databaseName}"
            return self.db_Url
            
        except Exception as e:
            raise e

    def process_pdf_and_Save_To_vector_Db(self, file_content: bytes):
        try:
            import io
            from pypdf import PdfReader
            from langchain_core.documents import Document

            # 1. Load the PDF into memory from the raw bytes!
            virtual_file = io.BytesIO(file_content)
            pdf_reader = PdfReader(virtual_file)
            
            # 2. Extract into Langchain Documents
            Pages = []
            for text_page in pdf_reader.pages:
                Pages.append(Document(page_content=text_page.extract_text()))

            # 2. Break pdf into chunks (FIXED: chunk_size and chunk_overlap must be fully lowercase!)
            textSplitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
            textChunks = textSplitter.split_documents(Pages)

            # 3. Extract just the raw text strings from the chunks (FIXED: must be chunk.page_content)
            content_strings = [chunk.page_content for chunk in textChunks]

            if not content_strings:
                raise Exception("Could not extract any text from the PDF. It might be a scanned image or the format is unsupported by pypdf.")

            # 4. Convert all text strings to numbers
            vectorChunkList = self.embeddings.embed_documents(content_strings)

            # 5. Connect to Postgres
            # FIX: We have to actually FETCH the URL from AWS before we connect!
            if not self.db_Url:
                self.getDb_ConnectionstringfromAWSSecret()
                
            connection = psycopg2.connect(self.db_Url)
            cursor_db = connection.cursor()

            # 6. Insert ALL chunks
            for i in range(len(content_strings)):
                chunkId = str(uuid.uuid4())
                Content = content_strings[i]
                vector = vectorChunkList[i]
                
                # Check if pgvector is enabled, psycopg2 needs lists to be cast to vector type explicitly
                # otherwise you might get 'can't adapt type list' errors.
                # If you haven't run register_vector(), you can insert with ::vector cast:
                cursor_db.execute(
                    "INSERT INTO Documents (content, embedding) VALUES (%s, %s::vector)",
                    ( Content, vector)
                )

            # 7. FIX: We must commit and close AFTER the loop finishes, not inside the loop!
            connection.commit()
            cursor_db.close()
            connection.close()

            print(f"Successfully Saved {len(content_strings)} Chunks to Vector DB")
            return True

        except Exception as e:
            raise e
