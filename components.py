import os
import base64
from mistralai import Mistral
from openai import OpenAI
from sparknlp.pretrained import PretrainedPipeline
from mcp.server.fastmcp import FastMCP
from duckduckgo_search import DDGS
from dotenv import load_dotenv
import json

load_dotenv()


model = 'openai/gpt-oss-120b'

mistral_client = Mistral(api_key='rcf0Mx1SCubHeUgdGQGaML5Jnb5ew0Au')

gclient = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key="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"
)

mcp = FastMCP("Medical Tools")


@mcp.tool()
def ocr(pdf_path_or_link: str):
    """Extract text from a given PDF path or mistral PDF link."""
    if pdf_path_or_link.startswith("http://") or pdf_path_or_link.startswith("https://"):
        signed_url = pdf_path_or_link
    else:
        uploaded_pdf = mistral_client.files.upload(
            file={
                "file_name": "uploaded_file.pdf",
                "content": open(pdf_path_or_link, "rb"),
            },
            purpose="ocr"
        )
        signed_url = mistral_client.files.get_signed_url(file_id=uploaded_pdf.id)
        print(signed_url)

    ocr_response = mistral_client.ocr.process(
        model="mistral-ocr-latest",
        document={
            "type": "document_url",
            "document_url": signed_url.url
        },
        include_image_base64=True
    )

    response = ''
    for page in ocr_response.pages:
        response += "\n" + page.markdown
    return response


@mcp.tool()
def document_question(pdf_path_or_link: str, user_query: str):
    """Answers user_query by retrieving content from the PDF."""
    if pdf_path_or_link.startswith("http://") or pdf_path_or_link.startswith("https://"):
        signed_url = pdf_path_or_link
    else:
        uploaded_pdf = mistral_client.files.upload(
            file={
                "file_name": "uploaded_file.pdf",
                "content": open(pdf_path_or_link, "rb"),
            },
            purpose="ocr"
        )
        signed_url = mistral_client.files.get_signed_url(file_id=uploaded_pdf.id)

    messages = [
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": user_query
            },
            {
                "type": "document_url",
                # "document_url": "https://arxiv.org/pdf/1805.04770"
                "document_url": signed_url.url
            }
        ]
    }
]

    chat_response = mistral_client.chat.complete(
        model='mistral-small-latest',
        messages=messages
    )
    return chat_response.choices[0].message.content


@mcp.tool()
def groq_llm(query: str, text: str):
    """Answers a query for a given text using Groq LLM."""
    response = gclient.chat.completions.create(
        model='openai/gpt-oss-120b',
        messages=[{
            'role': "user",
            'content': f"{query}\n\n{text}"
        }],
        temperature=0.5,
         top_p=1,
    # stream=False,
    # stop=None,
    
    # tool_choice="auto",
    # tools=[
    #     {
    #         "type": "browser_search"
    #     }
    # ]
    )
    return response.choices[0].message.content


@mcp.tool()
def groq_vlm(img_path: str, prompt: str):
    """Vision-based inference using image and prompt with Groq VLM."""
    base64_image = encode_image(img_path)
    chat_completions = gclient.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                },
            ],
        }]
    )
    return chat_completions.choices[0].message.content


@mcp.tool()
def mistral_llm(query: str, text: str):
    """Uses Mistral LLM to answer a query based on a text."""
    response = mistral_client.chat.complete(
        model='mistral-small-latest',
        messages=[{
            'role': 'user',
            'content': f'{query}\n\n{text}'
        }]
    )
    return response.choices[0].message.content


@mcp.tool()
def mist_llm(text: str):
    """Uses Mistral LLM to respond to free-form text."""
    response = mistral_client.chat.complete(
        model='mistral-small-latest',
        messages=[{
            'role': 'user',
            'text': text
        }]
    )
    return response.choices[0].message.content


@mcp.tool()
def websearch(query: str):
    """Searches the web using DuckDuckGo and returns combined content bodies."""
    results = DDGS().text(query, max_results=5)
    response = ''
    for result in results:
        response += result['body']
    return response


@mcp.tool()
def encode_image(image_path: str):
    """Encodes an image to base64 for LLM/VLM input."""
    with open(image_path, 'rb') as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')



def generate_web_queries(context,question):
    prompt = f"""
    Based on the following prescription and user question:
    
    Prescription: {context}
    Question: {question}

    Generate a few (2-3) web search queries that could provide additional helpful information for answering the question.
    Return them as a numbered list.

    Return the output strictly as a JSON object in the following format:
    {{
    "web_search_queries":['question1','question2','question3']
    }}
    """
    response = gclient.chat.completions.create(
        model='openai/gpt-oss-120b',
        messages=[{
            'role': "user",
            'content': f"{prompt}"
        }],
        temperature=0.2,
        response_format={'type': "json_object"}
    )

    output = json.loads(response.choices[0].message.content)
    return output['web_search_queries']


if __name__ == '__main__':
    print("Medical Tools MCP is ready.")
    print(ocr(r"C:\Desktop\certificates\cloud.pdf"))
    # mcp.run(transport='stdio')
