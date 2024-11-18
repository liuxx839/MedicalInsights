# config.py
import json
import pandas as pd
from collections import defaultdict


topics = {
  "获益/风险": ["治疗效果", "安全性评估", "副作用管理", "成本效益分析"],
  "竞争产品": ["市场替代品", "竞品分析", "市场份额", "产品比较"],
  "医疗器械与设备": ["医疗技术", "设备性能", "操作流程", "维护与校准"],
  "疾病诊断与治疗": ["诊断标准", "治疗方案", "疗效评估", "并发症处理"],
  "指南与共识": ["临床实践指南", "专家共识", "政策建议", "标准操作流程"],
  "卫生政策与环境": ["卫生法规", "政策影响", "健康经济学", "医疗体系分析"],
  "患者旅程、准入与支持": ["患者体验", "医疗准入", "患者支持计划", "健康教育资源"],
  "证据生成": ["临床试验设计", "研究成果", "医学论文", "数据共享政策"],
  "赛诺菲产品": ["产品特性", "临床试验结果", "患者反馈", "市场表现"],
  "科学数据": ["数据收集", "数据分析", "结果解释", "数据保护"]
}

primary_topics_list = list(topics.keys())

# 颜色映射，超过7个颜色的primary_topics_list都赋予粉色
color_list = [
    "#067647",  # 绿色
    "#B42318",  # 红色
    "#B54708",  # 棕色
    "#175CD3",  # 蓝色
    "#282828",  # 黑色
    "#7A00E6",  # 紫色
]

# 默认紫色用于超过6个颜色的主题
default_color = "#7A00E6"  # 紫色


# 按照顺序为 primary_topics_list 分配颜色
colors = {}
for i, topic in enumerate(primary_topics_list):
    colors[topic] = color_list[i] if i < len(color_list) else default_color
  

generate_tag_system_message = '''
你的职责是给文本打标签，标签只能在下面的类别里,最多最多选三个最接近的,不需要解释，直接返回结果即可,不需要任何其他文字,如果判断内容不符合任何标签，返回out of label
{primary_topics_list}
'''

diseases = {
    "心血管疾病": ["冠心病", "高血压", "心力衰竭", "心律失常"],
    "呼吸系统疾病": ["哮喘", "慢性阻塞性肺疾病", "肺炎", "肺癌"],
    "消化系统疾病": ["胃溃疡", "肝炎", "胰腺炎", "结肠癌"],
    "内分泌系统疾病": ["糖尿病", "甲状腺功能亢进", "肾上腺功能不全", "肥胖症"],
    "神经系统疾病": ["阿尔茨海默病", "帕金森病", "多发性硬化", "脑卒中"],
    "骨骼肌肉系统疾病": ["骨质疏松", "类风湿性关节炎", "腰椎间盘突出", "肌肉萎缩"],
    "血液系统疾病": ["贫血", "白血病", "血友病", "淋巴瘤"],
    "免疫系统疾病": ["系统性红斑狼疮", "HIV/AIDS", "多发性硬化", "过敏性疾病"],
    "泌尿生殖系统疾病": ["肾衰竭", "前列腺癌", "尿路感染", "子宫内膜异位症"],
    "精神疾病": ["抑郁症", "焦虑障碍", "精神分裂症", "双相情感障碍"],
    "皮肤疾病": ["银屑病", "湿疹", "皮肤癌", "痤疮"],
    "眼科疾病": ["白内障", "青光眼", "视网膜病变", "近视"],
    "耳鼻喉疾病": ["中耳炎", "鼻窦炎", "咽喉癌", "听力损失"],
    "传染病": ["流感", "结核病", "疟疾", "新冠肺炎"],
    "罕见疾病": ["囊性纤维化", "亨廷顿舞蹈症", "马凡综合征", "血友病"]
}

primary_diseases_list = list(diseases.keys())

