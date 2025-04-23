#main.py
import streamlit as st
from layout import setup_layout
from functions import (
    setup_client, generate_tag, generate_diseases_tag, rewrite,
    prob_identy, generate_structure_data
)
from config import (
    topics, diseases, institutions, departments, persons,
    primary_topics_list, primary_diseases_list,colors
)
from streamlit_extras.stylable_container import stylable_container
import pandas as pd
import json
import time
import ast
import io
from openai import OpenAI
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
from dagrelation import DAGRelations
from datadescription import DataDescription

# Add at the top of the file with other imports
import numpy as np
from datetime import datetime
from prophet import Prophet
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import base64
from io import BytesIO
import re

model_choice_research, client_research = setup_client(model_choice = 'gemini-2.0-flash')
 
def create_mermaid_html_from_edges(dag_edges):
    """
    Create a Mermaid flowchart HTML from a list of edges.
    
    Parameters:
    dag_edges (list): List of tuples representing edges. Each tuple can be:
                     - ('var1', 'var2') for a single edge
                     - (['var1', 'var2'], 'var3') for multiple sources to one target
    
    Returns:
    str: HTML code with embedded Mermaid flowchart
    """
    mermaid_code = ['flowchart TD']
    
    for edge in dag_edges:
        if isinstance(edge[0], list):
            # Handle multiple sources to one target
            source_vars = edge[0]
            target_var = edge[1]
            
            # Create individual connections for each source to target
            for source_var in source_vars:
                mermaid_code.append(f'    {source_var} --> {target_var}')
        else:
            # Simple one-to-one edge
            source_var = edge[0]
            target_var = edge[1]
            mermaid_code.append(f'    {source_var} --> {target_var}')
    
    # Join all lines with newlines
    mermaid_code_str = '\n'.join(mermaid_code)
    
    # Create the HTML with the embedded Mermaid code and zoom controls
    mermaid_html = f"""
<div id="mermaid-container" style="width:100%; height:100%; position:relative;">
    <div class="mermaid" id="mermaid-diagram">
    {mermaid_code_str}
    </div>
    
    <div style="position:absolute; top:10px; right:10px; background:white; padding:5px; border:1px solid #ccc; border-radius:5px;">
        <button onclick="zoomIn()" style="margin-right:5px;">➕</button>
        <button onclick="zoomOut()">➖</button>
        <button onclick="resetZoom()" style="margin-left:5px;">🔄</button>
    </div>
</div>

<script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
    mermaid.initialize({{ startOnLoad: true }});
    
    window.currentZoom = 1;
    
    window.zoomIn = function() {{
        window.currentZoom += 0.1;
        document.getElementById('mermaid-diagram').style.transform = `scale(${{window.currentZoom}})`;
        document.getElementById('mermaid-diagram').style.transformOrigin = 'top left';
    }};
    
    window.zoomOut = function() {{
        if (window.currentZoom > 0.5) {{
            window.currentZoom -= 0.1;
            document.getElementById('mermaid-diagram').style.transform = `scale(${{window.currentZoom}})`;
            document.getElementById('mermaid-diagram').style.transformOrigin = 'top left';
        }}
    }};
    
    window.resetZoom = function() {{
        window.currentZoom = 1;
        document.getElementById('mermaid-diagram').style.transform = 'scale(1)';
    }};
</script>
"""
    
    return mermaid_html
    
