import io
from pydantic.deprecated import json
from fastapi import Depends
from fastapi import Security
from RagAgent import RagAgent
from fastapi import Body
import os
from fastapi import FastAPI, UploadFile, HTTPException
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from s3_BuckerHelper import s3_Bucket_Helper
from AwsSecretHelper import AwsSecretHelper
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
from db_helper_method import db_helper_method
import jwt
import boto3
import json

# 1. LOAD THE SECRETS
# This line goes looking for your .env file and secretly loads the AWS keys and Grok key
# into your computer's memory so we can use them safely.
load_dotenv()

#create the bearer token detector
security = HTTPBearer()

# Verify the JWT token method using Token

def verify_Token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        Aws_Secret_helper = AwsSecretHelper()
        secret_value = Aws_Secret_helper.get_Secret("JWTSecrets")
        secret_dict = json.loads(secret_value)
        Jwt_Key = secret_dict.get("JWT_SECRET_KEY")
        Jwt_Issuer = secret_dict.get("JWT_ISSUER")
        Jwt_Audienece = secret_dict.get("JWT_AUDIENCE")
        payload = jwt.decode(token,Jwt_Key,algorithms=["HS256"],issuer=Jwt_Issuer,audience=Jwt_Audienece)
        
        return payload
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Exception {str(e)}")

# 2. CREATE THE APP
# This creates the actual FastAPI server instance. This 'app' variable is what Uvicorn runs.
app = FastAPI(title="Grok RAG Agent API")

origins = ["*"]  # allow all (for development)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. CREATE THE AMAZON S3 CONNECTION
# boto3 is the official library to talk to AWS. 
# We tell it we want to talk to the 's3' service. 
# It will automatically find your AWS_ACCESS_KEY that load_dotenv() just loaded.
s3_client = boto3.client('s3', region_name='ap-south-1') 

# Get your bucket name from the .env file so we don't have to hardcode it in the script
BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")

# 4. CREATE A SIMPLE TEST ROUTE
# When you visit the base URL of your API, it will return a welcome JSON message.
@app.get("/test")
def read_root():
    return {"message": "Welcome to the Grok RAG API!"}



# Creating API End Point for uploading the Pdf file

@app.post("/upload-pdf", dependencies=
[Depends(verify_Token)])
async def upload_pdf(file: UploadFile):
    try:
        # Check If File name ends with .pdf
        if not file.filename.endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Invalid File type Pdf Only Upload")
        
        # Reda the file
        content = await file.read()


        # Use Our Connected Client to put the Object into S3 bucket

        s3_helper_Bucket = s3_Bucket_Helper()
        s3_helper_Bucket.upload_file(file_name=file.filename, file_content=content)

        # Store Convert pdf into chunks to db 

        dbHelpermethod = db_helper_method()



        dbHelpermethod.process_pdf_and_Save_To_vector_Db(content)


        return HTTPException(status_code=200, detail=f"File {file.filename} uploaded successfully")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@app.post("/download_pdf",dependencies=
[Depends(verify_Token)])
async def download_pdf(filename : str):
    try:
        s3_helper_Bucket = s3_Bucket_Helper()
        Download_Response= s3_helper_Bucket.download_file(filename)
        if Download_Response:
            return HTTPException(status_code=200, detail=f"File {filename} downloaded sucessfully")
        else:
            return HTTPException(status_code=404, detail=f"File {filename} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f" Exception {str(e)}")


@app.post("/get_secret",dependencies=
[Depends(verify_Token)])
async def get_secret(secret : str):
    try:
        aws_secret_helper = aws_secret_helper()
        secret_value = aws_secret_helper.get_Secret(secret)
        return HTTPException(status_code=200, detail=f"Secret{secret} retreived sucessfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Exception getting while retreving secret {str(e)}")


@app.post("/ask-question",dependencies=[
    Depends(verify_Token)
])
async def ask_question(question : str):
    try:
        rag_agent = RagAgent()
        answer = rag_agent.generateAnswer(question)
        return HTTPException(status_code=200, detail=f"Answer: {answer}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Exception getting while retreving answer {str(e)}")