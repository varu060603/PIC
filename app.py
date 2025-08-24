from components import document_question,ocr,groq_llm,mistral_llm,websearch,groq_vlm
from prompts import prescript_prompt,insurance_prompt
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from duckduckgo_search import DDGS
from pdf2image import convert_from_path, convert_from_bytes



def prescript_answering(pdf_path_or_url,user_query):
    
    return document_question(pdf_path_or_url,user_query)


def prescript_analysis(pdf_path_or_url):

    return document_question(pdf_path_or_url,prescript_prompt)


def text_extraction(pdf_path_or_url):
    return ocr(pdf_path_or_url)


def general_question_answering(text,query):
    return groq_llm(query,text)


def medicines_understadning(query):
    
    relevant_content = websearch(query)
    prompt = 'with respect to medication and relevant content provided can you please resolve the user query with a precise answer without any explantion about the answer but just the answer'
    user_prompt = prompt + query + "####relevant contnet"
    return groq_llm(user_prompt,relevant_content)







def health_insurance_analysis(pdf_path_or_url,user_query):

    from_content = ocr(pdf_path_or_url)

    additive = f"""

From Content
{from_content}

User Question
{user_query}

"""
    
    return mistral_llm(insurance_prompt,additive)



def health_insurance_rag(pdf_path_or_url,user_query):
    content = ocr(pdf_path_or_url)
    text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    add_start_index=True,
    strip_whitespace=True,
    separators=["\n\n", "\n", ".", " ", ""],
)
    chunks = text_splitter.split_text(content)

    docs = [Document(page_content=chunk) for chunk in chunks]

    retriever = BM25Retriever.from_documents(docs, k=10)

    # Retrieve top-k relevant documents for the query
    results = retriever.invoke(user_query)

    # Format and return the result
    releavnt_content =  "\nRetrieved documents:\n" + "".join(
        [
            f"\n\n===== Document {i + 1} =====\n{doc.page_content}"
            for i, doc in enumerate(results)
        ]
    )

    additive = f"""        From Content {releavnt_content} User Question {user_query}        """

    return mistral_llm(insurance_prompt,additive)



def vision_analysis(pdf_path,user_query):
    images = convert_from_path(pdf_path)
    response = ''
    for img in images:
        img.save('temp.png')
        response = response + groq_vlm('temp.png',user_query)

    return groq_llm("summarise and remove redeancy and answer accurately",response)
        


if __name__ == '__main__':
    # texts = health_insurance_rag('hello','')
    # for text in texts:
    #     print(text)
    #     print("------------------------------")
    results = DDGS().text("Symptoms of using paracetemol in medicine?", max_results=5)
    for result in results:
        print(result['body'])
        print('--------------------------')






    
    
    
