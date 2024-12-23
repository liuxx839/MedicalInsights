#functions.py
from zhipuai import ZhipuAI
from openai import OpenAI
from groq import Groq
from hunyuan import Hunyuan
import os
from config import (
    get_rewrite_system_message,
    generate_tag_system_message,
    generate_diseases_system_message,
    prob_identy_system_message,
    generate_structure_table_message,
    primary_diseases_list,
    primary_topics_list
)

def setup_client():
    # model_choice = "llama3-70b-8192"  # 默认模型，你可以根据需要修改
    # model_choice = "llama-3.3-70b-versatile"
    # model_choice = "llama-3.1-70b-versatile"  # 默认模型，你可以根据需要修改
    # model_choice = "hunyuan-pro" 
    # model_choice = "glm-4-airx" 
    model_choice = "glm-4-plus" 
    if model_choice in ["llama3-70b-8192", "llama-3.1-70b-versatile", "llama-3.1-8b-instant","llama-3.3-70b-versatile"]:
        api_key = os.environ.get("GROQ_API_KEY")
        client = Groq(api_key=api_key)
    elif model_choice == "glm-4-plus":
        api_key = os.environ.get("ZHIPU_API_KEY")
        client = ZhipuAI(api_key=api_key)
    elif model_choice in ["hunyuan-lite", "hunyuan-pro"]:
        api_id = os.environ.get("TENCENT_SECRET_ID")
        api_key = os.environ.get("TENCENT_SECRET_KEY")
        client = Hunyuan(api_id=api_id, api_key=api_key)
    return model_choice, client

def generate_tag(text, model_choice, client):
    completion = client.chat.completions.create(
        model=model_choice,
        messages=[
            {"role": "system", "content": generate_tag_system_message.format(primary_topics_list=','.join(primary_topics_list))},       
            {"role": "user", "content": text}
        ],
        temperature=0.1,
        max_tokens=300,
    )
    summary = completion.choices[0].message.content.strip()
    return summary

def generate_diseases_tag(text, model_choice, client):
    completion = client.chat.completions.create(
        model=model_choice,
        messages=[
            {"role": "system", "content":generate_diseases_system_message.format(primary_diseases_list=','.join(primary_diseases_list))},       
            {"role": "user", "content": text}
        ],
        temperature=0.1,
        max_tokens=300,
    )
    summary = completion.choices[0].message.content.strip()
    return summary

def rewrite(text, institution, department, person, model_choice, client):
    completion = client.chat.completions.create(
        model=model_choice,
        messages=[
            {"role": "system", "content": get_rewrite_system_message(institution, department, person)},
            {"role": "user", "content": text}
        ],
        temperature=0.1,
        max_tokens=1200,
    )
    summary = completion.choices[0].message.content
    return summary

def prob_identy(text, model_choice, client):
    completion = client.chat.completions.create(
        model=model_choice,
        messages=[
            {"role": "system", "content": prob_identy_system_message},       
            {"role": "user", "content": text}
        ],
        temperature=0.0,
        max_tokens=500,
    )
    summary = completion.choices[0].message.content
    return summary

def generate_structure_data(text, model_choice, client):
    completion = client.chat.completions.create(
        model=model_choice,
        messages=[
            {"role": "system", "content": generate_structure_table_message},       
            {"role": "user", "content": text}
        ],
        temperature=0.0,
        max_tokens=500
    )
    summary = completion.choices[0].message.content
    return summary
