import streamlit as st
import speech_recognition as sr
from PIL import Image
import os

st.set_page_config(page_title="Voice to Sign Language", layout="centered")

st.title("🎤 Voice to Sign Language Translator")
st.write("Speak or type a word to convert it into sign language.")

recognizer = sr.Recognizer()

text = ""

# Voice Input
if st.button("🎙 Speak"):
    with sr.Microphone() as source:
        st.info("Listening...")
        audio = recognizer.listen(source)

    try:
        text = recognizer.recognize_google(audio)
        st.success(f"You said: {text}")
    except:
        st.error("Could not understand audio")

# Text Input
typed_text = st.text_input("Or type text here")

if typed_text:
    text = typed_text

# Convert text to sign images
if text:
    text = text.upper()

    st.subheader("🤟 Sign Language Output")

    cols = st.columns(len(text))

    for i, letter in enumerate(text):

        if letter != " ":
            path = f"signs/{letter}.png"

            if os.path.exists(path):
                img = Image.open(path)
                cols[i].image(img, width=100)
