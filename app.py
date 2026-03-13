import streamlit as st
from gtts import gTTS
from PIL import Image
import speech_recognition as sr
import tempfile
import os
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase, WebRtcMode
import cv2
import time

# --------------------------
# Dark theme CSS tweaks
# --------------------------
st.markdown(
    """
    <style>
    /* App background & text */
    .stApp { background-color: #0e1117; color: #fafafa; }

    /* Buttons */
    .stButton>button { background-color: #1abc9c; color: #000; }
    .stButton>button:hover { background-color: #16a085; color: #fff; }

    /* FileUploader */
    .stFileUploader>div { background-color: #262730; color: #fafafa; }

    /* Headers and markdown */
    h1, h2, h3, h4, h5, h6 { color: #fafafa; }
    .stMarkdown p, .stMarkdown span { color: #fafafa; }

    /* Divider line */
    hr { border: 1px solid #1abc9c; }
    </style>
    """,
    unsafe_allow_html=True
)

st.set_page_config(page_title="AI Speech ↔ Sign Letters", page_icon="🤟", layout="centered")
st.title("AI Speech ↔ Sign Letters Demo 🎤🖐️")

# --------------------------
# Folder containing letter signs
# --------------------------
SIGNS_FOLDER = os.path.join(os.getcwd(), "signs")
if not os.path.exists(SIGNS_FOLDER):
    st.error(f"Folder '{SIGNS_FOLDER}' not found! Make sure it exists in the repo root.")
    st.stop()

# --------------------------
# Session state for letters
# --------------------------
if "letters" not in st.session_state:
    st.session_state["letters"] = []
if "live_tts_queue" not in st.session_state:
    st.session_state["live_tts_queue"] = []

letters = st.session_state["letters"]

# --------------------------
# Select mode
# --------------------------
mode = st.selectbox("Select mode:", 
                    ["Speech → Letters", "Letter Image → Speech", "Live Camera → Letters → Speech"])

# ========================
# Mode 1: Speech → Letters
# ========================
if mode == "Speech → Letters":
    st.markdown("## 🎤 Speech → Letters", unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Upload speech file (wav/mp3):", type=["wav","mp3"])
    if uploaded_file:
        audio_bytes = uploaded_file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            temp_audio.write(audio_bytes)
            temp_path = temp_audio.name

        r = sr.Recognizer()
        try:
            with sr.AudioFile(temp_path) as source:
                audio = r.record(source)
            text = r.recognize_google(audio)
            st.markdown(f"**Recognized text:** {text}", unsafe_allow_html=True)
        except:
            st.error("Could not process audio.")
            text = ""

        if text:
            st.markdown("**Letter Signs:**", unsafe_allow_html=True)
            available_files = [os.path.splitext(f)[0].upper() for f in os.listdir(SIGNS_FOLDER)]
            for letter in text.replace(" ", ""):
                letter_upper = letter.upper()
                if letter_upper in available_files:
                    for f in os.listdir(SIGNS_FOLDER):
                        if os.path.splitext(f)[0].upper() == letter_upper:
                            img_path = os.path.join(SIGNS_FOLDER, f)
                            img = Image.open(img_path)
                            st.image(img, caption=letter_upper)
                            break
                else:
                    st.warning(f"No sign image for letter '{letter_upper}'")

            tts_file = "output_speech.mp3"
            tts = gTTS(text=text, lang="en")
            tts.save(tts_file)
            st.audio(tts_file)

# ========================
# Mode 2: Letter Image → Speech
# ========================
elif mode == "Letter Image → Speech":
    st.markdown("## 🖐️ Letter Image → Speech", unsafe_allow_html=True)
    uploaded_images = st.file_uploader(
        "Upload letter images in order", 
        type=["png","jpg","jpeg"], 
        accept_multiple_files=True
    )

    letters.clear()
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
# Mode 3: Live Camera → Letters → Speech (Auto-TTS)
# ========================
elif mode == "Live Camera → Letters → Speech":
    st.markdown("## 📹 Live Camera → Letters → Speech", unsafe_allow_html=True)

    # Helper function: match frame to signs
    def recognize_letter_from_frame(frame_img):
        pil_img = Image.fromarray(cv2.cvtColor(frame_img, cv2.COLOR_BGR2RGB))
        for file_name in os.listdir(SIGNS_FOLDER):
            path = os.path.join(SIGNS_FOLDER, file_name)
            try:
                if Image.open(path).tobytes() == pil_img.tobytes():
                    return os.path.splitext(file_name)[0].upper()
            except:
                continue
        return None

    # Video processor class
    class SignProcessor(VideoTransformerBase):
        def __init__(self):
            self.detected_list = []

        def transform(self, frame):
            img = frame.to_ndarray(format="bgr24")
            letter = recognize_letter_from_frame(img)

            if letter:
                if not self.detected_list or self.detected_list[-1] != letter:
                    self.detected_list.append(letter)
                    st.session_state.live_tts_queue.append(letter)

                cv2.putText(img, f"MATCH: {letter}", (50, 100),
                            cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 0), 4)
            return img

    # Start WebRTC streamer
    ctx = webrtc_streamer(
        key="sign_cam_v5",
        mode=WebRtcMode.SENDONLY,
        video_transformer_factory=SignProcessor,
        async_transform=True,
        media_stream_constraints={"video": True, "audio": False},
    )

    # Button to sync captured letters
    if ctx.video_transformer:
        if st.button("Sync Captured Letters"):
            st.session_state.letters = ctx.video_transformer.detected_list.copy()
            st.success("Letters synced!")

    # Auto-TTS for new letters
    while st.session_state.live_tts_queue:
        letter_to_speak = st.session_state.live_tts_queue.pop(0)
        letters.append(letter_to_speak)
        tts = gTTS(text=letter_to_speak, lang="en")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            tts.save(fp.name)
            st.audio(fp.name)
        time.sleep(0.5)

# ========================
# Footer: display constructed word
# ========================
st.divider()
current_word = "".join(st.session_state.get("letters", []))
st.markdown(f"### Constructed Word: <span style='color:#1abc9c'>{current_word if current_word else '...'}</span>", unsafe_allow_html=True)

if st.button("🗑️ Reset"):
    st.session_state.letters = []
    st.session_state.live_tts_queue = []
    st.rerun()