generate_diseases_system_message = '''
你的职责是给文本打标签，标签只能在下面的类别里,最多最多选三个最接近的,不需要解释，直接返回结果即可,不需要任何其他文字,如果判断内容不符合任何标签，返回out of label
{primary_diseases_list}
'''

# def get_rewrite_system_message(institution, department, person):
#     return f'''
# 你的职责是改写文本，原则尽量使用原始文本内容
# 改写建议：根据综合判断和评估反馈对原文本进行改写，尽量保留原文本表达和意思，并对原文本中的未脱敏信息进行脱敏处理。改写后文本不少于100字
# 严格遵循下面的规范文本样式：
# 一名{institution}的{department}的{person}提出{{观点}},{{内容间的逻辑关系}},{{进一步的方案}}

# 执行逻辑：
# 1.如果判断原始文本缺失太多内容，请礼貌提醒，无需执行下面的任何步骤或者逻辑
# 2. 否则： "一名{institution}的{department}的{person}提出"， 不需要修改
# 3。 原文如果存在的机构和人物，需要脱敏, 替换为"一名{institution}的{person}" 相应的部份
# 4.其中{{观点}},{{内容间的逻辑关系}},{{进一步的方案}} 要源于原始文本，尽量使用原文。不需要特别指出{{观点}},{{内容间的逻辑关系}},{{进一步的方案}}
# 5.只返回改写后的文本即可，无需解释。不要作额外推理
# '''

def get_rewrite_system_message(institution, department, person):
    return f'''
你的职责是改写文本，要丰富内容，但要基于事实
改写建议：根据综合判断和评估反馈对原文本进行改写，尽量保留原文本表达和意思，并对原文本中的未脱敏信息进行脱敏处理。改写后文本不少于100字
严格遵循下面的规范文本样式：
一名{institution}的{department}的{person}提出{{观点}},{{内容间的逻辑关系}},{{进一步的方案}}

执行逻辑：
1.如果判断原始文本缺失太多内容，请礼貌提醒，无需执行下面的任何步骤或者逻辑
2. 否则： "一名{institution}的{department}的{person}提出"， 不需要修改
3。 原文如果存在的机构和人物，需要脱敏, 替换为"一名{institution}的{person}" 相应的部份
4.其中{{观点}},{{内容间的逻辑关系}},{{进一步的方案}} 要源于原始文本，要丰富内容。不需要特别指出{{观点}},{{内容间的逻辑关系}},{{进一步的方案}}
5.只返回改写后的文本即可，无需解释。不要作额外推理
6.根据改写的内容，请在结尾添加不多于5个的简短关键词会
7.在最后提出一些可扩展内容的问题
'''

prob_identy_system_message = '''
You are a Medical Insight quality inspector. Please check if the given materials in json meets the below requriments:
the info  should cover the 4W elements (Who(Title,Affiliation,department), What, Why, Way Forward), while the private info should be empty for Anonymization purpose.
just return: 1) if any missing in the required fields, pay extra attention to Who part, pay extra attention to Why part,  pay extra attention to Way Forward part 2) if private info meets Anonymization. 3)no need to re-write. 
You need to add appropriate emojis in your response, and the reply should be in Chinese. REPLY SHOULD BE IN CHINESE

'''

# prob_identy_system_message = '''
# You need to add appropriate emojis in your response, and the reply should be in Chinese.

# A standard and complete Medical Insight should cover the 4W elements (Who, What, Why, Way Forward). Here is a sample of a qualified format: "A representative from [Anonymized Institution] in the [Department] stated [Opinion], explaining [Reasoning and Logical Connections], and further proposed [Follow-up Plan]."

# You are a Medical Insight quality inspector. Please check if the given text meets the following rules:

# 4W Elements: Check if the text covers the 4W elements (Who, What, Why, Way Forward).
# **Anonymized Information**: Check if there are identifiable, non-anonymized names of medical institutions and persons (including surnames). However, specific job titles, hospital types or levels, clinical study names, etc., are not sensitive information and are considered anonymized. Specific drug names or abbreviations are also not sensitive information and do not need to be pointed out.
# Opinion Expression: Evaluate if a clear opinion is included.
# Logical Relationship: Analyze the logical coherence of the content.
# Follow-up Plan: Determine if a follow-up plan or action is provided.
# Word Count Requirement: Ensure the word count is >20.
# Response Rules: Please answer in Chinese.
# Overall Judgment: First, make a comprehensive judgment on the overall rule compliance, choosing only from: “Meet All Conditions”, “Content Basically Meets”, or “Content Needs Modification”.
# Evaluation Feedback: Provide feedback according to the evaluation rules. If there are violations, please briefly point out the issue and explain the reason without being verbose.
# '''

# prob_identy_system_message = '''
# **你回复中需要添加适当表情，回复用汉语**

# 规范完整的Medical Insight应涵盖4W要素（Who-谁、What-什么、Why-为什么、Way Forward-下一步计划或跟进方案）。
# 以下是一个合格样式的示例："一位{脱敏机构}的{科室}的{脱敏人物}指出{观点}，并阐述了{观点背后的原因和逻辑联系}，进而提出了{后续方案}"。
# 你是Medical Insight书写质量检测员，请检查给定文本是否符合以下规则:
# 4W要素：检查是否涵盖4W要素（Who-谁、What-什么、Why-为什么、Way Forward-下一步计划或跟进方案）
# 脱敏信息: 检查是否存在可被识别的、未脱敏的医疗机构名和人名(包括仅姓氏)private information,**但是具体的人物职务或者职称，医院类型或级别、临床研究名称等，并非敏感信息，算为已脱敏**。具体药品名称或缩写也并非敏感信息，算是已脱敏，不必指出。
# 观点表述: 评估是否包含明确观点
# 逻辑关系: 分析内容逻辑性
# 跟进方案: 判断是否提供下一步计划或跟进方案
# 字数要求: 确保字数>20
# 响应规则：请用中文回答
# 综合判断: 首先综合判断整体规则服从情况，只能从：“满足所有条件”，“内容基本满足”，“内容需要修改”三个词中选择
# 评估反馈: 根据评估规则进行逐条反馈。如果有违反情况，请简明指出问题,解释原因，不要啰嗦
# '''

institutions = [
   # "斯坦索姆",
    "大型医疗机构",
    "综合性医院",
    "专科医院",
    "三甲医院",
    "二甲医院",
    "城市医院",
    "省立医院",
    "地区医院",
    "医疗中心",
    "教学医院",
    "医疗集团",
    "医疗机构",
    "临床医院",
    "医疗服务中心"
]

departments = [
  #  "嚎哭洞穴",
    "内分泌科",
    "肾移植科",
    "妇产科",
    "儿科",
    "急诊科",
    "心血管内科",
    "神经内科",
    "消化内科",
    "呼吸内科",
    "骨科",
    "泌尿外科",
    "心胸外科",
    "整形外科",
    "眼科",
    "耳鼻喉科",
    "口腔科",
    "皮肤科",
    "中医科",
    "康复科",
    "肿瘤科",
    "放射科",
    "检验科",
    "病理科",
    "药剂科",
    "麻醉科",
    "重症医学科",
    "感染性疾病科",
    "老年病科",
    "精神心理科",
    "肾内科",
    "血液科",
    "风湿免疫科",
    "营养科",
    "介入科",
    "核医学科",
    "超声科",
    "体检中心",
    "医学美容科"
]

persons = [
  #  "大壮",
    "专家",
    "医生",
    "主任医师",
    "副主任医师",
    "主治医师",
    "医疗团队成员",
    "研究人员",
    "学者",
    "顾问",
    "分析师",
    "工作人员",
    "主任",
    "副主任",
    "教授",
    "副教授",
    "讲师",
    "医疗保健提供者",
    "护士长",
    "护士",
    "研究员"
]

