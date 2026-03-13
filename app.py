import streamlit as st
from gtts import gTTS
from PIL import Image
import speech_recognition as sr
import tempfile
import os
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase, WebRtcMode
import cv2

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
    st.header("Speech → Letters")
    st.session_state["live_mode"] = False
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
            st.write("**Recognized text:**", text)
        except:
            st.error("Could not process audio.")
            text = ""

        if text:
            st.write("**Letter Signs:**")
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
    st.header("Static Image Recognition")
    uploaded_images = st.file_uploader("Upload sign images", type=["png","jpg","jpeg"], accept_multiple_files=True)

    if uploaded_images and st.button("Extract Letters"):
        detected_word = ""
        for img_file in uploaded_images:
            file_bytes = np.asarray(bytearray(img_file.read()), dtype=np.uint8)
            img = cv2.imdecode(file_bytes, 1)
            letter = recognize_letter_from_frame(img)
            if letter:
                detected_word += letter
        
        if detected_word:
            st.session_state.letters = list(detected_word)
            st.success(f"Detected Word: {detected_word}")

# ========================
# Mode 3: Live Camera
# ========================
elif mode == "Live Camera → Letters":
    st.header("Live Camera Recognition")
    st.info("Hold your hand sign clearly in front of the camera.")
    
    class SignProcessor(VideoProcessorBase):
        def __init__(self):
            self.last_letter = None

        def recv(self, frame):
            img = frame.to_ndarray(format="bgr24")
            
            # Call our recognition helper
            letter = recognize_letter_from_frame(img)
            
            if letter:
                with lock:
                    # Prevent spamming the same letter repeatedly
                    if not st.session_state.letters or st.session_state.letters[-1] != letter:
                        st.session_state.letters.append(letter)
                
                # Draw the letter on the screen for feedback
                cv2.putText(img, f"MATCH: {letter}", (50, 100), 
                            cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 0), 4)
            
            return frame.from_ndarray(img, format="bgr24")

    # The actual WebRTC widget with STUN configuration
    webrtc_streamer(
        key="sign_cam_v2",
        mode=WebRtcMode.SENDRECV,
        video_processor_factory=SignProcessor,
        async_processing=True,
        # THIS FIXES THE "CONNECTION TAKING LONGER" ERROR
        rtc_configuration={
            "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
        },
        media_stream_constraints={"video": True, "audio": False},
    )

# --- GLOBAL FOOTER ---
st.divider()
current_word = "".join(st.session_state.letters)
st.subheader(f"Constructed Word: :blue[{current_word if current_word else '...'}]")

col1, col2 = st.columns(2)
if col1.button("🗑️ Reset"):
    st.session_state.letters = []
    st.rerun()

if col2.button("🔊 Speak Result"):
    if current_word:
        tts = gTTS(text=current_word, lang="en")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            tts.save(fp.name)
            st.audio(fp.name, autoplay=True)
    else:
        st.warning("No letters detected yet.")
