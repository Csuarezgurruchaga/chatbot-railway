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

# Guardrails configurables
ENABLE_INPUT_MODERATION = os.environ.get("ENABLE_INPUT_MODERATION", "false").lower() == "true"
ENABLE_TOPIC_VALIDATION = os.environ.get("ENABLE_TOPIC_VALIDATION", "true").lower() == "true"
ENABLE_OUTPUT_MODERATION = os.environ.get("ENABLE_OUTPUT_MODERATION", "false").lower() == "true"