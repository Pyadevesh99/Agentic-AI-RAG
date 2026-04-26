import boto3
import os


class s3_Bucket_Helper:
    def __init__(self):

        self.bucket_name = os.getenv("AWS_BUCKET_NAME")
        self.s3_client = boto3.client("s3",region_name="ap-south-1")

    def upload_file(self, file_name, file_content):
        # Upload the file to S3
        self.s3_client.put_object(
        Bucket = self.bucket_name,
        Key = file_name,
        Body = file_content,
        ContentType = "application/pdf"
        )
        return f"file {file_name} uploaded Sucessfully"


    def download_file(self,file_name):

        """
        Download the file from S3
        """
        try:
            self.s3_client.download_file(
                Bucket = self.bucket_name,
                key = self.file_name,
                Filename = "./downloads/" + self.file_name
            )
            return " File Downloaded from S3: " + "./downloads/" + self.file_name

        except Exception as e:
            print(f"Error downloading file from S3: {str(e)}")
            raise e
            
            


    
