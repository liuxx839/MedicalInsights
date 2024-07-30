import streamlit as st
from zhipuai import ZhipuAI
from groq import Groq
from openai import OpenAI
import json
import os
import re
from hunyuan import Hunyuan
import pandas as pd
from collections import defaultdict

st.set_page_config(layout="wide")

from config import get_rewrite_system_message,json_to_dataframe

# 在主程序文件的开头
from config import (
    topics, diseases,
    generate_tag_system_message, 
    generate_diseases_system_message,
    prob_identy_system_message,
    institutions,
    departments,
    persons,
    generate_structure_table_message
)

# 设置页面配置
# st.set_page_config(page_title="Medical Insights", layout="centered")

primary_topics_list = list(topics.keys())
primary_diseases_list = list(diseases.keys())

# 颜色映射，超过7个颜色的primary_topics_list都赋予粉色
color_list = [
    "#FF6347",  # 番茄红
    "#4682B4",  # 钢蓝色
    "#32CD32",  # 石灰绿色
    "#FFD700",  # 金色
    "#EE82EE",  # 紫罗兰
    "#8A2BE2",  # 蓝紫色
    "#FF4500"   # 橙红色
]

# 默认粉色用于超过7个颜色的主题
default_color = "#FF69B4"  # 粉色

# 按照顺序为 primary_topics_list 分配颜色
colors = {}
for i, topic in enumerate(primary_topics_list):
    colors[topic] = color_list[i] if i < len(color_list) else default_color

def setup_client():
    st.sidebar.markdown("---")
    model_choice = st.sidebar.selectbox(
        "Select Model",
        ["llama-3.1-70b-versatile","llama3-70b-8192","llama-3.1-8b-instant", "glm-4-air","hunyuan-lite","hunyuan-pro"],
        index=0  # 默认选择 llama3-70b-8192
    )

    if model_choice == "llama3-70b-8192" or model_choice == "llama-3.1-70b-versatile" or model_choice == "llama-3.1-8b-instant":
        api_key = os.environ.get("GROQ_API_KEY")
        client = Groq(api_key=api_key)
    elif model_choice == "glm-4-air":
        api_key = os.environ.get("ZHIPU_API_KEY")
        client = ZhipuAI(api_key=api_key)
    elif model_choice == "hunyuan-lite":
        # 从环境变量获取 API ID 和 API Key
        api_id = os.environ.get("TENCENT_SECRET_ID")
        api_key = os.environ.get("TENCENT_SECRET_KEY")
        # 创建 Hunyuan 客户端实例
        client = Hunyuan(api_id=api_id, api_key=api_key)
    else: 
        # 从环境变量获取 API ID 和 API Key
        api_id = os.environ.get("TENCENT_SECRET_ID")
        api_key = os.environ.get("TENCENT_SECRET_KEY")
        # 创建 Hunyuan 客户端实例
        client = Hunyuan(api_id=api_id, api_key=api_key)

    return model_choice, client

# 在主程序的开始部分调用这个函数
model_choice, client = setup_client()


# 修改generate_tag函数
def generate_tag(text,model_choice="llama3-70b-8192"):
    completion = client.chat.completions.create(
        model=model_choice,  # 填写需要调用的模型名称
        messages=[
            {"role": "system", "content": 
            generate_tag_system_message.format(primary_topics_list=','.join(primary_topics_list))},       
            {"role": "user", "content": text}
        ],
        temperature=0.1,
        max_tokens=300,
    )
    summary = completion.choices[0].message.content.strip()
    return summary

def generate_diseases_tag(text,model_choice="llama3-70b-8192"):
    completion = client.chat.completions.create(
        model=model_choice,  # 填写需要调用的模型名称
        messages=[
            {"role": "system", "content": 
            generate_diseases_system_message.format(primary_diseases_list=','.join(primary_diseases_list))},       
            {"role": "user", "content": text}
        ],
        temperature=0.1,
        max_tokens=300,
    )
    summary = completion.choices[0].message.content.strip()
    return summary

