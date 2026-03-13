import streamlit as st
import speech_recognition as sr
from gtts import gTTS
import os
from PIL import Image

st.title("AI Speech to Sign Language Demo 🎤🤟")

st.write("Speak into the mic and see the corresponding Sign Language output!")

# 1. Speech Recognition
recognizer = sr.Recognizer()

if st.button("Record Speech"):
    with sr.Microphone() as source:
        st.info("Listening...")
        audio = recognizer.listen(source, phrase_time_limit=5)
        st.success("Recording complete!")

    try:
        text = recognizer.recognize_google(audio)
        st.write("You said:", text)
    except sr.UnknownValueError:
        st.error("Sorry, could not understand audio")
        text = ""
    except sr.RequestError as e:
        st.error(f"Could not request results; {e}")
        text = ""

    # 2. Convert text to sign language images (example)
    # Assuming you have images for each word in 'sign_images/' folder named as word.png
    if text:
        words = text.split()
        st.write("Sign Language Representation:")
        for word in words:
            try:
                img = Image.open(f"sign_images/{word.lower()}.png")
                st.image(img, caption=word)
            except FileNotFoundError:
                st.warning(f"No sign image found for '{word}'")

    # 3. Optional: convert text back to speech for confirmation
    if text:
        tts = gTTS(text=text, lang='en')
        tts.save("output.mp3")
        st.audio("output.mp3")
