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

def main():
    st.set_page_config(layout="wide")
    
    client = setup_client()
    
    setup_layout(
        topics, diseases, institutions, departments, persons,
        primary_topics_list, primary_diseases_list,
        generate_tag, generate_diseases_tag, rewrite,
        prob_identy, generate_structure_data,
        client
    )

if __name__ == "__main__":
    main()
