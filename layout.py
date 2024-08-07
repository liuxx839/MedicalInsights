import streamlit as st
import re
from utils import match_color, determine_issue_severity, create_json_data
from config import json_to_dataframe, get_rewrite_system_message, colors, topics, primary_topics_list

def setup_layout(
    topics, diseases, institutions, departments, persons,
    primary_topics_list, primary_diseases_list,
    generate_tag, generate_diseases_tag, rewrite,
    prob_identy, generate_structure_data,
    model_choice, client
):
    # 将标题放在整个页面最上面的中间
    st.markdown("<h1 style='text-align: center;'>Medical Insights Tagging & Rewrite</h1>", unsafe_allow_html=True)
    
    # Sidebar layout
    user_input = setup_sidebar(
        topics, primary_topics_list,
        generate_tag, generate_diseases_tag, rewrite,
        prob_identy, generate_structure_data,
        model_choice, client
    )
    
    # Main page layout
    setup_main_page(
        institutions, departments, persons,
        model_choice, client, user_input
    )

def setup_sidebar(
    topics, primary_topics_list,
    generate_tag, generate_diseases_tag, rewrite,
    prob_identy, generate_structure_data,
    model_choice, client
):
    with st.sidebar:
        st.markdown("""
        <div style="font-size:14px;">
        - Insight应涵盖4W要素（Who-谁、What-什么、Why-为什么、Wayfoward-未来方向）。<br>
        以下是一个合格样式的示例："一位{脱敏机构}的{科室}的{脱敏人物}指出{观点}，并阐述了{内容间的逻辑联系}，进而提出了{后续方案}"。<br>
        - Insight Copilot：您可以在下面提交您的初稿，然后使用此工具对内容进行打标或者重写。您还可以直接修改重写后的结果。
        </div>
        """, unsafe_allow_html=True)

        st.markdown("## **Enter Medical Insights:**")
        user_input = st.text_area("", key="user_input", height=200)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Generate Tags"):
                tags = generate_tag(user_input, model_choice, client)
                unique_tags = list(set(tags.split(",")))
                st.session_state.tags = ",".join(unique_tags)

                disease_tags = generate_diseases_tag(user_input, model_choice, client)
                unique_disease_tags = list(set(disease_tags.split(",")))
                st.session_state.disease_tags = ",".join(unique_disease_tags)

        with col2:
            if st.button("ReWrite"):
                process_rewrite(user_input, st.session_state.get('institution'), 
                                st.session_state.get('department'), st.session_state.get('person'), 
                                model_choice, client, rewrite, generate_structure_data, prob_identy)

    return user_input

def setup_main_page(
    institutions, departments, persons,
    model_choice, client, user_input
):
    st.markdown("### 请根据拜访，选择如下信息用于rewrite")
    
    # 创建三列
    col1, col2, col3 = st.columns(3)

    # 在每列中放置一个选择框
    with col1:
        st.session_state.institution = st.selectbox("Select Institution", institutions)
    
    with col2:
        st.session_state.department = st.selectbox("Select Department", departments)
    
    with col3:
        st.session_state.person = st.selectbox("Select Title", persons)

    display_tags()
    display_rewrite_results()

    use_generated_text_and_tags = st.checkbox("Use Editable Rewritten Text and AutoTags", value=True)

    st.download_button(
        label="Download JSON",
        data=create_json_data(use_generated_text_and_tags, st.session_state, user_input, []),
        file_name="medical_insights.json",
        mime="application/json"
    )

# 其余函数保持不变
def display_tags():
    # ... (保持不变)

def process_rewrite(user_input, institution, department, person, model_choice, client,
                    rewrite, generate_structure_data, prob_identy):
    # ... (保持不变)

def display_rewrite_results():
    # ... (保持不变)
