import os
import dashscope
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("DASHSCOPE_API_KEY")
print(f"Key loaded: {api_key[:10]}...{api_key[-10:] if api_key else 'None'}")
print(f"Key length: {len(api_key) if api_key else 0}")

dashscope.base_http_api_url = 'https://ws-qhebnre9dgsdfa13.ap-southeast-1.maas.aliyuncs.com/api/v1'
dashscope.api_key = api_key

from langchain_community.llms import Tongyi
llm = Tongyi(model="qwen-max", temperature=0.1, dashscope_api_key=api_key)

try:
    print("Testing invoke...")
    print(llm.invoke("Test"))
except Exception as e:
    print("Error:", type(e).__name__, e)
