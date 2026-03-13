import streamlit as st
import speech_recognition as sr
from PIL import Image
import os
import time

st.title("Voice to Sign Language Slideshow")

# text input backup
text = st.text_input("Enter a word")

if text:
    word = text.upper()
    placeholder = st.empty()

    for letter in word:
        path = f"signs/{letter}.png"

        if os.path.exists(path):
            img = Image.open(path)
            placeholder.image(img, width=300)
            time.sleep(1.5)
        else:
            st.warning(f"No image for {letter}")
