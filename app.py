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
    st.warning(f"Note: Put letter images (A.jpg, B.jpg, etc.) in the '{SIGNS_FOLDER}' folder.")

# --- SESSION STATE ---
# We use a list to track detected letters
if "letters" not in st.session_state:
    st.session_state["letters"] = []

# This lock prevents the Camera thread and UI thread from crashing each other
lock = threading.Lock()

# --- RECOGNITION HELPER ---
def recognize_letter_from_frame(frame_bgr):
    """
    Compares the current camera frame to images in the signs folder.
    Uses Template Matching (Similarity score) instead of bit-wise comparison.
    """
    best_match = None
    max_val = -1
    
    # Convert frame to grayscale for faster/more accurate comparison
    gray_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    
    # Check if folder is empty
    if not os.listdir(SIGNS_FOLDER):
        return None

    for file_name in os.listdir(SIGNS_FOLDER):
        if file_name.lower().endswith(('.png', '.jpg', '.jpeg')):
            path = os.path.join(SIGNS_FOLDER, file_name)
            template = cv2.imread(path, 0)
            if template is None: continue
            
            # Resize template to match a portion of the frame
            # (Basic approach: match template to frame size)
            t_h, t_w = template.shape[:2]
            f_h, f_w = gray_frame.shape[:2]
            
            # To make it work, we resize the template to roughly match the camera input
            scaling_factor = f_h / t_h
            resized_template = cv2.resize(template, (int(t_w * scaling_factor), f_h))
            
            # Use OpenCV Template Matching
            res = cv2.matchTemplate(gray_frame, resized_template, cv2.TM_CCOEFF_NORMED)
            _, val, _, _ = cv2.minMaxLoc(res)
            
            if val > max_val:
                max_val = val
                best_match = os.path.splitext(file_name)[0].upper()
    
    # Sensitivity Threshold: 0.6 means 60% similarity
    return best_match if max_val > 0.6 else None

# --- UI LOGIC ---
st.title("AI Speech ↔ Sign Letters Demo 🎤🖐️")
mode = st.selectbox("Select mode:", ["Speech → Letters", "Letter Image → Speech", "Live Camera → Letters"])

# ========================
# Mode 1: Speech → Letters
# ========================
if mode == "Speech → Letters":
    st.header("Speech → Letters")
    uploaded_file = st.file_uploader("Upload speech (wav/mp3):", type=["wav","mp3"])
    
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
            
            # Display signs in a row
            char_list = [c for c in text if c.isalnum()]
            if char_list:
                cols = st.columns(len(char_list))
                for i, char in enumerate(char_list):
                    img_path = os.path.join(SIGNS_FOLDER, f"{char}.jpg")
                    if os.path.exists(img_path):
                        cols[i].image(Image.open(img_path), caption=char)
        except Exception as e:
            st.error(f"Could not process audio: {e}")

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