def rewrite(text, institution, department, person,model_choice="llama3-70b-8192"):
    completion = client.chat.completions.create(
        model=model_choice,
        messages=[
            {"role": "system", "content": get_rewrite_system_message(institution, department, person)},
            {"role": "user", "content": text}
        ],
        temperature=0.1,
        max_tokens=500,
    )
    summary = completion.choices[0].message.content
    return summary

def prob_identy(text,model_choice="llama3-70b-8192"):
    completion = client.chat.completions.create(
        model=model_choice,
        messages=[
            {"role": "system", "content": prob_identy_system_message},       
            {"role": "user", "content": text}
        ],
        temperature=0.1,
        max_tokens=500,
    )
    summary = completion.choices[0].message.content
    return summary

def generate_structure_data(text,model_choice="llama3-70b-8192"):
    completion = client.chat.completions.create(
        model=model_choice,
        messages=[
            {"role": "system", "content": generate_structure_table_message},       
            {"role": "user", "content": text}
        ],
        temperature=0.1,
        max_tokens=500
    )
    summary = completion.choices[0].message.content
    return summary
  
# 修改match_color函数
def match_color(tag):
    tag = tag.strip()
    # 直接匹配一级分类
    if tag in primary_topics_list:
        return colors[tag]
    # 二级分类匹配
    for topic, keywords in topics.items():
        if tag in keywords:
            return colors[topic]
    return "#696969"  # 默认为灰色

# 标题
st.title("Medical Insights Tagging&Rewrite")

# 多选框和下拉菜单
with st.sidebar:
    st.markdown("""
    <div style="font-size:18px; font-weight:bold;">
    - Insight应涵盖4W要素（Who-谁、What-什么、Why-为什么、Wayfoward-未来方向）。<br>
    以下是一个合格样式的示例："一位{脱敏机构}的{科室}的{脱敏人物}指出{观点}，并阐述了{内容间的逻辑联系}，进而提出了{后续方案}"。<br>
    - Insight Copilot：您可以在下面提交您的初稿，然后使用此工具对内容进行打标或者重写。您还可以直接修改重写后的结果。
    </div>
    """, unsafe_allow_html=True)

    # st.header("Select Options")
    
    # 用户输入框
    user_input = st.text_area("Enter Medical Insights: ")

    # 生成标签
    if st.button("Generate Tags"):
        # 直接将用户输入的文本传递给 generate_tag 函数
        tags = generate_tag(user_input,model_choice)
        # 去重复并存储生成的标签到会话状态
        unique_tags = list(set(tags.split(",")))  # 将标签按逗号分隔后转换为集合去重，再转换为列表
        st.session_state.tags = ",".join(unique_tags)  # 将去重后的标签列表转换为逗号分隔的字符串并存储到会话状态

        # 生成疾病标签
        disease_tags = generate_diseases_tag(user_input, model_choice)
        unique_disease_tags = list(set(disease_tags.split(",")))
        st.session_state.disease_tags = ",".join(unique_disease_tags)

    # 一级主题选择
    primary_topics = st.multiselect("Select Primary Topics", primary_topics_list)
    
    # 二级主题选择
    secondary_topics = {}
    if primary_topics:
        for topic in primary_topics:
            secondary_topics[topic] = st.multiselect(f"Select Secondary Topics for {topic}", topics[topic])

institution = st.selectbox("Select Institution", institutions)
department = st.selectbox("Select Department", departments)
person = st.selectbox("Select Person", persons)

# 主页面内容
st.write("### Selected Options")
primary_topic_tags = [f'<span class="tag" style="background-color: {colors[topic]};">{topic}</span>' for topic in primary_topics]
st.markdown(f"**Primary Topics:** {' '.join(primary_topic_tags)}", unsafe_allow_html=True)

secondary_topic_tags = []
for topic, subtopics in secondary_topics.items():
    for subtopic in subtopics:
        secondary_topic_tags.append(f'<span class="tag" style="background-color: {colors[topic]};">{subtopic}</span>')
st.markdown(f"**Secondary Topics:** {' '.join(secondary_topic_tags)}", unsafe_allow_html=True)

