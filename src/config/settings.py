from twilio.rest import Client
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

twilio_client = Client(
    os.environ["TWILIO_ACCOUNT_SID"],
    os.environ["TWILIO_AUTH_TOKEN"]
)

openai_client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"]
)

PINECONE_API_KEY = os.environ["PINECONE_API_KEY"]
PINECONE_NAMESPACE = os.environ.get("PINECONE_NAMESPACE", "default")