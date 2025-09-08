import streamlit as st
from streamlit_ace import st_ace

#Initialize session state for markdown content if it doesn't exist
if 'markdown_content' not in st.session_state:
    st.session_state.markdown_content = """# Sample Markdown

This is a sample markdown content that you can edit.

Features
Edit in code editor mode
View rendered markdown
Toggle between modes seamlessly

# Code blocks work too!
def hello_world():
    print("Hello, World!")

"""

#Create radio button for mode selection
mode = st.radio(
    "Choose mode:",
    ["📝 Edit", "👁️ View"],
    horizontal=True
)

#Display appropriate component based on selected mode
if mode == "📝 Edit":
    st.subheader("Markdown Editor")

#Code editor for markdown editing
    updated_content = st_ace(
        value=st.session_state.markdown_content,
        language='markdown',
        theme='monokai',
        key='markdown_editor',
        height=400,
        auto_update=True,
        wrap=True,
        font_size=14
    )

#Update session state when content changes
    if updated_content != st.session_state.markdown_content:
        st.session_state.markdown_content = updated_content

else:  # View mode
    st.subheader("Markdown Preview")

#Display rendered markdown
    st.markdown(st.session_state.markdown_content, unsafe_allow_html=True)