import streamlit as st
import re
import time
from PIL import Image
from utils import match_color, determine_issue_severity, create_json_data
from config import json_to_dataframe, get_rewrite_system_message, colors, topics, primary_topics_list
from streamlit_extras.stylable_container import stylable_container

def readimg(user_image, model_choice='llama-3.2-90b-vision-preview', client=None):
    completion = client.chat.completions.create(
        model=model_choice,
        messages=[
            {"role": "system", "content": '提取图片里的文字'},
            {"role": "user", "content": user_image}
        ],
        temperature=0.1,
        max_tokens=1200,
    )
    summary = completion.choices[0].message.content
    return summary

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
        
        # Add tabs for text input and image upload
        tab1, tab2 = st.tabs(["文字输入", "图片上传"])
        
        # 在创建文本框之前检查是否需要清除
        if "clear_clicked" not in st.session_state:
            st.session_state.clear_clicked = False
            
        # Generate dynamic key for text input
        if st.session_state.clear_clicked:
            key = "user_input_" + str(hash(time.time()))
            st.session_state.clear_clicked = False
        else:
            key = "user_input"
            
        with tab1:
            # Text input
            user_input = st.text_area(
                "", 
                placeholder="请输入内容\n提示：您可以按下 Ctrl + A 全选内容，接着按下 Ctrl + C 复制", 
                key=key, 
                height=200
            )
            
        with tab2:
            # Image upload
            uploaded_file = st.file_uploader("上传图片", type=['png', 'jpg', 'jpeg'])
            if uploaded_file is not None:
                # Display the uploaded image
                image = Image.open(uploaded_file)
                st.image(image, caption="上传的图片", use_column_width=True)
                
                # Process the image and extract text
                try:
                    user_input = readimg(image, model_choice, client)
                    st.text_area("提取的文字", user_input, height=200)
                except Exception as e:
                    st.error(f"图片处理出错: {str(e)}")
                    user_input = ""

        # Clear button
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
        
        # Rest of the sidebar content remains the same
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
