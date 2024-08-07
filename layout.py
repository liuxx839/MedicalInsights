#layout.py
import streamlit as st
import re
from utils import match_color, determine_issue_severity, create_json_data
from config import json_to_dataframe, get_rewrite_system_message, colors,topics,primary_topics_list

def setup_layout(
    topics, diseases, institutions, departments, persons,
    primary_topics_list, primary_diseases_list,
    generate_tag, generate_diseases_tag, rewrite,
    prob_identy, generate_structure_data,
    model_choice, client
):
    st.title("Medical Insights Tagging & Rewrite")
    
    # Sidebar layout
    user_input, primary_topics, secondary_topics = setup_sidebar(
        topics, primary_topics_list,
        generate_tag, generate_diseases_tag,
        model_choice, client
    )
    
    # Main page layout
    setup_main_page(
        topics, institutions, departments, persons,
        rewrite, prob_identy, generate_structure_data,
        model_choice, client, user_input, primary_topics, secondary_topics
    )

def setup_sidebar(
    topics, primary_topics_list,
    generate_tag, generate_diseases_tag,
    model_choice, client
):
    with st.sidebar:
        st.markdown("""
        <div style="font-size:18px; font-weight:bold;">
        - Insight应涵盖4W要素（Who-谁、What-什么、Why-为什么、Wayfoward-未来方向）。<br>
        以下是一个合格样式的示例："一位{脱敏机构}的{科室}的{脱敏人物}指出{观点}，并阐述了{内容间的逻辑联系}，进而提出了{后续方案}"。<br>
        - Insight Copilot：您可以在下面提交您的初稿，然后使用此工具对内容进行打标或者重写。您还可以直接修改重写后的结果。
        </div>
        """, unsafe_allow_html=True)

        user_input = st.text_area("Enter Medical Insights: ")

        if st.button("Generate Tags"):
            tags = generate_tag(user_input, model_choice, client)
            unique_tags = list(set(tags.split(",")))
            st.session_state.tags = ",".join(unique_tags)

            disease_tags = generate_diseases_tag(user_input, model_choice, client)
            unique_disease_tags = list(set(disease_tags.split(",")))
            st.session_state.disease_tags = ",".join(unique_disease_tags)

        primary_topics = st.multiselect("Select Primary Topics", primary_topics_list)
        
        secondary_topics = {}
        if primary_topics:
            for topic in primary_topics:
                secondary_topics[topic] = st.multiselect(f"Select Secondary Topics for {topic}", topics[topic])

    return user_input, primary_topics, secondary_topics

def setup_main_page(
    topics, institutions, departments, persons,
    rewrite, prob_identy, generate_structure_data,
    model_choice, client, user_input, primary_topics, secondary_topics
):
    st.write("### Selected Options")
    display_topics(primary_topics, secondary_topics)

     # 创建三列
    col1, col2, col3 = st.columns(3)

    # 在每列中放置一个选择框
    with col1:
        institution = st.selectbox("Select Institution", institutions)
    
    with col2:
        department = st.selectbox("Select Department", departments)
    
    with col3:
        person = st.selectbox("Select Title", persons)

    display_tags()

    if st.button("ReWrite"):
        process_rewrite(user_input, institution, department, person, model_choice, client,
                        rewrite, generate_structure_data, prob_identy)

    display_rewrite_results()

    use_generated_text_and_tags = st.checkbox("Use Editable Rewritten Text and AutoTags", value=True)

    st.download_button(
        label="Download JSON",
        data=create_json_data(use_generated_text_and_tags, st.session_state, user_input, primary_topics),
        file_name="medical_insights.json",
        mime="application/json"
    )

def display_topics(primary_topics, secondary_topics):
    primary_topic_tags = [f'<span class="tag" style="background-color: {colors[topic]};">{topic}</span>' for topic in primary_topics]
    st.markdown(f"**Primary Topics:** {' '.join(primary_topic_tags)}", unsafe_allow_html=True)

    secondary_topic_tags = []
    for topic, subtopics in secondary_topics.items():
        for subtopic in subtopics:
            secondary_topic_tags.append(f'<span class="tag" style="background-color: {colors[topic]};">{subtopic}</span>')
    st.markdown(f"**Secondary Topics:** {' '.join(secondary_topic_tags)}", unsafe_allow_html=True)

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

        st.subheader("Extracted Information:")
        if 'table_df' in st.session_state:
            st.dataframe(st.session_state.table_df)

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
