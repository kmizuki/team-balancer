import streamlit as st
from PIL import Image

st.title("今日の弁財天")

img = Image.open("zeniarai.jpeg")
st.image(img, use_column_width=True)
