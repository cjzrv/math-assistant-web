# math_assistant_gui.py (FastAPI + HTML + Follow-up + Lang switch + Markdown + Model selector)

from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import requests
import json
import random
import uvicorn
import os
import markdown as md

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
    "Content-Type": "application/json"
}

with open("ape210k_test.json", "r", encoding="utf-8") as f:
    QUESTION_BANK = json.load(f)

def get_random_question():
    q = random.choice(QUESTION_BANK)
    return {
        "question": q["original_text"],
        "question_en": q.get("original_text_en", q["original_text"]),
        "answer": q["ans"],
        "equation": q["equation"]
    }

def get_llm_response(messages, model="google/gemini-2.0-flash-001"):
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.5
    }
    response = requests.post(OPENROUTER_API_URL, headers=HEADERS, json=payload)
    result = response.json()
    return result["choices"][0]["message"]["content"]

@app.get("/", response_class=HTMLResponse)
def get_home(request: Request, lang: str = Query("zh"), model: str = Query("google/gemini-2.0-flash-001")):
    question_data = get_random_question()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "question": question_data["question"] if lang == "zh" else question_data["question_en"],
        "correct_answer": question_data["answer"],
        "response": "",
        "chat_history": [],
        "history_json": "[]",
        "lang": lang,
        "model": model
    })

@app.post("/answer", response_class=HTMLResponse)
def submit_answer(
    request: Request,
    user_answer: str = Form(...),
    question: str = Form(...),
    correct_answer: str = Form(...),
    history_json: str = Form(default="[]"),
    lang: str = Form(default="zh"),
    model: str = Form(default="google/gemini-2.0-flash-001")
):
    try:
        history = json.loads(history_json)
    except:
        history = []

    if lang == "en":
        system_msg = "You are an elementary school math teacher. Please evaluate the student's answer and explain in English."
        prompt = f"""
You are an elementary school math teacher. Please check the student's answer and reply in English. You may use Markdown formatting.

Here is a math question:
Question: {question}

The student's answer: {user_answer}  
The correct answer should be: {correct_answer}

Please follow these rules to respond:
- If the student's answer is correct (even with unit or formatting differences), praise them.
- If the answer is wrong, start your response with: ❌ Your answer is incorrect. The correct answer is {correct_answer}. Then briefly explain how to solve it.
"""
    else:
        system_msg = "你是使用者的數學家教，請幫助學生解題，回覆可以使用 Markdown。"
        prompt = f"""
你是使用者的數學家教，請批改以下數學題，並用繁體中文回應，可以使用 Markdown 格式。

這是一道數學題目：
問題：{question}

使用者的答案是：{user_answer}
正確答案應該是：{correct_answer}

請根據以下規則給出回饋：
- 如果使用者答對（即使有單位或格式上的差異），請告知正確答案，並稱讚使用者。
- 如果答錯，請以「❌ 錯誤，正確答案是 {correct_answer}。」開頭，解釋這題應該如何解。
"""

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": prompt}
    ]

    llm_reply = get_llm_response(messages, model=model)
    llm_reply_html = md.markdown(llm_reply)

    history.append({"role": "user", "content": user_answer})
    history.append({"role": "assistant", "content": llm_reply})
    history_json = json.dumps(history)

    chat_history = []
    for h in history:
        if h.get("role") == "user":
            chat_history.append({"user": h["content"]})
        elif h.get("role") == "assistant":
            chat_history.append({"assistant": md.markdown(h["content"])})

    return templates.TemplateResponse("index.html", {
        "request": request,
        "question": question,
        "correct_answer": correct_answer,
        "response": llm_reply_html,
        "chat_history": chat_history,
        "history_json": history_json,
        "lang": lang,
        "model": model
    })

@app.post("/followup", response_class=HTMLResponse)
def submit_followup(
    request: Request,
    followup: str = Form(...),
    question: str = Form(...),
    correct_answer: str = Form(...),
    history_json: str = Form(default="[]"),
    lang: str = Form(default="zh"),
    model: str = Form(default="google/gemini-2.0-flash-001")
):
    try:
        history = json.loads(history_json)
    except:
        history = []

    history.append({"role": "user", "content": followup})

    system_msg = (
        "You are an elementary school math teacher. Please continue the conversation in English. You may use Markdown."
        if lang == "en" else
        "你是使用者的數學家教，請根據對話內容協助學生，可以使用 Markdown 語法回覆。"
    )

    messages = [{"role": "system", "content": system_msg}] + history

    llm_reply = get_llm_response(messages, model=model)
    llm_reply_html = md.markdown(llm_reply)
    history.append({"role": "assistant", "content": llm_reply})
    history_json = json.dumps(history)

    chat_history = []
    for h in history:
        if h.get("role") == "user":
            chat_history.append({"user": h["content"]})
        elif h.get("role") == "assistant":
            chat_history.append({"assistant": md.markdown(h["content"])})

    return templates.TemplateResponse("index.html", {
        "request": request,
        "question": question,
        "correct_answer": correct_answer,
        "response": llm_reply_html,
        "chat_history": chat_history,
        "history_json": history_json,
        "lang": lang,
        "model": model
    })

if __name__ == "__main__":
    uvicorn.run("math_assistant_gui:app", host="0.0.0.0", port=8000, reload=True)