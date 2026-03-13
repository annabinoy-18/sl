import streamlit as st
from streamlit_audio_recorder import st_audio_recorder
import speech_recognition as sr
from gtts import gTTS
from PIL import Image
import tempfile

st.title("Live Speech to Sign Language Demo 🎤🤟")

audio_bytes = st_audio_recorder("Click to record your speech")

if audio_bytes:
    st.success("Recording received! Processing...")

    # Save to temporary WAV file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
        temp_audio.write(audio_bytes)
        temp_path = temp_audio.name

    # Speech recognition
    r = sr.Recognizer()
    with sr.AudioFile(temp_path) as source:
        audio = r.record(source)
    try:
        text = r.recognize_google(audio)
        st.write("You said:", text)
    except:
        st.error("Could not recognize speech")
        text = ""

    # Show sign language images
    if text:
        words = text.split()
        for word in words:
            try:
                img = Image.open(f"sign_images/{word.lower()}.png")
                st.image(img, caption=word)
            except:
                st.warning(f"No sign image for '{word}'")

    # Optional: TTS feedback
    if text:
        tts = gTTS(text=text, lang="en")
        tts.save("output.mp3")
        st.audio("output.mp3")
