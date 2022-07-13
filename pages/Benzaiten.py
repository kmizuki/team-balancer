import streamlit as st
from PIL import Image

st.set_page_config(
    page_title="PlinCustom",
    page_icon="garen.jpeg",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("今日の弁財天")

img = Image.open("zeniarai.jpeg")
st.image(img, use_column_width=True)
