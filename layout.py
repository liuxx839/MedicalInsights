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

# api_key = os.environ.get("GROQ_API_KEY")
# client = Groq(api_key=api_key)
api_key = os.environ.get("ZHIPU_API_KEY")
client = ZhipuAI(api_key=api_key)

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
    if client is None:
        raise ValueError("Groq client must be provided")

    try:
        # 复制图片对象以避免修改原始图片
        image_to_process = user_image.copy()
        base64_image = encode_image(image_to_process)
        
        response = client.chat.completions.create(
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
        model_choice, client
    )
    
    # Main page layout
    setup_main_page(
        model_choice, client, user_input
    )

def setup_sidebar(
    topics, primary_topics_list, institutions, departments, persons,
    generate_tag, generate_diseases_tag, rewrite,
    prob_identy, generate_structure_data,
    model_choice, client
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
        
        with tab2:
            uploaded_file = st.file_uploader("上传图片", type=['png', 'jpg', 'jpeg'])
            if uploaded_file is not None:
                # 显示上传的图片
                image = Image.open(uploaded_file)
                st.image(image, caption="上传的图片", use_column_width=True)
                
                # 处理图片并提取文字
                try:
                    extracted_text = readimg(image)
                    user_input = extracted_text
                    st.text_area("提取的文字", extracted_text, height=200, key="extracted_text")
                except Exception as e:
                    st.error(f"图片处理出错: {str(e)}")
                    user_input = ""

        # 只保留清除按钮
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
    try:
        table_text = generate_structure_data(user_input, model_choice, client)
        st.session_state.table_df = json_to_dataframe(table_text)
    except Exception as e:
        st.error(f"生成表格数据时出错: {str(e)}")
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
        user_editable_text = st.text_area("", placeholder="Rewritten text will appear here after clicking 'Rewrite'\nTip: You can press Ctrl + A to select all the content, then press Ctrl + C to copy it\n\nIf the result is not satisfactory, the 'Rewrite' button can be clicked again for a new attempt", height=300)

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