# st.write(f"**Institution:** {institution}")
# st.write(f"**Department:** {department}")
# st.write(f"**Person:** {person}")

# 替换默认标签，按逗号分词
if 'tags' in st.session_state:
    # 使用正则表达式同时匹配逗号和空白作为分隔符
    user_generated_tags = re.split(r'[,\s]+', st.session_state.tags.strip())
    # 移除空字符串
    user_generated_tags = [tag for tag in user_generated_tags if tag]
    tag_html = " ".join([f'<span class="tag" style="background-color: {match_color(tag)};">{tag}</span>' for tag in user_generated_tags])
    st.markdown(f"**AutoTags:** {tag_html}", unsafe_allow_html=True)
    
    # 显示疾病标签
    if 'disease_tags' in st.session_state:
        disease_tags = re.split(r'[,\s]+', st.session_state.disease_tags.strip())
        disease_tags = [tag for tag in disease_tags if tag]
        disease_tag_html = ", ".join(disease_tags)
        st.markdown(f"**Disease Tags:** {disease_tag_html}")

# 创建按钮和可编辑文本区域
if st.button("ReWrite"):
    rewrite_text = rewrite(user_input, institution, department, person,model_choice)
    potential_issues = prob_identy(user_input,model_choice)
    table_text = generate_structure_data(user_input, model_choice)  # 生成表格数据
    st.session_state.rewrite_text = rewrite_text
    st.session_state.potential_issues = potential_issues
    st.session_state.table_df = json_to_dataframe(table_text)  # 将表格数据转换为DataFrame


def determine_issue_severity(issues_text):
    if "内容需要修改" in issues_text:
        return "red"
    elif "内容基本满足" in issues_text or ("满足所有条件" in issues_text and "内容基本满足" in issues_text):
        return "yellow"
    elif "满足所有条件" in issues_text:
        return "green"
    else:
        return "white"

if 'rewrite_text' in st.session_state:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Assessment Feedback:")
        background_color = determine_issue_severity(st.session_state.potential_issues)
        st.markdown(
            f"""
            <div style="background-color: {background_color}; color: black; padding: 10px; border-radius: 5px; font-family: sans-serif;">
                {st.session_state.potential_issues}
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with col2:
        st.subheader("Editable Rewritten Text:")
        user_editable_text = st.text_area("", st.session_state.rewrite_text, height=300)
        st.session_state.rewrite_text = user_editable_text

    # 表格展示
    st.subheader("Extracted Information:")
    if 'table_df' in st.session_state:
        st.dataframe(st.session_state.table_df)

# if 'rewrite_text' in st.session_state:
#     col1, col2 = st.columns(2)
    
#     with col1:
#         st.subheader("Potential Issues:")
#         st.write(st.session_state.potential_issues)
    
#     with col2:
#         st.subheader("Editable Rewritten Text:")
#         user_editable_text = st.text_area("", st.session_state.rewrite_text, height=300)
#         st.session_state.rewrite_text = user_editable_text

# # 添加更多选项
# if st.checkbox("More"):
#     st.write("More options are selected.")

# 添加其他标签
st.markdown(
    """
    <style>
    .tag {
        display: inline-block;
        color: white;
        border-radius: 5px;
        padding: 5px;
        margin: 2px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# 复选框选项
use_generated_text_and_tags = st.checkbox("Use Editable Rewritten Text and AutoTags", value=True)

# 生成并下载 JSON 文件
def create_json_data():
    if use_generated_text_and_tags and 'rewrite_text' in st.session_state and 'tags' in st.session_state:
        data = {
            "Medical_Insights": st.session_state.rewrite_text,
            "Tags": st.session_state.tags.split(",")
        }
    else:
        data = {
            "Medical_Insights": user_input,
            "Tags": primary_topics
        }
    return json.dumps(data, ensure_ascii=False, indent=4)

# 下载 JSON 文件
st.download_button(
    label="Download JSON",
    data=create_json_data(),
    file_name="medical_insights.json",
    mime="application/json"
)