def create_word_document(qa_response, fact_check_result=None):
    """
    创建包含QA响应和事实核查结果的Word文档，支持Markdown标题转换为Word样式
    """
    doc = Document()
    
    # 设置标题
    title = doc.add_heading('Medical Knowledge Base Q&A Report', 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # 添加时间戳
    timestamp = doc.add_paragraph()
    timestamp.add_run(f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}").italic = True
    
    # 添加QA响应
    doc.add_heading('回应内容', level=1)
    
    # 处理QA响应中的Markdown格式
    lines = qa_response.split('\n')
    current_text = []
    
    for line in lines:
        # 检查是否是标题行
        if line.strip().startswith('#'):
            # 如果之前有累积的文本，先添加为段落
            if current_text:
                doc.add_paragraph(''.join(current_text))
                current_text = []
            
            # 计算标题级别
            level = 1
            line = line.strip()
            while line.startswith('#'):
                level += 1
                line = line[1:]
            level = min(level, 9)  # Word支持最多9级标题
            
            # 移除可能的引用标记 [1,2,3] 并保存
            citation = ''
            if '[' in line and ']' in line:
                main_text = line[:line.find('[')].strip()
                citation = line[line.find('['):].strip()
                heading = doc.add_heading(main_text, level=level-1)
                if citation:
                    heading.add_run(f" {citation}").italic = True
            else:
                doc.add_heading(line.strip(), level=level-1)
        else:
            current_text.append(line + '\n')
    
    # 添加最后剩余的文本
    if current_text:
        doc.add_paragraph(''.join(current_text))
    
    # 如果有事实核查结果，添加到文档
    if fact_check_result:
        doc.add_heading('事实核查结果', level=1)
        # 对事实核查结果也进行相同的处理
        lines = fact_check_result.split('\n')
        current_text = []
        
        for line in lines:
            if line.strip().startswith('#'):
                if current_text:
                    doc.add_paragraph(''.join(current_text))
                    current_text = []
                
                level = 1
                line = line.strip()
                while line.startswith('#'):
                    level += 1
                    line = line[1:]
                level = min(level, 9)
                
                if '[' in line and ']' in line:
                    main_text = line[:line.find('[')].strip()
                    citation = line[line.find('['):].strip()
                    heading = doc.add_heading(main_text, level=level-1)
                    if citation:
                        heading.add_run(f" {citation}").italic = True
                else:
                    doc.add_heading(line.strip(), level=level-1)
            else:
                current_text.append(line + '\n')
        
        if current_text:
            doc.add_paragraph(''.join(current_text))
    
    # 保存到内存中
    doc_io = io.BytesIO()
    doc.save(doc_io)
    doc_io.seek(0)
    return doc_io

def extract_dag_edges(text_content):
    # 从文本中提取 dag_edges 部分
    if "dag_edges = [" in text_content:
        start_idx = text_content.find("dag_edges = [")
        start_idx = text_content.find("[", start_idx)
        
        # 找到匹配的结束括号
        open_brackets = 1
        end_idx = start_idx + 1
        
        while open_brackets > 0 and end_idx < len(text_content):
            if text_content[end_idx] == '[':
                open_brackets += 1
            elif text_content[end_idx] == ']':
                open_brackets -= 1
            end_idx += 1
        
        # 提取 dag_edges 列表内容
        dag_edges_str = text_content[start_idx:end_idx]
        
        # 使用 ast.literal_eval 安全地将字符串转换为 Python 对象
        try:
            dag_edges = ast.literal_eval(dag_edges_str)
            return dag_edges
        except (SyntaxError, ValueError) as e:
            print(f"解析错误: {e}")
            return None
    
    return None

def setup_spreadsheet_analysis():
    st.markdown(
        """
    <h1 style='text-align: center; font-size: 18px; font-weight: bold;'>Spreadsheet Analysis</h1>
    <h6 style='text-align: center; font-size: 12px;'>上传Excel/CSV文件或粘贴JSON数据进行分析</h6>
    <br><br><br>
    """,
        unsafe_allow_html=True,
    )
    
    # Initialize all session state variables
    if "analysis_response" not in st.session_state:
        st.session_state.analysis_response = ""
    if "analysis_reasoning" not in st.session_state:
        st.session_state.analysis_reasoning = ""
    if "dag_edges" not in st.session_state:
        st.session_state.dag_edges = ""
    if "sample_data" not in st.session_state:
        st.session_state.sample_data = {}
    if "business_report" not in st.session_state:
        st.session_state.business_report = ""
    if "dag_report" not in st.session_state:
        st.session_state.dag_report = ""
    if "dag_reasoning" not in st.session_state:
        st.session_state.dag_reasoning = ""
    if "df" not in st.session_state:
        st.session_state.df = None
    
    # Create tabs for different input methods
    tab1, tab2 = st.tabs(["文件上传", "JSON粘贴"])
    
    with tab1:
        uploaded_file = st.file_uploader("上传文件(xlsx/csv)", type=['xlsx', 'csv'])
        
        if uploaded_file is not None:
            try:
                # 根据文件类型读取数据
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)
                    
                # 处理列名，将空格和特殊符号替换为下划线
                df.columns = [re.sub(r'[^\w]', '_', col) for col in df.columns]
                
                # 保存DataFrame到session state
                st.session_state.df = df
                
                # 显示前10行数据
                st.write("数据预览:")
                st.dataframe(df)
                
                # 保存sample数据到session state
                st.session_state.sample_data = df.sample(10).to_dict()
                
            except Exception as e:
                st.error(f"处理文件时出错: {str(e)}")
    
    with tab2:
        json_input = st.text_area("粘贴JSON数据:", height=200)
        process_json_button = st.button("处理JSON数据")
        
        if process_json_button and json_input:
            try:
                # 清理JSON字符串 - 如果前后有额外的引号，去掉它们
                cleaned_json = json_input.strip()
                if cleaned_json.startswith('"') and cleaned_json.endswith('"'):
                    # 如果JSON被额外的引号包围，去掉这些引号并处理转义字符
                    cleaned_json = cleaned_json[1:-1].replace('\\"', '"')
                
                # 解析JSON数据
                try:
                    json_data = json.loads(cleaned_json)
                    df = pd.DataFrame(json_data)
                except Exception as e:
                    # 如果第一次尝试失败，尝试以Records格式解析
                    try:
                        json_data = json.loads(cleaned_json)
                        if isinstance(json_data, list):
                            df = pd.DataFrame(json_data)
                        else:
                            df = pd.DataFrame([json_data])
                    except:
                        st.error(f"无法解析JSON数据: {str(e)}")
                        return
                
                # 保存DataFrame到session state
                st.session_state.df = df
                
                # 显示前10行数据
                st.write("数据预览:")
                st.dataframe(df)
                
                # 保存sample数据到session state
                st.session_state.sample_data = df.head(10).to_dict()
                
            except Exception as e:
                st.error(f"处理JSON数据时出错: {str(e)}")
    
    # 只有当DataFrame可用时才显示下面的控件
    if st.session_state.df is not None:
        # 用户输入需求
        user_question = st.text_area("请输入您的需求:", height=100)
        
        # 创建两列布局，一列放生成按钮，一列放DAG分析按钮
        col1, col2 = st.columns(2)
        
        with col1:
            # 根据是否已经进行过DAG分析来显示不同的按钮文本
            button_text = "再次生成" if "business_report" in st.session_state and st.session_state.business_report else "生成"
            generate_button = st.button(button_text)
        
        with col2:
            with stylable_container(
                "dag_analysis_button",
                css_styles="""
                    button {
                        background-color: #FFA500;
                        color: white;
                    }""",
            ):
                dag_analysis_button = st.button("📊 DAG分析")
        
        # 确保有DataFrame可用于分析
        df = st.session_state.df
        
        # 处理生成按钮点击
        if generate_button and user_question:
            with st.spinner("正在分析..."):
                # 根据是否已经有business_report来决定使用哪个提示
                if "business_report" in st.session_state and st.session_state.business_report:
                    # 使用已有的business_report作为输入，重新思考DAG结构
                    response = client_research.chat.completions.create(
                        model=model_choice_research,
                        messages=[
                            {
                                "role": "system",
                                "content": """你是一个数据分析专家。请基于提供的sample数据和已有的分析报告，重新思考并优化DAG关系。
                                关注以下几点：
                                1. 仔细分析已有报告中的发现和关系
                                2. 重新评估可能的因果关系
                                3. 构建更优化的DAG边
                                4. 支持多对一的关系
                                5. 确保使用的是原始的列名，不要做任何修改
                                6. 考虑已有分析中可能被忽略的关系
                                7. 不要增加任何不存在的列名

                                请先提供详细的推理过程，然后再给出优化后的DAG定义。

                                最终输出格式必须如下：
                                ##推理过程
                                [详细的分析推理过程，包括对已有分析的评估]

                                ##定义DAG边（支持多对一关系）
                                请严格遵循下面的格式，仔细核对，务必保证使用原始列名，以及正确的括号
                                dag_edges = [
                                    ('var1', 'var2'),
                                    ('var3', 'var4'),
                                    # 多对一关系示例
                                    (['var1', 'var2'], 'var3'),
                                    (['var1', 'var2', 'var3'], 'var4')
                                ]
                                
                                ##分析说明：
                                [这里是对优化后DAG结构的解释说明，以及与之前分析的比较]
                                """
                            },
                            {
                                "role": "user",
                                "content": f"Sample数据：\n{st.session_state.sample_data}\n\n用户需求：{user_question}\n\n已有分析报告：\n{st.session_state.business_report}"
                            }
                        ],
                        temperature=0.7,
                        max_tokens=2000,
                        stream=True
                    )
                else:
                    # 原有的提示，用于首次生成
                    response = client_research.chat.completions.create(
                        model=model_choice_research,
                        messages=[
                            {
                                "role": "system", 
                                "content": """
                                你是一个数据分析专家。请基于提供的sample数据分析用户需求，并构建潜在的DAG关系。
                                关注以下几点：
                                0. 确保充分理解用户的需求，DAG构建围绕用户的需求
                                1. 仔细分析数据列之间的关系
                                2. 识别可能的因果关系
                                3. 构建合适的DAG边
                                4. 支持多对一的关系
                                5. 确保使用的是原始的列名，不要做任何修改
                                6. 不要增加任何不存在的列名

                                最终输出格式必须如下：

                                ## 推理过程
                                [首先复述用户的需求是什么]
                                [详细的分析推理过程]

                                ## 定义DAG边（支持多对一关系）
                                请严格遵循下面的格式，仔细核对，务必保证使用原始列名，以及正确的括号
                                dag_edges = [
                                    ('var1', 'var2'),
                                    ('var3', 'var4'),
                                    # 多对一关系示例
                                    (['var1', 'var2'], 'var3'),
                                    (['var1', 'var2', 'var3'], 'var4')
                                ]


                                ## 分析说明：
                                [这里是对DAG结构的解释说明，包含原则遵循情况分析]
                                """
                            },
                            {
                                "role": "user", 
                                "content": f"Sample数据：\n{st.session_state.sample_data}\n\n用户需求：{user_question}"
                            }
                        ],
                        temperature=0.7,
                        max_tokens=2000,
                        stream=True
                    )
                
                full_response = ""
                reasoning_content = ""
                
                # 创建进度显示的容器
                progress_container = st.empty()
                
                # 处理流式响应
                for chunk in response:
                    if hasattr(chunk.choices[0].delta, 'reasoning_content') and chunk.choices[0].delta.reasoning_content:
                        reasoning_content += chunk.choices[0].delta.reasoning_content
                        progress_container.markdown(f"思考过程：\n{reasoning_content}\n\n回答：\n{full_response}")
                    elif hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                        full_response += chunk.choices[0].delta.content
                        progress_container.markdown(f"思考过程：\n{reasoning_content}\n\n回答：\n{full_response}")
                
                # 仅提取DAG定义部分
                dag_definition = ""
                if "dag_edges = [" in full_response:
                    dag_start = full_response.find("dag_edges = [")
                    
                    # Find the matching closing bracket by counting opening and closing brackets
                    open_brackets = 1
                    dag_end = dag_start + len("dag_edges = [")
                    
                    while open_brackets > 0 and dag_end < len(full_response):
                        if full_response[dag_end] == '[':
                            open_brackets += 1
                        elif full_response[dag_end] == ']':
                            open_brackets -= 1
                        dag_end += 1
                    
                    dag_definition = full_response[dag_start:dag_end]
                
                # 保存到session state
                st.session_state.analysis_response = full_response
                st.session_state.analysis_reasoning = reasoning_content
                st.session_state.dag_edges = dag_definition
                
                # 清空进度容器
                progress_container.empty()
        
        # 处理DAG分析按钮点击
        if dag_analysis_button and st.session_state.dag_edges:
            with st.spinner("正在进行DAG分析..."):
                try:
                    # 执行DAG分析
                    dag_edges_text = st.session_state.dag_edges
                    dag_edges = extract_dag_edges(dag_edges_text)
                    
                    full_response = ""
                    reasoning_content = ""

                    # 创建进度显示的容器
                    dag_progress = st.empty()
                    
                    if dag_edges:
                        # 执行DAG分析
                        analyzer = DAGRelations(df, dag_edges)
                        dag_report = analyzer.analyze_relations().print_report()
                        st.session_state.dag_report = dag_report

                        # 添加数据描述分析
                        data_analyzer = DataDescription(df, include_histogram=False, string_threshold=10)
                        data_analyzer.analyze_data()
                        json_output = data_analyzer.to_json()
                        st.session_state.data_description = json_output

                        # 生成商业报告
                        response = client_research.chat.completions.create(
                            model=model_choice_research,
                            messages=[
                                {
                                    "role": "system",
                                    "content": """你是一位专业的数据分析师。请基于提供的初始分析结果、DAG分析报告和数据描述信息生成一份结构化的分析报告。如果DAG分析报告不存在，请在报告中说明这一情况。

                                        报告结构应包含：

                                        # 执行摘要
                                        简明扼要地总结关键发现和建议（不超过200字）
                                        
                                        # 关键洞察
                                        ## 主要发现
                                        - 发现1: [简明描述] - 支持数据: [相关统计结果]
                                        - 发现2: [简明描述] - 支持数据: [相关统计结果]
                                        - 发现n: ...
                                        
                                        # 数据概览
                                        ## 数据基本情况
                                        以表格形式呈现：
                                        | 数据维度 | 值 |
                                        | --- | --- |
                                        | 总记录数 | X |
                                        | 变量数量 | X |
                                        | 数值型变量 | X个 (列出名称) |
                                        | 分类型变量 | X个 (列出名称) |
                                        | 缺失值情况 | 总体百分比及主要缺失列 |

                                        ## 关键变量分析
                                        针对重要变量以表格形式呈现：

                                        **数值型变量统计**
                                        | 变量名 | 均值 | 中位数 | 标准差 | 最小值 | 最大值 | 异常值比例 |
                                        | --- | --- | --- | --- | --- | --- | --- |

                                        **分类型变量统计**
                                        | 变量名 | 唯一值数量 | 最常见类别(占比) | 熵值(归一化) | 分布均衡度 |
                                        | --- | --- | --- | --- | --- | --- |

                                        # 变量关系分析
                                        ## DAG关系概述
                                        以表格形式呈现主要变量间的关系：

                                        | 关系类型 | 源变量 | 目标变量 | 统计量 | p值 | 显著性 | 关系强度 |
                                        | --- | --- | --- | --- | --- | --- | --- |

                                        ## 详细关系分析
                                        针对每个重要关系，使用以下格式：

                                        ### 关系: [源变量] -> [目标变量]
                                        **统计结果:**
                                        - 关系类型: [分类->数值/数值->数值/分类->分类]
                                        - 统计量: [F值/相关系数/卡方值] = X
                                        - p值: X
                                        - 显著性: [高度显著/显著/不显著]

                                        **类别统计:** (适用于分类->数值关系)
                                        | 类别 | 样本数 | 均值 | 标准差 | 与总体均值差异 |
                                        | --- | --- | --- | --- | --- |

                                        **显著差异类别:**
                                        - 类别X: 均值Y (比总体均值[高/低]Z%)

                                        # 技术附录
                                        ## DAG分析完整报告
                                        [此处直接插入原始DAG报告，不做修改]

                                        请确保：
                                        1. 表格格式清晰，数据对齐
                                        2. 所有统计结果保留适当小数位数(通常2-4位)
                                        3. 对统计显著性使用标准表示: *** p<0.001, ** p<0.01, * p<0.05, ns p≥0.05
                                        4. 对非技术读者解释统计术语，但保持专业性
                                        5. 重点突出异常值、显著差异和有商业价值的发现
                                        6. 所有结论必须有数据支持，避免过度解读
                                        7. 对于复杂关系，提供简明的解释和可能的因果机制
                                        8. 请提供尽可能详细的数据洞察和业务影响分析"""
                                },
                                {
                                    "role": "user",
                                    "content": f"""
                                    初始分析结果：{st.session_state.analysis_response}
                                    DAG分析报告：{dag_report}
                                    数据描述信息：{json_output}
                                    
                                    请基于以上信息生成一份专业的数据分析报告。报告应严格遵循系统提示中的结构和格式要求，特别注意：
                                    1. 充分利用DAG分析报告中的统计结果，包括F值、p值和类别统计
                                    2. 整合数据描述中的统计信息和分布特征
                                    3. 所有表格必须格式规范，数据对齐
                                    4. 重点关注统计显著的关系和异常值
                                    5. 确保非技术人员也能理解报告内容
                                    6. 所有结论和建议必须有数据支持
                                    """
                                }
                            ],
                            temperature=0.7,
                            max_tokens=5000,
                            stream=True
                        )
                        
                        full_response = ""
                        reasoning_content = ""
                        
                        # 处理流式响应
                        for chunk in response:
                            if hasattr(chunk.choices[0].delta, 'reasoning_content') and chunk.choices[0].delta.reasoning_content:
                                reasoning_content += chunk.choices[0].delta.reasoning_content
                                dag_progress.markdown(f"思考过程：\n{reasoning_content}\n\n分析结果：\n{full_response}")
                            elif hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                                full_response += chunk.choices[0].delta.content
                                dag_progress.markdown(f"思考过程：\n{reasoning_content}\n\n分析结果：\n{full_response}")
                        
                        # 保存到session state
                        st.session_state.business_report = full_response + "\n\n# 分析raw results\n" + dag_report + "\n\n# descriptive analysis\n" + json_output
                        st.session_state.dag_reasoning = reasoning_content
                        
                        # 清空进度容器
                        dag_progress.empty()
                        
                except Exception as e:
                    st.error(f"DAG分析过程中出错: {str(e)}")
        
        # 使用两列显示分析结果和DAG分析结果
        if st.session_state.analysis_response or st.session_state.business_report:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### 数据分析")
                if st.session_state.analysis_reasoning:
                    with st.expander("思考过程", expanded=False):
                        st.markdown(st.session_state.analysis_reasoning)
                st.markdown(st.session_state.analysis_response)
                
                # DAG定义编辑器
                st.markdown("### DAG定义")
                dag_editor = st.text_area("编辑DAG边定义:", value=st.session_state.dag_edges, height=200)
                if dag_editor != st.session_state.dag_edges:
                    st.session_state.dag_edges = dag_editor
                # Generate the Mermaid HTML
                try:
                    # 确保先解析文本中的dag_edges
                    dag_edges = extract_dag_edges(st.session_state.dag_edges)
                    if dag_edges:
                        mermaid_html = create_mermaid_html_from_edges(dag_edges)
                        # 渲染 Mermaid 图，并增加高度以适应缩放
                        st.markdown("## 关系图 (使用右上角按钮缩放)")
                        st.components.v1.html(mermaid_html, height=600, scrolling=True)
                    else:
                        st.warning("无法解析DAG边定义，请检查格式是否正确")
                except Exception as e:
                    st.error(f"生成关系图时出错: {str(e)}")
            
            with col2:
                if st.session_state.business_report:
                    st.markdown("### DAG分析结果")
                    if hasattr(st.session_state, 'dag_reasoning'):
                        with st.expander("分析过程", expanded=False):
                            st.markdown(st.session_state.dag_reasoning)
                    st.markdown(st.session_state.business_report)
            
            # 添加下载按钮
            if st.session_state.business_report:
                st.markdown("---")
                st.download_button(
                    label="📥 下载分析报告",
                    data=create_word_document(st.session_state.business_report),
                    file_name=f"data_analysis_report_{time.strftime('%Y%m%d_%H%M%S')}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )

# Add this function before the main() function
def setup_sales_forecasting():
    st.markdown(
        """
    <h1 style='text-align: center; font-size: 18px; font-weight: bold;'>Sales Forecasting Application</h1>
    <h6 style='text-align: center; font-size: 12px;'>Upload your Excel file to forecast sales or other time series data</h6>
    <br><br><br>
    """,
        unsafe_allow_html=True,
    )

    np.random.seed(42)
    
    # Initialize session state for storing results between interactions
    if 'forecast_df' not in st.session_state:
        st.session_state.forecast_df = None
    if 'all_groups' not in st.session_state:
        st.session_state.all_groups = []
    if 'has_forecast' not in st.session_state:
        st.session_state.has_forecast = False
    if 'target_column' not in st.session_state:
        st.session_state.target_column = None
    if 'original_filename' not in st.session_state:
        st.session_state.original_filename = None
    if 'training_accuracy' not in st.session_state:
        st.session_state.training_accuracy = {}
    if 'validation_accuracy' not in st.session_state:
        st.session_state.validation_accuracy = {}
    if 'start_date_str' not in st.session_state:
        st.session_state.start_date_str = None
    if 'training_end_date_str' not in st.session_state:
        st.session_state.training_end_date_str = None
    
    st.markdown("""
    This app helps you forecast sales or other time series data using Facebook Prophet.
    Upload your Excel file, configure the settings, and get predictions for future periods.
    """)
    
    # File uploader
    uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx", "xls"])
    
    if uploaded_file is not None:
        # Store original filename
        if st.session_state.original_filename is None:
            st.session_state.original_filename = uploaded_file.name.split('.')[0]
            
        # Load the file and display sheet selection
        excel_file = pd.ExcelFile(uploaded_file)
        sheet_name = st.selectbox("Select Sheet", excel_file.sheet_names)
        
        # Read the selected sheet
        df = pd.read_excel(uploaded_file, sheet_name=sheet_name)
        
        # Display data preview
        st.subheader("Data Preview")
        st.dataframe(df.head())
        
        # Basic data info
        st.subheader("Dataset Information")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"Number of rows: {df.shape[0]}")
        with col2:
            st.write(f"Number of columns: {df.shape[1]}")
        
        # Column selection and configuration
        st.subheader("Configure Forecasting Parameters")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Date column selection
            date_column_options = df.columns.tolist()
            date_column = st.selectbox("Select Date/Month Column", date_column_options)
            
            # Date format selection
            date_format_options = [
                "%Y%m", "%Y-%m", "%b %Y", "%B %Y", 
                "%Y%m%d", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y"
            ]
            date_format = st.selectbox("Select Date Format", date_format_options)
            
            # Target column (to be predicted)
            numeric_columns = df.select_dtypes(include=['number']).columns.tolist()
            target_column = st.selectbox("Select Target Column to Forecast", numeric_columns)
            st.session_state.target_column = target_column
            
            # Start date for training
            min_date = pd.to_datetime("2020-01-01")  # Default minimum date
            max_date = datetime.now()
            start_date = st.date_input("Training Start Date", 
                                      value=pd.to_datetime("2022-01-01"),
                                      min_value=min_date,
                                      max_value=max_date)
            
        
        with col2:
            # Grouping columns (multi-select)
            all_columns = df.columns.tolist()
            grouping_columns = st.multiselect("Select Columns for Grouping (Optional)", all_columns)
    
            # Forecast horizon
            forecast_years = st.number_input("Forecast Horizon (Years)", min_value=1, max_value=10, value=3)
            
            # Add a forecast end date input
            current_date = datetime.now()
            default_end_date = current_date.replace(day=1) + pd.DateOffset(years=forecast_years) - pd.DateOffset(days=1)
            end_date = st.date_input("Forecast End Date", 
                                    value=default_end_date,
                                    min_value=current_date)
            
            # Hidden Confidence Interval Width (not displayed in UI)
            interval_width = 0.6  # Set default to 0.6 as requested
            
            # Add a training end date input at the bottom of col2
            training_end_date = st.date_input("Training End Date", 
                                    value=current_date,
                                    min_value=start_date,
                                    max_value=current_date)
        
        # Run forecast button
        if st.button("Run Forecast") or st.session_state.has_forecast:
            if not st.session_state.has_forecast:
                try:
                    # Progress bar
                    progress_bar = st.progress(0)
                    
                    # Copy the dataframe to avoid modifying the original
                    df_copy = df.copy()
                    
                    # Process date column
                    st.info("Processing date column...")
                    try:
                        df_copy['date'] = pd.to_datetime(df_copy[date_column].astype(str), format=date_format)
                    except:
                        df_copy['date'] = pd.to_datetime(df_copy[date_column].astype(str))
                        
                    # Store the original date format from the column
                    original_date_values = df_copy[date_column].copy()
                        
                    progress_bar.progress(10)
                    
                    # Create grouping key if group columns are selected
                    if grouping_columns:
                        st.info("Creating group combinations...")
                        df_copy['group'] = df_copy[grouping_columns[0]].astype(str)
                        for col in grouping_columns[1:]:
                            df_copy['group'] += '_' + df_copy[col].astype(str)
                    else:
                        # If no grouping is selected, create a single group
                        df_copy['group'] = 'all_data'
                        
                    progress_bar.progress(20)
                    
                    # Get current date and calculate end date for forecasting
                    current_date = datetime.now()
                    end_date_str = end_date.strftime('%Y-%m-%d')
                    training_end_date_str = training_end_date.strftime('%Y-%m-%d')
                    start_date_str = start_date.strftime('%Y-%m-%d')
                    
                    # Store date strings in session state for later use
                    st.session_state.start_date_str = start_date_str
                    st.session_state.training_end_date_str = training_end_date_str
                    
                    # Create complete date and group combinations
                    st.info("Creating complete date-group combinations...")
                    # 修改: 确保生成的日期范围始终延伸到预测结束日期
                    all_dates = pd.date_range(start=df_copy['date'].min(), end=end_date_str, freq='MS')
                    all_groups = df_copy['group'].unique()
                    st.session_state.all_groups = all_groups.tolist()
                    
                    complete_df = pd.DataFrame([(date, group) for date in all_dates for group in all_groups],
                                              columns=['date', 'group'])
                    
                    # Merge with original data
                    df_copy = pd.merge(complete_df, df_copy, on=['date', 'group'], how='left')
                    
                    # Fill missing values for target column with 0
                    df_copy[target_column] = df_copy[target_column].fillna(0)
                    
                    # Forward fill other columns within groups
                    if grouping_columns:
                        for col in grouping_columns:
                            df_copy[col] = df_copy.groupby('group')[col].ffill().bfill()
                            
                    progress_bar.progress(40)
                    
                    # Sort data
                    df_copy = df_copy.sort_values(by=['group', 'date'], ascending=[True, True])
                    
                    # Convert dates to string format
                    current_date_str = current_date.strftime("%Y-%m-%d")
                    
                    # Run Prophet forecast for each group
                    st.info("Running forecasts for each group...")
                    forecasts = {}
                    training_accuracy = {}
                    validation_accuracy = {}
                    total_groups = len(all_groups)
                    
                    for i, group in enumerate(all_groups):
                        # Update progress based on group progress
                        progress_value = 40 + (i / total_groups * 50)
                        progress_bar.progress(int(progress_value))
                        
                        # Filter data for this group - using the start_date parameter
                        group_data = df_copy[(df_copy['group'] == group) & 
                                           (df_copy['date'] >= start_date_str) & 
                                           (df_copy['date'] <= training_end_date_str)].copy()
                        
                        group_data = group_data.rename(columns={'date': 'ds', target_column: 'y'})
                        
                        # Fit Prophet model
                        model = Prophet(interval_width=interval_width, uncertainty_samples=1000, mcmc_samples=300)
                        # model = Prophet(interval_width=interval_width)
                        try:
                            model.fit(group_data[['ds', 'y']])
                            
                            # 修改: 直接使用预测结束日期来创建future dataframe
                            future_end_date = pd.to_datetime(end_date_str)
                            # 创建从训练数据开始到预测结束日期的完整日期范围
                            future_dates = pd.date_range(start=group_data['ds'].min(), end=future_end_date, freq='MS')
                            future = pd.DataFrame({'ds': future_dates})
                            
                            # Make forecast
                            forecast = model.predict(future)
                            
                            forecasts[group] = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']]
                        except Exception as e:
                            st.warning(f"Could not forecast for group {group}: {str(e)}")
                            # Create empty forecast data for this group
                            forecasts[group] = pd.DataFrame({
                                'ds': all_dates,
                                'yhat': np.zeros(len(all_dates)),
                                'yhat_lower': np.zeros(len(all_dates)),
                                'yhat_upper': np.zeros(len(all_dates))
                            })
                    
                    progress_bar.progress(90)
                    
                    # Write forecasts back to the dataframe using direct array assignment
                    st.info("Combining results...")
                    for group, forecast in forecasts.items():
                        # Use date matching approach instead of direct array assignment
                        for i, row in forecast.iterrows():
                            forecast_date = row['ds']
                            # Match both group and date
                            mask = (df_copy['group'] == group) & (df_copy['date'] == forecast_date)
                            # Assign forecast values
                            df_copy.loc[mask, 'forecast'] = row['yhat']
                            df_copy.loc[mask, 'forecast_lower'] = row['yhat_lower']
                            df_copy.loc[mask, 'forecast_upper'] = row['yhat_upper']
                    
                    # Format dates in the original date column according to the selected format
                    # This preserves the original date format while extending to future dates
                    df_copy[date_column] = df_copy['date'].dt.strftime(date_format)
                    
                    # Calculate prediction accuracy percentages for each group
                    for group in all_groups:
                        # Training period accuracy (Training Start Date to Training End Date)
                        training_data = df_copy[(df_copy['group'] == group) & 
                                              (df_copy['date'] >= start_date_str) & 
                                              (df_copy['date'] <= training_end_date_str)]
                        
                        if not training_data.empty and training_data[target_column].sum() > 0:
                            actual = training_data[target_column].values
                            pred = training_data['forecast'].values
                            # Calculate percentage error: (pred - actual) / actual
                            pct_errors = np.where(actual > 0, (pred - actual) / actual, np.nan)
                            # Calculate MAPE (Mean Absolute Percentage Error)
                            mean_pct_error = np.nanmean(pct_errors) * 100
                            training_accuracy[group] = mean_pct_error
                        else:
                            training_accuracy[group] = np.nan
                        
                        # Validation period accuracy (Training End Date to current date)
                        validation_data = df_copy[(df_copy['group'] == group) & 
                                                (df_copy['date'] > training_end_date_str) & 
                                                (df_copy['date'] <= current_date_str)]
                        
                        if not validation_data.empty and validation_data[target_column].sum() > 0:
                            actual = validation_data[target_column].values
                            pred = validation_data['forecast'].values
                            # Calculate percentage error: (pred - actual) / actual
                            pct_errors = np.where(actual > 0, (pred - actual) / actual, np.nan)
                            # Calculate MAPE
                            mean_pct_error = np.nanmean(pct_errors) * 100
                            validation_accuracy[group] = mean_pct_error
                        else:
                            validation_accuracy[group] = np.nan
                    
                    # Store accuracy metrics in session state
                    st.session_state.training_accuracy = training_accuracy
                    st.session_state.validation_accuracy = validation_accuracy
                    
                    # Store results in session state
                    st.session_state.forecast_df = df_copy
                    st.session_state.has_forecast = True
                    
                    progress_bar.progress(100)
                    st.success("Forecast completed successfully!")
                    
                except Exception as e:
                    st.error(f"An error occurred during forecasting: {str(e)}")
                    st.error("Please check your data and settings and try again.")
            
            # Display results if available in session state
            if st.session_state.has_forecast and st.session_state.forecast_df is not None:
                # Display results
                st.subheader("Forecast Results")
                st.dataframe(st.session_state.forecast_df.head(20))
                
                # Create download link for the forecast
                st.subheader("Download Complete Forecast")
                
                # Get the original filename for downloads
                filename_base = st.session_state.original_filename
                
                # CSV download with custom filename
                csv = st.session_state.forecast_df.to_csv(index=False)
                b64 = base64.b64encode(csv.encode()).decode()
                csv_filename = f"{filename_base}_forecast.csv"
                href = f'<a href="data:file/csv;base64,{b64}" download="{csv_filename}">Download CSV File</a>'
                st.markdown(href, unsafe_allow_html=True)
                
                # Excel download with custom filename
                buffer = io.BytesIO()
                st.session_state.forecast_df.to_excel(buffer, index=False)
                buffer.seek(0)
                b64_excel = base64.b64encode(buffer.read()).decode()
                excel_filename = f"{filename_base}_forecast.xlsx"
                href_excel = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64_excel}" download="{excel_filename}">Download Excel File</a>'
                st.markdown(href_excel, unsafe_allow_html=True)
                
                # Visualization section
                st.subheader("Forecast Visualizations")
                
                # Create dropdown for group selection
                selected_group = st.selectbox("Select group to visualize", st.session_state.all_groups)
                
                # Get accuracy metrics for selected group
                training_acc = st.session_state.training_accuracy.get(selected_group, np.nan)
                validation_acc = st.session_state.validation_accuracy.get(selected_group, np.nan)
                
                # Format accuracy metrics for display
                training_acc_text = f"Training Accuracy: {training_acc:.2f}%" if not np.isnan(training_acc) else "Training Accuracy: N/A"
                validation_acc_text = f"Validation Accuracy: {validation_acc:.2f}%" if not np.isnan(validation_acc) else "Validation Accuracy: N/A"
                
                # Plot the selected group
                selected_data = st.session_state.forecast_df[st.session_state.forecast_df['group'] == selected_group].copy()
                
                # 修改: 确保使用排序后的数据来创建图表，避免confidence interval的显示问题
                selected_data = selected_data.sort_values('date')
                
                # Create plotly figure for selected group
                fig = make_subplots(specs=[[{"secondary_y": True}]])
                
                # Add actual values
                fig.add_trace(
                    go.Scatter(
                        x=selected_data['date'],
                        y=selected_data[st.session_state.target_column],
                        mode='lines+markers',
                        name='Actual',
                        line=dict(color='blue')
                    )
                )
                
                # Add forecast
                fig.add_trace(
                    go.Scatter(
                        x=selected_data['date'],
                        y=selected_data['forecast'],
                        mode='lines',
                        name='Forecast',
                        line=dict(color='red')
                    )
                )
                
                # 修改: 更改confidence interval的绘制方法，确保正确绘制
                # 添加上边界
                fig.add_trace(
                    go.Scatter(
                        x=selected_data['date'],
                        y=selected_data['forecast_upper'],
                        mode='lines',
                        line=dict(width=0),
                        showlegend=False
                    )
                )
                
                # 添加下边界
                fig.add_trace(
                    go.Scatter(
                        x=selected_data['date'],
                        y=selected_data['forecast_lower'],
                        mode='lines',
                        line=dict(width=0),
                        fillcolor='rgba(255,0,0,0.2)',
                        fill='tonexty',
                        name='Confidence Interval'
                    )
                )
                
                # Update layout with accuracy metrics in the title
                fig.update_layout(
                    title=f'Forecast for {selected_group} ({training_acc_text}, {validation_acc_text})',
                    xaxis_title='Date',
                    yaxis_title=st.session_state.target_column,
                    hovermode='x unified',
                    legend=dict(orientation='h', y=1.1)
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Add option to view overall forecast (sum of all groups)
                if st.checkbox("View Overall Forecast (Sum of All Groups)"):
                    # Group by date and sum the values
                    overall_data = st.session_state.forecast_df.groupby('date').agg({
                        st.session_state.target_column: 'sum',
                        'forecast': 'sum',
                        'forecast_lower': 'sum',
                        'forecast_upper': 'sum'
                    }).reset_index()
                    
                    # 修改: 确保使用排序后的数据来创建图表，避免confidence interval的显示问题
                    overall_data = overall_data.sort_values('date')
                    
                    # Calculate overall accuracy metrics
                    # Convert dates to datetime for comparison
                    overall_data['date_dt'] = pd.to_datetime(overall_data['date'])
                    
                    # Use stored date strings from session state
                    start_date_str = st.session_state.start_date_str
                    training_end_date_str = st.session_state.training_end_date_str
                    
                    # Convert to datetime objects for comparison
                    start_date_dt = pd.to_datetime(start_date_str)
                    training_end_date_dt = pd.to_datetime(training_end_date_str)
                    current_date_dt = pd.to_datetime(current_date.strftime("%Y-%m-%d"))
                    
                    # Training period accuracy (Training Start Date to Training End Date)
                    training_overall = overall_data[(overall_data['date_dt'] >= start_date_dt) & 
                                                  (overall_data['date_dt'] <= training_end_date_dt)]
                    
                    if not training_overall.empty and training_overall[st.session_state.target_column].sum() > 0:
                        actual = training_overall[st.session_state.target_column].values
                        pred = training_overall['forecast'].values
                        # Calculate percentage error: (pred - actual) / actual
                        pct_errors = np.where(actual > 0, (pred - actual) / actual, np.nan)
                        # Calculate MAPE
                        overall_training_acc = np.nanmean(pct_errors) * 100
                    else:
                        overall_training_acc = np.nan
                    
                    # Validation period accuracy (Training End Date to current date)
                    validation_overall = overall_data[(overall_data['date_dt'] > training_end_date_dt) & 
                                                    (overall_data['date_dt'] <= current_date_dt)]
                    
                    if not validation_overall.empty and validation_overall[st.session_state.target_column].sum() > 0:
                        actual = validation_overall[st.session_state.target_column].values
                        pred = validation_overall['forecast'].values
                        # Calculate percentage error: (pred - actual) / actual
                        pct_errors = np.where(actual > 0, (pred - actual) / actual, np.nan)
                        # Calculate MAPE
                        overall_validation_acc = np.nanmean(pct_errors) * 100
                    else:
                        overall_validation_acc = np.nan
                    
                    # Format overall accuracy metrics for display
                    overall_training_acc_text = f"Training Accuracy: {overall_training_acc:.2f}%" if not np.isnan(overall_training_acc) else "Training Accuracy: N/A"
                    overall_validation_acc_text = f"Validation Accuracy: {overall_validation_acc:.2f}%" if not np.isnan(overall_validation_acc) else "Validation Accuracy: N/A"
                    
                    # Create plotly figure for overall data
                    fig_overall = make_subplots(specs=[[{"secondary_y": True}]])
                    
                    # Add actual values
                    fig_overall.add_trace(
                        go.Scatter(
                            x=overall_data['date'],
                            y=overall_data[st.session_state.target_column],
                            mode='lines+markers',
                            name='Actual',
                            line=dict(color='blue')
                        )
                    )
                    
                    # Add forecast
                    fig_overall.add_trace(
                        go.Scatter(
                            x=overall_data['date'],
                            y=overall_data['forecast'],
                            mode='lines',
                            name='Forecast',
                            line=dict(color='red')
                        )
                    )
                    
                    # 修改: 更改confidence interval的绘制方法，确保正确绘制
                    # 添加上边界
                    fig_overall.add_trace(
                        go.Scatter(
                            x=overall_data['date'],
                            y=overall_data['forecast_upper'],
                            mode='lines',
                            line=dict(width=0),
                            showlegend=False
                        )
                    )
                    
                    # 添加下边界
                    fig_overall.add_trace(
                        go.Scatter(
                            x=overall_data['date'],
                            y=overall_data['forecast_lower'],
                            mode='lines',
                            line=dict(width=0),
                            fillcolor='rgba(255,0,0,0.2)',
                            fill='tonexty',
                            name='Confidence Interval'
                        )
                    )
                    
                    # Update layout with accuracy metrics in the title
                    fig_overall.update_layout(
                        title=f'Overall Forecast (Sum of All Groups) ({overall_training_acc_text}, {overall_validation_acc_text})',
                        xaxis_title='Date',
                        yaxis_title=st.session_state.target_column,
                        hovermode='x unified',
                        legend=dict(orientation='h', y=1.1)
                    )
                    
                    st.plotly_chart(fig_overall, use_container_width=True)
        
        # Add button to clear results and start over
        if st.session_state.has_forecast:
            if st.button("Clear Results and Start Over"):
                # Fix for experimental_rerun issue - use session state to clear data
                st.session_state.forecast_df = None
                st.session_state.all_groups = []
                st.session_state.has_forecast = False
                st.session_state.target_column = None
                st.session_state.original_filename = None
                st.session_state.training_accuracy = {}
                st.session_state.validation_accuracy = {}
                st.session_state.start_date_str = None
                st.session_state.training_end_date_str = None
                # Use Streamlit's rerun function instead of experimental_rerun
                st.rerun()
    
    else:
        # Display sample instructions when no file is uploaded
        st.info("Please upload an Excel file to begin. Your file should contain:")
        st.markdown("""
        - A column with dates or year-month values
        - At least one numeric column to forecast
        - Optional grouping columns (e.g., product codes, regions)
        
        The app will:
        1. Process your data
        2. Fill missing values
        3. Generate forecasts using Facebook Prophet
        4. Allow you to download the complete forecast results
        """)
        
        # Sample data structure
        st.subheader("Sample Data Structure")
        sample_data = pd.DataFrame({
            'year_month': ['202201', '202202', '202203', '202201', '202202', '202203'],
            'product_code': ['A001', 'A001', 'A001', 'B002', 'B002', 'B002'],
            'region': ['North', 'North', 'North', 'South', 'South', 'South'],
            'sales_quantity': [100, 120, 110, 80, 85, 95],
            'sales_amount': [5000, 6000, 5500, 4000, 4250, 4750]
        })
        
        st.dataframe(sample_data)
    
    # Footer
    st.markdown("""
    ---
    ### Notes:
    - For best results, provide at least 12 months of historical data
    - If using grouping, ensure all groups have sufficient data points
    - The forecast horizon can be adjusted based on your needs
    """)


# Modify the main() function to add the Sales Forecasting option
def main():
    st.set_page_config(layout="wide")
    
    # Create the page selection in sidebar
    page = st.sidebar.radio("选择功能", ["Medical Insights Copilot", "Spreadsheet Analysis", "Sales Forecasting"])
    
    if page == "Medical Insights Copilot":  
        model_choice, client = setup_client()
        setup_layout(
            topics, diseases, institutions, departments, persons,
            primary_topics_list, primary_diseases_list,
            generate_tag, generate_diseases_tag, rewrite,
            prob_identy, generate_structure_data,
            model_choice, client
        )
    elif page == "Spreadsheet Analysis":
        setup_spreadsheet_analysis()
    elif page == "Sales Forecasting":
        setup_sales_forecasting()


if __name__ == "__main__":
    main()
