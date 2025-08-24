from fastapi import FastAPI, Request,UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import os
from pydantic import BaseModel
from components import ocr, mistral_llm, groq_llm,websearch,generate_web_queries,document_question # Ensure these are correctly imported
from prompts import prescript_prompt,insurance_prompt,prescript_prompt2,insurance_summarise_prompt

app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Global variables to store OCR results
# prescription_text = ""
# insurance_text = ""
# bill_text = ""

# Utility function to save uploaded file and perform OCR
import os
import uuid
from fastapi import UploadFile, File

UPLOAD_FOLDER = "./uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

async def save_and_ocr(file: UploadFile):
    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    file_location = os.path.join(UPLOAD_FOLDER, unique_filename)
    
    with open(file_location, "wb") as f:
        f.write(await file.read())

    extracted_text = ocr(file_location)
    # print(extracted_text)
    return extracted_text


async def save_ocr_summarise(file: UploadFile):
    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    file_location = os.path.join(UPLOAD_FOLDER, unique_filename)
    
    with open(file_location, "wb") as f:
        f.write(await file.read())
    extarcted_text = document_question(file_location,insurance_summarise_prompt)
    return extarcted_text


@app.post("/upload_and_extract_text")
async def upload_file(file: UploadFile = File(...)):
    try:
        extracted_text = await save_and_ocr(file)
        return {"message": "File uploaded and processed.", "extracted_text": extracted_text}
    except Exception as e:
        return {"error": str(e)}



@app.post("/upload_insurance")
async def upload_insurance(file: UploadFile = File(...)):
    try:
        extarct_text = await save_ocr_summarise(file)
        return {"message":"File uploaded and processed","extarcted_text":extarct_text}
    except Exception as e:
        return {"message":"File upload failes","extarcted_text":"could not process the text"}
    


class PS(BaseModel):
    prescription_text: str

@app.post("/prescription/summary")
async def prescription_summary(ps: PS):
    """Returns summary of the prescription text"""
    if not ps.prescription_text:
        raise HTTPException(status_code=400, detail="No prescription uploaded yet.")
    
    prescription_summary = groq_llm(prescript_prompt, ps.prescription_text)
    return {"prescription_summary": prescription_summary}


class PSQA(BaseModel):
    prescription_text:str
    question:str

# Prescription Q&A endpoint
# @app.post("/prescription/qa")
# async def prescription_qa(PSQA:PSQA):
#     """allows you to question answer based on prescript"""
#     if not PSQA.prescription_text:
#         raise HTTPException(status_code=400, detail="No prescription uploaded yet.")
#     answer = groq_llm(PSQA.question, PSQA.prescription_text)
#     return {"answer": answer}


@app.post("/prescription/qa")
async def prescription_qa(PSQA:PSQA):
    if not PSQA.prescription_text:
        raise HTTPException(status_code=400, detail="No prescription uploaded yet.")
    
    web_prompt = f"""
    Prescription: {PSQA.prescription_text}
    Question: {PSQA.question}

    Do you need more information from the web to answer this question? Reply with 'Yes' or 'No'.
    Espicially use in cased when asked about medicnes or their side effects 
    Find out right medicine for the given disease 
    

    Provide the output in only one word that is 'Yes' or 'No'
    """
    decision = groq_llm(" ",web_prompt).strip().lower()
    print(decision)
    combined_context = ''
    if "yes" in decision:
        queries = generate_web_queries(PSQA.prescription_text, PSQA.question)
        web_content = "\n".join(websearch(query) for query in queries)
        combined_context += "\n\nAdditional Web Information:\n" + web_content
    
        PSQA.prescription_text = PSQA.prescription_text + combined_context

    answer = groq_llm(PSQA.question,PSQA.prescription_text)
    return {"answer":answer}






class IS(BaseModel):
    insurance_text:str

# Insurance summary endpoint
@app.post("/insurance/summary")
async def insurance_summary(IS:IS):
    """this helps in Insurance summarization"""

    if not IS.insurance_text:
        return {"insurance_summary": "insurance text is not available please upload the document"}
    summary = mistral_llm("Summarize this insurance policy", IS.insurance_text)
    return {"insurance_summary": summary}





class ISQA(BaseModel):
    insurance_text:str
    question:str

# Insurance Q&A endpoint
@app.post("/insurance/qa")
async def insurance_qa(ISQA:ISQA):
    """allows you to perform question answering on insurance copies"""
    if not ISQA.insurance_text:
        return {"insurance_summary": "insurance text is not available please upload the document"}
    answer = groq_llm(ISQA.question, ISQA.insurance_text)
    return {"answer": answer}




class CA(BaseModel):
    insurance_text:str
    billing_text:str

# Coverage analysis endpoint
@app.post("/coverage/analysis")
async def coverage_analysis(CA:CA):
    if not CA.insurance_text :
        return {"coverage_analysis":"Insurance text has not been provided please provide insurance text"}
    
    if not CA.billing_text:
        return {"coverage_analysis":"Billing text has not been provided please provide insurance text"}

        
    prompt = f"""
    Based on the following insurance policy and hospital bill, identify what parts of the bill are likely to be covered under the policy, and what parts are not covered. Provide a detailed explanation.
    Also provide reasoning behind the reason for not not being not covered 

    Insurance Policy:
    {CA.insurance_text}

    Hospital Bill:
    {CA.billing_text}
    """
    analysis = groq_llm("Analyze insurance coverage based on bill", prompt)
    return {"coverage_analysis": analysis}


import uvicorn
if __name__ == "__main__":
    uvicorn.run("fastapi-app:app", host="0.0.0.0", port=8000, reload=True)