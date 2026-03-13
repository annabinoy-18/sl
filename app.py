import streamlit as st
from gtts import gTTS
from PIL import Image
import speech_recognition as sr
import tempfile
import os
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase, WebRtcMode
import cv2

st.set_page_config(page_title="Speech ↔ Letters ↔ Live Letters", page_icon="🤟", layout="centered")
st.title("AI Speech ↔ Sign Letters Demo 🎤🖐️")

# --- Folder containing individual letter signs ---
SIGNS_FOLDER = os.path.join(os.getcwd(), "signs")

# Check if folder exists
if not os.path.exists(SIGNS_FOLDER):
    st.error(f"Folder '{SIGNS_FOLDER}' not found! Make sure it exists in the repo root.")
    st.stop()

# --- Select Mode ---
mode = st.selectbox("Select mode:", 
                    ["Speech → Letters", "Letter Image → Speech", "Live Camera → Letters → Speech"])

# ----------------------------
# Mode flags for WebRTC
# ----------------------------
if "live_mode" not in st.session_state:
    st.session_state["live_mode"] = False

st.session_state["live_mode"] = (mode == "Live Camera → Letters → Speech")
letters = []

# ========================
# Mode 1: Speech → Letters
# ========================
if mode == "Speech → Letters":
    st.header("Speech → Letters")
    st.write("Upload an audio file (wav/mp3) to see the letter signs for each letter.")

    uploaded_file = st.file_uploader("Upload speech file", type=["wav","mp3"], key="speech2letters")
    if uploaded_file:
        audio_bytes = uploaded_file.read()
        st.success("Audio uploaded! Processing...")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            temp_audio.write(audio_bytes)
            temp_path = temp_audio.name

        r = sr.Recognizer()
        try:
            with sr.AudioFile(temp_path) as source:
                audio = r.record(source)
            text = r.recognize_google(audio)
            st.write("**Recognized text:**", text)
        except:
            st.error("Could not process audio.")
            text = ""

        if text:
            st.write("**Letter Signs:**")
            for letter in text.replace(" ", "").lower():
                img_path = os.path.join(SIGNS_FOLDER, f"{letter}.png")
                if os.path.exists(img_path):
                    img = Image.open(img_path)
                    st.image(img, caption=letter.upper())
                else:
                    st.warning(f"No sign image for letter '{letter}'")

            tts_file = "output_speech.mp3"
            tts = gTTS(text=text, lang="en")
            tts.save(tts_file)
            st.audio(tts_file)

# ========================
# Mode 2: Letter Image → Speech
# ========================
elif mode == "Letter Image → Speech":
    st.header("Letter Image → Speech")
    st.write("Upload one or more letter sign images to hear the spoken letters/word.")

    uploaded_images = st.file_uploader(
        "Upload letter images in order", 
        type=["png","jpg","jpeg"], 
        accept_multiple_files=True, 
        key="letters2speech"
    )

    letters = []
    if uploaded_images:
        for img_file in uploaded_images:
            img = Image.open(img_file)
            st.image(img, caption="Uploaded Letter", use_column_width=True)

            recognized_letter = None
            for file_name in os.listdir(SIGNS_FOLDER):
                path = os.path.join(SIGNS_FOLDER, file_name)
                try:
                    if Image.open(path).tobytes() == img.tobytes():
                        recognized_letter = os.path.splitext(file_name)[0].upper()
                        break
                except:
                    continue

            if recognized_letter:
                letters.append(recognized_letter)
            else:
                st.warning(f"Could not recognize letter for {img_file.name}")

        if letters:
            word = "".join(letters)
            st.success(f"Recognized letters: {word}")
            tts_file = "output_letters.mp3"
            tts = gTTS(text=word, lang="en")
            tts.save(tts_file)
            st.audio(tts_file)

# ========================
# Mode 3: Live Camera → Letters → Speech
# ========================
st.header("Live Camera → Letters → Speech (Camera always shown)")

class LetterRecognizer(VideoTransformerBase):
    def transform(self, frame):
        img = frame.to_ndarray(format="bgr24")
        pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

        if st.session_state["live_mode"]:
            recognized_letter = None
            for file_name in os.listdir(SIGNS_FOLDER):
                path = os.path.join(SIGNS_FOLDER, file_name)
                try:
                    if Image.open(path).tobytes() == pil_img.tobytes():
                        recognized_letter = os.path.splitext(file_name)[0].upper()
                        break
                except:
                    continue

            if recognized_letter and (len(letters) == 0 or recognized_letter != letters[-1]):
                letters.append(recognized_letter)

            if recognized_letter:
                cv2.putText(img, f"Letter: {recognized_letter}", (10,30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
        return img

# Always call WebRTC at top-level
webrtc_streamer(
    key="live_letters",
    mode=WebRtcMode.SENDONLY,
    video_transformer_factory=LetterRecognizer,
    media_stream_constraints={"video": {"facingMode": "user"}, "audio": False}
)

st.write("Word so far:", "".join(letters))

if st.button("Speak Word"):
    if letters:
        word = "".join(letters)
        tts_file = "output_live.mp3"
        tts = gTTS(text=word, lang="en")
        tts.save(tts_file)
        st.audio(tts_file)
    else:
        st.warning("No letters detected yet.")
