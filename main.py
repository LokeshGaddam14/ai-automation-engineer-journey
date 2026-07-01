import pandas as pd
from langchain_groq import ChatGroq
import os
import json
from dotenv import load_dotenv
api_key = os.getenv("LANGCHAIN_API_KEY")