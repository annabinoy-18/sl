import streamlit as st
from gtts import gTTS
from PIL import Image
import speech_recognition as sr
import tempfile
import os
import cv2
import numpy as np
import threading
from streamlit_webrtc import webrtc_streamer, WebRtcMode, VideoProcessorBase

# --- CONFIGURATION ---
st.set_page_config(page_title="AI Speech ↔ Sign Letters", page_icon="🤟", layout="centered")

SIGNS_FOLDER = os.path.join(os.getcwd(), "signs")
if not os.path.exists(SIGNS_FOLDER):
    os.makedirs(SIGNS_FOLDER, exist_ok=True)
    st.error(f"Please add letter images (A.jpg, B.jpg, etc.) to the '{SIGNS_FOLDER}' folder.")

# --- SESSION STATE ---
if "letters" not in st.session_state:
    st.session_state["letters"] = []

# Thread-safe lock for WebRTC
lock = threading.Lock()

# --- HELPER FUNCTIONS ---
def recognize_letter_from_image(input_img):
    """
    Compares input image to images in the signs folder using Template Matching.
    This is more reliable than bit-wise comparison but still basic.
    """
    best_match = None
    max_val = -1
    
    # Convert input to grayscale for faster comparison
    gray_input = cv2.cvtColor(np.array(input_img), cv2.COLOR_RGB2GRAY)
    
    for file_name in os.listdir(SIGNS_FOLDER):
        if file_name.lower().endswith(('.png', '.jpg', '.jpeg')):
            path = os.path.join(SIGNS_FOLDER, file_name)
            template = cv2.imread(path, 0) # Read as grayscale
            if template is None: continue
            
            # Resize template to match input size for basic comparison
            template = cv2.resize(template, (gray_input.shape[1], gray_input.shape[0]))
            
            res = cv2.matchTemplate(gray_input, template, cv2.TM_CCOEFF_NORMED)
            _, val, _, _ = cv2.minMaxLoc(res)
            
            if val > max_val:
                max_val = val
                best_match = os.path.splitext(file_name)[0].upper()
    
    # Threshold: Only return if the match is decent (> 60% similarity)
    return best_match if max_val > 0.6 else None

# --- UI ---
st.title("AI Speech ↔ Sign Letters Demo 🎤🖐️")
mode = st.selectbox("Select mode:", ["Speech → Letters", "Letter Image → Speech", "Live Camera → Letters"])

# ========================
# Mode 1: Speech → Letters
# ========================
if mode == "Speech → Letters":
    st.header("Speech → Letters")
    uploaded_file = st.file_uploader("Upload speech file (wav/mp3):", type=["wav","mp3"])
    
    if uploaded_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            temp_audio.write(uploaded_file.read())
            temp_path = temp_audio.name

        r = sr.Recognizer()
        try:
            with sr.AudioFile(temp_path) as source:
                audio = r.record(source)
            text = r.recognize_google(audio).upper()
            st.success(f"Recognized: {text}")
            
            cols = st.columns(len(text.replace(" ", "")))
            idx = 0
            for char in text:
                if char == " ": continue
                img_path = os.path.join(SIGNS_FOLDER, f"{char}.jpg") # Assumes .jpg
                if os.path.exists(img_path):
                    cols[idx].image(Image.open(img_path), caption=char)
                    idx += 1
        except Exception as e:
            st.error(f"Error: {e}")

# ========================
# Mode 2: Letter Image → Speech
# ========================
elif mode == "Letter Image → Speech":
    st.header("Letter Image → Speech")
    uploaded_images = st.file_uploader("Upload signs in order", type=["png","jpg","jpeg"], accept_multiple_files=True)

    if uploaded_images and st.button("Process Images"):
        detected_word = ""
        for img_file in uploaded_images:
            img = Image.open(img_file)
            letter = recognize_letter_from_image(img)
            if letter:
                detected_word += letter
        
        if detected_word:
            st.session_state.letters = list(detected_word)
            st.success(f"Recognized: {detected_word}")
        else:
            st.warning("No signs recognized.")

# ========================
# Mode 3: Live Camera
# ========================
elif mode == "Live Camera → Letters":
    st.header("Live Camera Recognition")
    
    class SignProcessor(VideoProcessorBase):
        def __init__(self):
            self.last_letter = None

        def recv(self, frame):
            img = frame.to_ndarray(format="bgr24")
            # Convert to PIL for our helper function
            pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            
            letter = recognize_letter_from_image(pil_img)
            
            if letter:
                with lock:
                    # Update session state if it's a new letter
                    if not st.session_state.letters or st.session_state.letters[-1] != letter:
                        st.session_state.letters.append(letter)
                
                cv2.putText(img, f"Detected: {letter}", (10, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
            
            return frame.from_ndarray(img, format="bgr24")

    webrtc_streamer(
        key="sign_cam",
        mode=WebRtcMode.SENDRECV,
        video_processor_factory=SignProcessor,
        media_stream_constraints={"video": True, "audio": False},
        async_processing=True,
    )

# --- FOOTER / AUDIO OUTPUT ---
st.divider()
current_word = "".join(st.session_state.letters)
st.subheader(f"Current Word: {current_word}")

col1, col2 = st.columns(2)
if col1.button("Clear Word"):
    st.session_state.letters = []
    st.rerun()

if col2.button("Speak Word"):
    if current_word:
        tts = gTTS(text=current_word, lang="en")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            tts.save(fp.name)
            st.audio(fp.name)
    else:
        st.warning("Nothing to speak.")