generate_structure_table_message = """
Template:
{
"Who": {
"Title": "",
"Affiliation": "",
"Department": ""
},
"What": {
"Topic": "",
"Key findings": []
},
"Why": {
"Reasons": []
},
"Wayforward": {
"Future directions": []
},
"Private_Information": []
}
Example:
{
"Who": {
"Title": "李教授",
"Affiliation": "北京大学第一医院"
"Department": "心血管科"
},
"What": {
"Topic": "GLP-1 receptor agonist研究",
"Key findings": [
"LEAD研究：HbA1c<7%",
"EXSCEL研究：HbA1c<8%",
"治疗时间从6个月内扩展到12个月内",
"LEAD和EXSCEL研究GLP-1 receptor agonist治疗时间为26周",
"ELIXA研究GLP-1 receptor agonist治疗时间为104周"
]
},
"Why": {
"Reasons": [
"扩大GLP-1 receptor agonist应用场景",
"为2型糖尿病GLP-1 receptor agonist治疗提供更多循证证据"
]
},
"Wayforward": {
"Future directions": [
"让更多医生了解并在实战中充分利用该研究",
"推荐26周的临床使用时间"
]
},
"Private_Information": [
"李教授",
"北京大学第一医院"
]
}
Template:
{
    "Who": {
        "Title": "主任",
        "Affiliation": "某三甲医院",
        "Department": "神经内科"
    },
    "What": {
        "Topic": "LDL-C低限研究",
        "Key findings": [
            "LDL-C学术上可以降到婴儿水平",
            "临床实践中LDL-C要相对平稳",
            "指南推荐LDL-C控制在1850或1450"
        ]
    },
    "Why": {
        "Reasons": [
            "担心LDL-C过低导致的脑出血和神经认知功能障碍",
            "指南共识上未有推荐"
        ]
    },
    "Wayforward": {
        "Future directions": [
            "发表低LDL-C安全性相关文章",
            "研究脑胆固醇独立合成机制",
            "解除关于LDL-C的误区"
        ]
    },
    "Private_Information": []
}
Template:
{
"Who": {
"Title": "黄主任",
"Affiliation": "千佛山医院",
"Department": ""
},
"What": {
"Topic": "贝舒地尔在BOS患者中的应用",
"Key findings": [
"贝舒地尔应用期间应注意患者肺功能情况",
"密切关注患者感染情况",
"移植后患者免疫功能较差",
"积极抗感染治疗有利于FEV1升高及症状缓解"
]
},
"Why": {
"Reasons": [
"合并BOS患者更易罹患肺部感染",
"感染会进一步加重患者BOS症状"
]
},
"Wayforward": {
"Future directions": [
"积极抗感染治疗",
"密切关注患者肺功能情况"
]
},
"Private_Information": [
"黄主任",
"千佛山医院"
]
}
Follow above template, direct output json format in above format, no explanation, dont fill in any info if text is too short
"""

# def json_to_dataframe(json_data):
#     def flatten_json(data, prefix=''):
#         items = defaultdict(list)
#         max_length = 0
#         for key, value in data.items():
#             new_key = f"{prefix}/{key}" if prefix else key
#             if isinstance(value, dict):
#                 sub_items = flatten_json(value, new_key)
#                 for sub_key, sub_value in sub_items.items():
#                     items[sub_key] = sub_value
#                     max_length = max(max_length, len(sub_value))
#             elif isinstance(value, list):
#                 items[new_key] = value
#                 max_length = max(max_length, len(value))
#             else:
#                 items[new_key] = [value]
#                 max_length = max(max_length, 1)
        
#         # 确保所有列的长度一致
#         for key in items:
#             items[key] = items[key] + [''] * (max_length - len(items[key]))
        
#         return items

#     # 将JSON字符串转换为Python字典
#     if isinstance(json_data, str):
#         data = json.loads(json_data)
#     else:
#         data = json_data

