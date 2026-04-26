import os
import psycopg2
import requests
from db_helper_method import db_helper_method
from langchain_community.embeddings import HuggingFaceEmbeddings

class RagAgent:
    def __init__(self):
        self.dbUrl = ""
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    def get_db_connection(self):
        db_helper_service = db_helper_method()
        self.dbUrl = db_helper_service.getDb_ConnectionstringfromAWSSecret()
        return self.dbUrl

    def retreiveContext(self,ques: str, numChunks: int = 3) -> str:
        try:
            # Connect to the database
            self.get_db_connection()
            # Convert the question to a vector
            ques_vector = self.embeddings.embed_query(ques)
            # Connect to the database
            connection = psycopg2.connect(self.dbUrl)
            cursor_db = connection.cursor()
            # Retrieve the top k similar documents
            try:
                query = """ Select "content" 
                from documents order by embedding <-> %s::vector limit %s
                """

                cursor_db.execute(query,(ques_vector,numChunks))
                results = cursor_db.fetchall()
                context = "\n\n".join([row[0] for row in results])
                return context
            finally:
                if cursor_db:
                    cursor_db.close()
                if connection:
                    connection.close()
            
        except Exception as e:
            raise e

    
    def generateAnswer(self,ques: str) -> str:
        try:
            # Get the context from  the vector database
            context = self.retreiveContext(ques)
            
            # Setup the Groq API using OpenAI compatible endpoint
            groq_api_Key = os.getenv("GROQ_API_KEY")           

            url = "https://api.groq.com/openai/v1/chat/completions"

            headers = {
                "Authorization": f"Bearer {groq_api_Key}",
                "Content-Type": "application/json"
            }

            prompt = f"Use the following context to answer the question: {context}\n\nQuestion: {ques}"
            
            payload ={
                "model" : "llama-3.1-8b-instant",
                "messages" : [
                    {"role" : "system", "content" : "You are a strict technical assistant. You must answer the user's question using ONLY the provided context from the Vector Database. If the context does not contain the information needed to answer the question, you must respond exactly with: 'I am sorry, but the answer to your question is not available in the provided database.' Do not use outside knowledge."},
                    {"role" : "user", "content" : prompt}
                ],
                
                #"temperature" : 0.7,
            }

            # Make the Api call to model
            response = requests.post(url,headers= headers,json = payload)

            if response.status_code == 200:
                responseData = response.json()
                return responseData["choices"][0]["message"]["content"]
            else:
                raise Exception(f"Error from Groq API: {response.status_code} - {response.text}")


        except Exception as e:
            raise e

