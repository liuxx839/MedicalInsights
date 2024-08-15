import streamlit as st
import re
from utils import match_color, determine_issue_severity, create_json_data
from config import json_to_dataframe, get_rewrite_system_message, colors, topics, primary_topics_list
from streamlit_extras.stylable_container import stylable_container

def setup_layout(
    topics, diseases, institutions, departments, persons,
    primary_topics_list, primary_diseases_list,
    generate_tag, generate_diseases_tag, rewrite,
    prob_identy, generate_structure_data,
    model_choice, client
):
    # 将标题放在整个页面最上面的中间，并在后面添加空白行
    st.markdown("""
    <h1 style='text-align: center;'>Medical Insights Copilot</h1>
    <h6 style='text-align: center;'>改写的结果及反馈将呈现在下方，请根据自己的判断进行使用</h6>
    <br><br><br>
    """, unsafe_allow_html=True)
    
    # Sidebar layout
    user_input = setup_sidebar(
        topics, primary_topics_list,
        institutions, departments, persons,  # 添加这些参数
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
    # ## 添加自定义CSS样式来调整sidebar宽度
    # st.markdown("""
    # <style>
    # /* 调整sidebar宽度 */
    # [data-testid="stSidebar"][aria-expanded="true"] {
    #     width: 90%;
    # }
    # [data-testid="stSidebar"][aria-expanded="false"] {
    #     width: 90%;
    #     margin-left: -90%;
    # }
    # /* 修改按钮样式 */
    # .stButton > button {
    #     background-color: #7A00E6;
    #     color: white;
    # }
    # </style>
    # """, unsafe_allow_html=True)

    with st.sidebar:
        ## 原有的markdown内容
        st.markdown("""
        <div style="font-size:14px;">
        * Insight应涵盖4W要素（Who-谁、What-什么、Why-为什么、Wayfoward-未来方向）。<br>
        以下是一个合格样式的示例："一位{脱敏机构}的{科室}的{脱敏人物}指出{观点}，并阐述了{内容间的逻辑联系}，进而提出了{后续方案}"。<br>
        * Insight Copilot：您可以在下面提交您的初稿，然后使用此工具对内容进行打标或者重写。您还可以直接修改重写后的结果。
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("## **Step 1: 请根据上面的4W要求填写您的Insight初稿 ✏️:**")
        user_input = st.text_area("",placeholder="请输入内容", key="user_input", height=200)
        st.markdown("## **Step 2: 请根据拜访，选择如下信息用于Rewrite🧑‍⚕️**")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.session_state.institution = st.selectbox("Institution", institutions)
        with col2:
            st.session_state.department = st.selectbox("Department", departments)
        with col3:
            st.session_state.person = st.selectbox("Title", persons)

        col1, col2 = st.columns(2)
        with col1:
            # if st.button("Generate Tags (Optional)"):
            #     tags = generate_tag(user_input, model_choice, client)
            #     unique_tags = list(set(tags.split(",")))
            #     st.session_state.tags = ",".join(unique_tags)

            #     disease_tags = generate_diseases_tag(user_input, model_choice, client)
            #     unique_disease_tags = list(set(disease_tags.split(",")))
            #     st.session_state.disease_tags = ",".join(unique_disease_tags)
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
            # if st.button("Step 3: Rewrite →"):
            #     process_rewrite(user_input, st.session_state.get('institution'), 
            #                     st.session_state.get('department'), st.session_state.get('person'), 
            #                     model_choice, client, rewrite, generate_structure_data, prob_identy)
            
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

    ####disable download
    # use_generated_text_and_tags = st.checkbox("Use Editable Rewritten Text and AutoTags", value=True)

    # st.download_button(
    #     label="Download JSON",
    #     data=create_json_data(use_generated_text_and_tags, st.session_state, user_input, []),
    #     file_name="medical_insights.json",
    #     mime="application/json"
    # )

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
        st.subheader("Editable Rewritten Text:")
        user_editable_text = st.text_area("", st.session_state.rewrite_text, height=300)
        st.session_state.rewrite_text = user_editable_text

        with st.expander("Assessment Feedback (click for details)"):
            background_color = determine_issue_severity(st.session_state.potential_issues)
            st.markdown(
                f"""
                <div style="background-color: {background_color}; color: black; padding: 10px; border-radius: 5px; font-family: sans-serif;">
                    {st.session_state.potential_issues}
                </div>
                """,
                unsafe_allow_html=True
            )
            
            # 添加 table_df 的显示
            if 'table_df' in st.session_state and st.session_state.table_df is not None:
                st.markdown("<h3 style='font-size: 13px; font-weight: 800;'>Extracted Information:</h3>", unsafe_allow_html=True)
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
    
