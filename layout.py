import streamlit as st
import re
import time
from PIL import Image
from utils import match_color, determine_issue_severity, create_json_data
from config import json_to_dataframe, get_rewrite_system_message, colors, topics, primary_topics_list
from streamlit_extras.stylable_container import stylable_container
from groq import Groq
from zhipuai import ZhipuAI
import os
import base64
from io import BytesIO
import numpy as np
import pickle
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

# api_key = os.environ.get("GROQ_API_KEY")
# client = Groq(api_key=api_key)
api_key_vision = os.environ.get("ZHIPU_API_KEY")
client_vision = ZhipuAI(api_key=api_key_vision)

## Load embedding model
# @st.cache_resource
# def load_embedding_model():
#     return SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

@st.cache_resource
def load_embedding_model():
    return ZhipuAI(api_key=api_key_vision)

# @st.cache_resource
# def load_embedding_model():
#     # Use local model directory instead of downloading from HuggingFace
#     local_model_path = './embed_models/sentence-transformer'
#     try:
#         return SentenceTransformer(local_model_path)
#     except Exception as e:
#         st.error(f"Error loading model from {local_model_path}: {str(e)}")
#         return None
        
# Load embeddings from pkl file
@st.cache_data
def load_embeddings():
    try:
        with open('medical_text_embeddings_zhipu_256_250305.pkl', 'rb') as f:
            return pickle.load(f)
    except FileNotFoundError:
        st.error("Embeddings file not found. Please make sure 'embeddings.pkl' exists in the current directory.")
        return None

# def get_color(similarity):
#     if similarity >= 0.8:
#         return "#067647"  # 绿色
#     elif similarity >= 0.6:
#         return "#B42318"  # 红色
#     elif similarity >= 0.4:
#         return "#B54708"  # 棕色
#     elif similarity >= 0.2:
#         return "#175CD3"  # 蓝色
#     elif similarity >= 0.1:
#         return "#282828"  # 黑色
#     else:
#         return "#7A00E6"  # 紫色
# def get_similar_content(user_input, embeddings_data, model, top_k=5):
#     """
#     Find top-k similar content based on embeddings
    
#     Args:
#         user_input (str): User input text
#         embeddings_data (dict): Dictionary with embeddings and content
#         model: SentenceTransformer model
#         top_k (int): Number of similar contents to return
        
#     Returns:
#         list: List of top-k similar contents
#     """
#     if embeddings_data is None or user_input.strip() == "":
#         return []
    
#     # Get embeddings for user input
#     user_embedding = model.encode([user_input])[0].reshape(1, -1)
    
#     # Get all stored embeddings
#     stored_embeddings = np.array(embeddings_data['embeddings'])
#     stored_contents = embeddings_data['contents']
    
#     # Calculate similarity
#     similarities = cosine_similarity(user_embedding, stored_embeddings)[0]
    
#     # Get indices of top-k similar contents
#     top_indices = similarities.argsort()[-top_k:][::-1]
    
#     # Return top-k similar contents with their similarity scores
#     similar_contents = [
#         {"content": stored_contents[idx], "similarity": similarities[idx]}
#         for idx in top_indices
#     ]
    
#     return similar_contents

# def get_similar_content(user_input, embeddings_data, model, top_k=5):
#     """
#     Find top-k similar content based on embeddings
    
#     Args:
#         user_input (str): User input text
#         embeddings_data (dict): Dictionary with embeddings and content
#         model: SentenceTransformer model
#         top_k (int): Number of similar contents to return
        
#     Returns:
#         list: List of top-k similar contents
#     """
#     if embeddings_data is None or user_input.strip() == "":
#         return []
    
#     # Get embeddings for user input
#     user_embedding = model.encode([user_input])[0].reshape(1, -1)
    
#     # Get all stored embeddings
#     stored_embeddings = np.array(embeddings_data['embeddings'])
#     stored_contents = embeddings_data['contents']
    
#     # Check if timestamps are available
#     has_timestamps = 'timestamps' in embeddings_data
    
#     # Calculate similarity
#     similarities = cosine_similarity(user_embedding, stored_embeddings)[0]
    
#     # Get indices of top-k similar contents
#     top_indices = similarities.argsort()[-top_k:][::-1]
    
#     # Return top-k similar contents with their similarity scores and timestamps if available
#     similar_contents = []
#     for idx in top_indices:
#         item = {
#             "content": stored_contents[idx],
#             "similarity": similarities[idx]
#         }
        
#         # Add timestamp if available
#         if has_timestamps:
#             item["timestamp"] = embeddings_data['timestamps'][idx]
            
