import streamlit as st
from gtts import gTTS
from PIL import Image
import speech_recognition as sr
import io
import tempfile

st.set_page_config(page_title="AI Speech to Sign Language", page_icon="🤟", layout="centered")
st.title("AI Speech to Sign Language Demo 🎤🤟")
st.write("Record your speech or upload an audio file, then see the corresponding sign language output!")

# --- AUDIO INPUT ---
option = st.radio("Choose input method:", ["Record Audio", "Upload Audio File"])
audio_bytes = None

if option == "Record Audio":
    st.info("Click the button below to record your voice (max 5 seconds).")
    audio_bytes = st.audio_input("Record your speech here", type="wav")
elif option == "Upload Audio File":
    uploaded_file = st.file_uploader("Upload your audio (wav/mp3)", type=["wav","mp3"])
    if uploaded_file is not None:
        audio_bytes = uploaded_file.read()

# --- PROCESS AUDIO ---
if audio_bytes:
    st.success("Audio received! Processing...")
    r = sr.Recognizer()

    # Save audio to temporary file for SpeechRecognition
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
        temp_audio.write(audio_bytes)
        temp_path = temp_audio.name

    try:
        with sr.AudioFile(temp_path) as source:
            audio = r.record(source)
        text = r.recognize_google(audio)
        st.write("**You said:**", text)
    except sr.UnknownValueError:
        st.error("Could not understand audio")
        text = ""
    except sr.RequestError as e:
        st.error(f"Speech Recognition request failed; {e}")
        text = ""

    # --- TEXT TO SIGN LANGUAGE ---
    if text:
        st.write("**Sign Language Representation:**")
        words = text.split()
        for word in words:
            try:
                img = Image.open(f"sign_images/{word.lower()}.png")
                st.image(img, caption=word)
            except FileNotFoundError:
                st.warning(f"No sign image found for '{word}'")

    # --- OPTIONAL: TEXT TO SPEECH ---
    if text:
        tts = gTTS(text=text, lang="en")
        tts_file = "output.mp3"
        tts.save(tts_file)
        st.audio(tts_file)
