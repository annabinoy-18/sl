import streamlit as st
import speech_recognition as sr
from PIL import Image
import os
import time

st.title("🎤 Voice to Sign Language Slideshow")

recognizer = sr.Recognizer()

if st.button("Speak"):

    with sr.Microphone() as source:
        st.info("Listening...")
        audio = recognizer.listen(source)

    try:
        text = recognizer.recognize_google(audio)
        st.success(f"You said: {text}")

        word = text.upper()

        placeholder = st.empty()

        for letter in word:

            if letter != " ":

                path = f"signs/{letter}.png"

                if os.path.exists(path):
                    img = Image.open(path)

                    placeholder.image(img, width=300)

                    time.sleep(1.5)

    except:
        st.error("Could not understand the audio")
