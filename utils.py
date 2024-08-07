#utils.py
import json

def match_color(tag, colors, topics):
    tag = tag.strip()
    if tag in topics:
        return colors[tag]
    for topic, keywords in topics.items():
        if tag in keywords:
            return colors[topic]
    return "#696969"  # 默认为灰色

def determine_issue_severity(issues_text):
    if "内容需要修改" in issues_text:
        return "red"
    elif "内容基本满足" in issues_text or ("满足所有条件" in issues_text and "内容基本满足" in issues_text):
        return "yellow"
    elif "满足所有条件" in issues_text:
        return "green"
    else:
        return "white"

def create_json_data(use_generated_text_and_tags, session_state, user_input, primary_topics):
    if use_generated_text_and_tags and 'rewrite_text' in session_state and 'tags' in session_state:
        data = {
            "Medical_Insights": session_state.rewrite_text,
            "Tags": session_state.tags.split(",")
        }
    else:
        data = {
            "Medical_Insights": user_input,
            "Tags": primary_topics
        }
    return json.dumps(data, ensure_ascii=False, indent=4)