#         similar_contents.append(item)
    
#     return similar_contents

def get_similar_content(user_input, embeddings_data, client, top_k=5):
    """
    Find top-k similar content based on embeddings
    
    Args:
        user_input (str): User input text
        embeddings_data (dict): Dictionary with embeddings and content
        client: ZhipuAI client
        top_k (int): Number of similar contents to return
        
    Returns:
        list: List of top-k similar contents
    """
    if embeddings_data is None or user_input.strip() == "":
        return []
    
    # Get embeddings for user input
    response = client.embeddings.create(
        model="embedding-3",
        input=[user_input],
        dimensions=256
    )
    user_embedding = np.array(response.data[0].embedding).reshape(1, -1)
    
    # Get all stored embeddings
    stored_embeddings = np.array(embeddings_data['embeddings'])
    stored_contents = embeddings_data['contents']
    
    # Check if timestamps are available
    has_timestamps = 'timestamps' in embeddings_data
    
    # Calculate similarity
    similarities = cosine_similarity(user_embedding, stored_embeddings)[0]
    
    # Get indices of top-k similar contents
    top_indices = similarities.argsort()[-top_k:][::-1]
    
    # Return top-k similar contents with their similarity scores and timestamps if available
    similar_contents = []
    for idx in top_indices:
        item = {
            "content": stored_contents[idx],
            "similarity": similarities[idx]
        }
        
        # Add timestamp if available
        if has_timestamps:
            item["timestamp"] = embeddings_data['timestamps'][idx]
            
        similar_contents.append(item)
    
    return similar_contents

def encode_image(image):
    """
    Encode a PIL Image object to a Base64 string with compression and ensure it is under 4MB.
    """
    max_size = (800, 800)  # 设置最大尺寸
    max_file_size = 4 * 1024 * 1024  # 4MB 文件大小限制
    
    # 压缩图片
    image.thumbnail(max_size, Image.Resampling.LANCZOS)
    
    # 转换为RGB模式（去除alpha通道）
    if image.mode in ('RGBA', 'LA'):
        background = Image.new('RGB', image.size, (255, 255, 255))
        background.paste(image, mask=image.split()[-1])
        image = background
    
    # 尝试降低质量，直到图像文件大小小于 4MB
    quality = 95  # 初始质量为95
    buffered = BytesIO()
    
    # 反复压缩直到文件大小小于4MB
    while True:
        buffered.seek(0)
        image.save(buffered, format="JPEG", quality=quality, optimize=True)
        
        # 如果文件大小小于4MB，跳出循环
        if len(buffered.getvalue()) <= max_file_size:
            break
        
        # 每次降低5%的质量
        quality -= 5
    
    # 返回Base64编码
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def readimg(user_image):
    """
    Process a PIL Image and extract text using Groq's vision model.
    """
    if client_vision is None:
        raise ValueError("Groq client must be provided")

    try:
        # 复制图片对象以避免修改原始图片
        image_to_process = user_image.copy()
        base64_image = encode_image(image_to_process)
        
        response = client_vision.chat.completions.create(
            model="glm-4v-plus",  # Fill in the model name to be called
            messages=[
              {
                "role": "user",
                "content": [
                  {
                    "type": "image_url",
                    "image_url": {
                        "url": base64_image
                    }
                  },
                  {
                    "type": "text",
                    "text": "提取图片里的文字"
                  }
                ]
              }
            ]
        )
        return(response.choices[0].message.content)

    except Exception as e:
        raise Exception(f"Error processing image with Groq API: {str(e)}")


def setup_layout(
    topics, diseases, institutions, departments, persons,
    primary_topics_list, primary_diseases_list,
    generate_tag, generate_diseases_tag, rewrite,
    prob_identy, generate_structure_data,
    model_choice, client
):
    # Load embedding model and embeddings
    embedding_model = load_embedding_model()
    embeddings_data = load_embeddings()
    
    # 更新标题样式
    st.markdown("""
    <h1 style='text-align: center; font-size: 18px; font-weight: bold;'>Medical Insights Copilot</h1>
    <h6 style='text-align: center; font-size: 12px;'>改写的结果及反馈将呈现在下方，请根据自己的判断进行使用</h6>
    <br><br><br>
    """, unsafe_allow_html=True)
    
    # Sidebar layout
    user_input = setup_sidebar(
        topics, primary_topics_list,
        institutions, departments, persons,
        generate_tag, generate_diseases_tag, rewrite,
        prob_identy, generate_structure_data,
        model_choice, client,
        embedding_model, embeddings_data
    )
    
    # Main page layout
    setup_main_page(
        model_choice, client, user_input
    )