#     # 展平JSON结构
#     flat_data = flatten_json(data)

#     # 创建DataFrame
#     df = pd.DataFrame(flat_data)

#     return df
def json_to_dataframe(json_data):
    """
    将复杂的JSON数据转换为DataFrame格式。
    支持嵌套的字典、列表，将多条数据分别放入不同行。
    
    Args:
        json_data: JSON字符串或字典对象
        
    Returns:
        pd.DataFrame: 展平后的数据框，对于多记录数据总是返回多行
    """
    def extract_list_length(data):
        """递归查找最长列表的长度"""
        if isinstance(data, dict):
            return max([extract_list_length(v) for v in data.values()], default=1)
        elif isinstance(data, list):
            if not data:
                return 1
            # 移除对基本类型列表的特殊处理
            return len(data)
        return 1

    def flatten_json(data, prefix='', row_index=0, max_rows=1):
        items = defaultdict(list)
        
        # 处理基本类型
        if isinstance(data, (str, int, float, bool)) or data is None:
            items[prefix] = [data] * max_rows if prefix else []
            return items
            
        # 处理列表
        elif isinstance(data, list):
            if not data:
                items[prefix] = [None] * max_rows if prefix else []
                return items
            
            # 统一处理所有类型的列表
            if all(isinstance(x, (str, int, float, bool, type(None))) for x in data):
                # 基本类型列表也展开成多行
                if prefix:
                    items[prefix] = []
                    for item in data:
                        items[prefix].append(item)
                    # 如果当前列表长度小于最大行数，用None填充
                    if len(items[prefix]) < max_rows:
                        items[prefix].extend([None] * (max_rows - len(items[prefix])))
                return items
            
            # 处理包含复杂类型的列表
            for i, item in enumerate(data):
                if isinstance(item, dict):
                    temp = flatten_json(item, prefix, i, len(data))
                    for k, v in temp.items():
                        if not items[k]:
                            items[k] = [None] * max_rows
                        items[k][i] = v[0] if v else None
                else:
                    if prefix:
                        if not items[prefix]:
                            items[prefix] = [None] * max_rows
                        items[prefix][i] = item
            
            return items
            
        # 处理字典
        elif isinstance(data, dict):
            max_list_length = extract_list_length(data)
            
            for key, value in data.items():
                new_key = f"{prefix}/{key}" if prefix else key
                
                # 递归处理值
                temp = flatten_json(value, new_key, row_index, max_list_length)
                for k, v in temp.items():
                    if not items[k]:
                        items[k] = [None] * max_rows
                    if isinstance(v, list):
                        if len(v) == max_rows:
                            items[k] = v
                        else:
                            # 确保列表值正确对齐到行
                            items[k][:len(v)] = v
                            if len(v) < max_rows:
                                items[k][len(v):] = [None] * (max_rows - len(v))
                    else:
                        items[k] = [v] * max_rows
            
            return items
            
        return items

    # 转换输入数据
    if isinstance(json_data, str):
        try:
            data = json.loads(json_data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON string: {str(e)}")
    else:
        data = json_data

    # 如果输入是列表，确保作为多行处理
    if isinstance(data, list):
        if all(isinstance(x, (str, int, float, bool, type(None))) for x in data):
            # 基本类型列表转换为单列多行DataFrame
            return pd.DataFrame({"value": data})
        
    # 计算需要的总行数
    max_rows = extract_list_length(data)
    
    # 展平JSON结构
    flat_data = flatten_json(data, max_rows=max_rows)
    
    # 如果没有数据，返回空DataFrame
    if not flat_data:
        return pd.DataFrame()

    # 创建DataFrame
    df = pd.DataFrame(flat_data)
    
    # 清理列名，移除开头的/
    df.columns = [col[1:] if col.startswith('/') else col for col in df.columns]
    
    # 删除全为空值的行
    df = df.dropna(how='all')
    
    return df
