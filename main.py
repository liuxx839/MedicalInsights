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
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
from dagrelation import DAGRelations
from datadescription import DataDescription

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
                
                # 保存DataFrame到session state
                st.session_state.df = df
                
                # 显示前10行数据
                st.write("数据预览:")
                st.dataframe(df)
                
                # 保存sample数据到session state
                st.session_state.sample_data = df.head(10).to_dict()
                
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
                                1. 仔细分析数据列之间的关系
                                2. 识别可能的因果关系
                                3. 构建合适的DAG边
                                4. 支持多对一的关系
                                5. 确保使用的是原始的列名，不要做任何修改
                                6. 不要增加任何不存在的列名

                                最终输出格式必须如下：


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

                                        # 关键洞察
                                        ## 主要发现
                                        - 发现1: [简明描述] - 支持数据: [相关统计结果]
                                        - 发现2: [简明描述] - 支持数据: [相关统计结果]

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
                
def main():
    st.set_page_config(layout="wide")
    
    model_choice, client = setup_client()
    # Create the page selection in sidebar
    page = st.sidebar.radio("选择功能", ["Medical Insights Copilot", "Spreadsheet Analysis"])
    
    if page == "Medical Insights Copilot":  
        setup_layout(
            topics, diseases, institutions, departments, persons,
            primary_topics_list, primary_diseases_list,
            generate_tag, generate_diseases_tag, rewrite,
            prob_identy, generate_structure_data,
            model_choice, client
        )
    elif page == "Spreadsheet Analysis":
            setup_spreadsheet_analysis()


if __name__ == "__main__":
    main()