def setup_sidebar(
    topics, primary_topics_list, institutions, departments, persons,
    generate_tag, generate_diseases_tag, rewrite,
    prob_identy, generate_structure_data,
    model_choice, client,
    embedding_model, embeddings_data
):
    with st.sidebar:
        st.markdown("""
        <div style="font-size:12px;">
        * Insight应涵盖4W要素（Who-谁、What-什么、Why-为什么、Wayfoward-未来方向）。<br>
        以下是一个合格样式的示例："一位{脱敏机构}的{科室}的{脱敏人物}指出{观点}，并阐述了{内容间的逻辑联系}，进而提出了{后续方案}"。<br>
        * Insight Copilot：您可以在下面提交您的初稿或上传图片，然后使此工具对内容进行打标或者重写。您还可以直接修改重写后的结果。
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<p style='font-size: 14px; font-weight: bold;'>Step 1: 请输入文字或上传图片 ✏️:</p>", unsafe_allow_html=True)
        
        # 在创建文本框之前检查是否需要清除
        if "clear_clicked" not in st.session_state:
            st.session_state.clear_clicked = False
        
        # 如果清除按钮被点击，初始化一个空的key
        if st.session_state.clear_clicked:
            key = "user_input_" + str(hash(time.time()))
            st.session_state.clear_clicked = False
        else:
            key = "user_input"

        # 添加选项卡用于文字输入和图片上传
        tab1, tab2 = st.tabs(["文字输入", "图片上传"])
        
        with tab1:
            # 使用动态key创建文本框
            user_input = st.text_area("", placeholder="请输入内容\n提示：您可以按下 Ctrl + A 全选内容，接着按下 Ctrl + C 复制", key=key, height=200)
            
            # Find similar content when user inputs text
            if user_input and user_input.strip() != "":
                # Store in session state to avoid recalculating on every rerun
                if "similar_contents" not in st.session_state or st.session_state.get("last_input", "") != user_input:
                    with st.spinner("正在查找相似内容..."):
                        similar_contents = get_similar_content(user_input, embeddings_data, embedding_model,top_k = 5)
                        st.session_state.similar_contents = similar_contents
                        st.session_state.last_input = user_input

        with tab2:
            # 初始化 session state
            if "previous_file_name" not in st.session_state:
                st.session_state.previous_file_name = None
                
            uploaded_file = st.file_uploader("上传图片", type=['png', 'jpg', 'jpeg'])
            
            if uploaded_file is not None:
                current_file_name = uploaded_file.name
                
                # 只有当上传了新文件时才处理图片
                if (st.session_state.previous_file_name != current_file_name):
                    image = Image.open(uploaded_file)
                    st.image(image, caption="上传的图片", use_column_width=True)
                    
                    try:
                        with st.spinner('正在处理图片...'):
                            extracted_text = readimg(image)
                            st.session_state.extracted_text = extracted_text
                            st.session_state.previous_file_name = current_file_name
                            user_input = extracted_text
                            
                            # Find similar content for extracted text
                            similar_contents = get_similar_content(extracted_text, embeddings_data, embedding_model)
                            st.session_state.similar_contents = similar_contents
                            st.session_state.last_input = extracted_text
                    except Exception as e:
                        st.error(f"图片处理出错: {str(e)}")
                        user_input = ""
                else:
                    # 使用缓存的结果
                    st.image(Image.open(uploaded_file), caption="上传的图片", use_column_width=True)
                    user_input = st.session_state.extracted_text
                
                # 显示提取的文字
                st.text_area("提取的文字", st.session_state.get("extracted_text", ""), height=200, key="extracted_text_display")

        # 显示相似内容
        # if "similar_contents" in st.session_state and st.session_state.similar_contents:
        #     with st.expander("相似内容 (Top 5)"):
        #         for i, item in enumerate(st.session_state.similar_contents):
        #             st.markdown(f"**相似度: {item['similarity']:.2f}**")
        #             st.markdown(f"```\n{item['content']}\n```")
        #             if i < len(st.session_state.similar_contents) - 1:
        #                 st.markdown("---")
        
        if "similar_contents" in st.session_state and st.session_state.similar_contents:
            with st.expander("相似内容 (Top 5)", expanded=True):
                # 添加比较结果显示
                if user_input and user_input.strip() != "":
                    api_key = os.environ.get("GROQ_API_KEY")
                    client = Groq(api_key=api_key)
                    comparison = generate_comparison(user_input, 'llama3-70b-8192', client, st.session_state.similar_contents)
                    st.markdown("### 内容比较")
                    st.markdown(comparison)
                    st.markdown("---")
                
                # 原有的相似内容显示代码
                for i, item in enumerate(st.session_state.similar_contents):
                    col1, col2 = st.columns([1, 9])
                    with col1:
                        st.markdown(f"**{i+1}. {item['similarity']:.2f}**")
                        if 'timestamp' in item:
                            st.markdown(f"<small>{item['timestamp']}</small>", unsafe_allow_html=True)
                    with col2:
                        st.text_area(
                            label="",
                            value=item['content'],
                            height=100,
                            key=f"similar_content_{i}"
                        )
                    
                    if i < len(st.session_state.similar_contents) - 1:
                        st.markdown("<hr style='margin: 5px 0px'>", unsafe_allow_html=True)

        # if "similar_contents" in st.session_state and st.session_state.similar_contents:
        #     with st.expander("相似内容 (Top 5)", expanded=True):
        #         for i, item in enumerate(st.session_state.similar_contents):
        #             color = get_color(item['similarity'])
        #             with st.container():
        #                 col1, col2 = st.columns([2, 8])
        #                 with col1:
        #                     st.markdown(f"<h3 style='margin-bottom: 0; color: {color};'>{i+1}</h3>", unsafe_allow_html=True)
        #                     st.markdown(f"<p style='color: {color}; font-size: 0.9em; margin-top: 0; font-weight: bold;'>相似度: {item['similarity']:.2f}</p>", unsafe_allow_html=True)
        #                     if 'timestamp' in item:
        #                         st.markdown(f"<p style='color: #666; font-size: 0.8em;'>{item['timestamp']}</p>", unsafe_allow_html=True)
        #                 with col2:
        #                     st.markdown(
        #                         f"""
        #                         <div style='background-color: {color}22; border-left: 3px solid {color}; border-radius: 5px; padding: 10px; height: 100px; overflow-y: auto;'>
        #                             {item['content']}
        #                         </div>
        #                         """,
        #                         unsafe_allow_html=True
        #                     )
                        
        #                 if i < len(st.session_state.similar_contents) - 1:
        #                     st.markdown("<hr style='margin: 15px 0px; border: none; height: 1px; background-color: #e0e0e0;'>", unsafe_allow_html=True)
                
        # 清除按钮处理
        with stylable_container(
            "clear_button",
            css_styles="""
            button {
                background-color: white;
                color: #7A00E6;
                border: 1px solid #7A00E6;
            }"""
        ):
            if st.button("🗑️一键清除"):
                # 清除所有相关的 session state 变量
                keys_to_clear = [
                    'previous_file_name', 
                    'extracted_text', 
                    'tags', 
                    'disease_tags', 
                    'rewrite_text', 
                    'table_df', 
                    'potential_issues',
                    'similar_contents',
                    'last_input'
                ]
                for key in keys_to_clear:
                    if key in st.session_state:
                        del st.session_state[key]
                st.session_state.clear_clicked = True
                st.rerun()
        
        st.markdown("<p style='font-size: 14px; font-weight: bold;'>Step 2: 请根据拜访选择如下信息用于Rewrite🧑‍⚕️</p>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.session_state.institution = st.selectbox("Institution", institutions)
        with col2:
            st.session_state.department = st.selectbox("Department", departments)
        with col3:
            st.session_state.person = st.selectbox("Title", persons)

        col1, col2 = st.columns(2)
        with col1:
            with stylable_container("step1",
                    css_styles="""
                    button {
                        background-color: white;
                        color: #7A00E6;
                    }""",
                ):
                    if st.button("Generate Tags (Optional)"):
                        tags = generate_tag(user_input, model_choice, client)
                        unique_tags = list(set(tags.split(",")))
                        st.session_state.tags = ",".join(unique_tags)
            
                        disease_tags = generate_diseases_tag(user_input, model_choice, client)
                        unique_disease_tags = list(set(disease_tags.split(",")))
                        st.session_state.disease_tags = ",".join(unique_disease_tags)

        with col2:
            with stylable_container("step2",
                    css_styles="""
                    button {
                        background-color: #7A00E6;
                        color: white;
                    }""",
                    ):
                        if st.button("Rewrite   →", use_container_width=True):
                            process_rewrite(user_input, st.session_state.get('institution'), 
                                            st.session_state.get('department'), st.session_state.get('person'), 
                                            model_choice, client, rewrite, generate_structure_data, prob_identy)
        
    return user_input

def setup_main_page(
    model_choice, client, user_input
):
    display_tags()
    display_rewrite_results()

def display_tags():
    if 'tags' in st.session_state:
        user_generated_tags = re.split(r'[,\s]+', st.session_state.tags.strip())
        user_generated_tags = [tag for tag in user_generated_tags if tag]
        tag_html = " ".join([f'<span class="tag" style="background-color: {match_color(tag, colors, topics)};">{tag}</span>' for tag in user_generated_tags])
        st.markdown(f"**AutoTags:** {tag_html}", unsafe_allow_html=True)
        
        if 'disease_tags' in st.session_state:
            disease_tags = re.split(r'[,\s]+', st.session_state.disease_tags.strip())
            disease_tags = [tag for tag in disease_tags if tag]
            disease_tag_html = ", ".join(disease_tags)
            st.markdown(f"**Disease Tags:** {disease_tag_html}")

def process_rewrite(user_input, institution, department, person, model_choice, client,
                    rewrite, generate_structure_data, prob_identy):
    rewrite_text = rewrite(user_input, institution, department, person, model_choice, client)
    table_text = generate_structure_data(user_input, model_choice, client)
    
    try:
        st.session_state.table_df = json_to_dataframe(table_text)
    except Exception:
        # 只在 JSON 转换失败时静默设置为 None
        st.session_state.table_df = None   
        
    potential_issues = prob_identy(table_text, model_choice, client)
    st.session_state.rewrite_text = rewrite_text
    st.session_state.potential_issues = potential_issues

def display_rewrite_results():
    st.markdown("<p style='font-size: 14px; font-weight: bold;'>Editable Rewritten Text:</p>", unsafe_allow_html=True)

    if 'rewrite_text' in st.session_state:
        user_editable_text = st.text_area("", st.session_state.rewrite_text, height=300)
        st.session_state.rewrite_text = user_editable_text
    else:
        user_editable_text = st.text_area("", placeholder="Rewritten text will appear here after clicking 'Rewrite'\nTip: You can press Ctrl + A to select all the content, then press Ctrl + C to copy it\n\nContent quality may vary\nIf the result is not satisfactory, the 'Rewrite' button can be clicked again for a new attempt", height=300)

    with stylable_container(
        "copy_button",
        css_styles="""
        button {
            background-color: white;
            color: #7A00E6;
            border: 1px solid #7A00E6;
            padding: 5px 10px;
        }"""
    ):
        if st.button("📋 复制"):
            if 'rewrite_text' in st.session_state:
                st.write("请点击下方内容右上角进行复制！")
                st.code(st.session_state.rewrite_text, language=None)
                st.toast("请遵循下面提示进行操作！", icon="😄")
    
    if 'rewrite_text' in st.session_state:
        with st.expander("Assessment Feedback (click for details)"):
            background_color = determine_issue_severity(st.session_state.potential_issues)
            st.markdown(
                f"""
                <div style="background-color: {background_color}; color: black; padding: 10px; border-radius: 5px; font-family: sans-serif; font-size: 12px;">
                    {st.session_state.potential_issues}
                </div>
                """,
                unsafe_allow_html=True
            )
            
            if 'table_df' in st.session_state and st.session_state.table_df is not None:
                st.markdown("<p style='font-size: 12px; font-weight: bold;'>Extracted Information:</p>", unsafe_allow_html=True)
                st.dataframe(st.session_state.table_df)
            else:
                st.warning("No extracted information available.")

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

def generate_comparison(text, model_choice, client, similar_contents):
    """
    Generate comparison between user input and similar contents
    """
    # 构建知识库内容字符串
    knowledge_base = []
    for i, item in enumerate(similar_contents):
        knowledge_base.append(f"[{i+1}] {item['content']}")
    knowledge_base_str = "\n".join(knowledge_base)
    
    completion = client.chat.completions.create(
        model=model_choice,
        messages=[
            {
                "role": "system", 
                "content": """你的职责是比较用户的输入，和知识库内容的相似性和不同，要根据内容本身，尽量不要展开推理，输出格式：
相似观点：xxxx （给出出处index）
不同观点：xxxx。（给出出处index）

整体尽量简洁，如果观点不存在，留位空即可"""
            },
            {
                "role": "user", 
                "content": f"用户输入：{text}\n知识库：{knowledge_base_str}"
            }
        ],
        temperature=0.1,
        max_tokens=1000,
    )
    summary = completion.choices[0].message.content.strip()
    return summary
