import streamlit as st
import pdfplumber
import cohere
import os
import re

# ---- Page Configuration ----
st.set_page_config(page_title="ATS Resume Expert", layout="centered", page_icon="📄")

# ---- Custom Dark Theme ----
st.markdown("""
    <style>
    body, .stApp {
        background-color: #1e1e1e;
        color: #ffffff;
    }
    .stTextArea textarea, .stTextInput input {
        background-color: #2d2d2d !important;
        color: #ffffff !important;
    }
    .stButton button {
        background-color: #4CAF50;
        color: white;
        border-radius: 10px;
    }
    .result-box {
        border-left: 5px solid #4CAF50;
        background-color: #2e7d32;
        padding: 15px;
        border-radius: 10px;
        margin-top: 10px;
        color: #ffffff;
    }
    </style>
""", unsafe_allow_html=True)

# ---- Header ----
st.title("📄 ATS Resume Checker")
st.markdown("""
Upload **multiple resumes** and compare them with a job description using **Cohere AI**.  
Get both **HR-style feedback** and **ATS match scoring** for each candidate!
""")

# ---- API Key ----
COHERE_API_KEY = "4GTzqZ8iZrLTzJW1czAzQvzN763pSgNSuNAPWHY5"
# COHERE_API_KEY = os.getenv("COHERE_API_KEY")

if not COHERE_API_KEY:
    st.error("❌ Cohere API key not configured.")
    st.stop()

co = cohere.Client(COHERE_API_KEY)

# ---- Resume Text Extractor ----
def extract_resume_text(uploaded_file):
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            text = ''.join([page.extract_text() + '\n' for page in pdf.pages if page.extract_text()])
        return text.strip()
    except Exception as e:
        st.error(f"❌ Error reading {uploaded_file.name}: {e}")
        return None

# ---- Prompt Creators ----
def create_hr_prompt(resume_text, job_desc):
    return (
        "You are an experienced HR professional. Given the following job description and resume text, "
        "please provide an evaluation of the candidate. Highlight strengths, weaknesses, skill match, "
        "and areas for improvement.\n\n"
        f"Job Description:\n{job_desc}\n\n"
        f"Resume:\n{resume_text}"
    )

def create_ats_prompt(resume_text, job_desc):
    return (
        "Act as an ATS (Applicant Tracking System). Analyze the resume and the job description. "
        "Give a match percentage (0–100%), list missing keywords, and provide a summary.\n\n"
        f"Job Description:\n{job_desc}\n\n"
        f"Resume:\n{resume_text}"
    )

# ---- Cohere Chat API ----
def generate_cohere_response(prompt):
    try:
        response = co.chat(model="command-r-plus", message=prompt)
        return response.text
    except Exception as e:
        st.error(f"❌ Cohere API Error: {e}")
        return None

# ---- Display Helper ----
def display_result(title, content):
    st.subheader(title)
    st.markdown(f"<div class='result-box'>{content}</div>", unsafe_allow_html=True)

# ---- Input Fields ----
st.header("📥 Provide Your Inputs")
job_description = st.text_area("📝 Paste the Job Description", placeholder="Job responsibilities, qualifications, skills, etc.")
uploaded_files = st.file_uploader("📎 Upload Multiple Resumes (PDF only)", type=["pdf"], accept_multiple_files=True)

# Control buttons and inputs in a row
col1, col2, col3, col4 = st.columns([1, 1, 2, 1])

with col1:
    submit_hr = st.button("🔍 HR Evaluation")

with col2:
    submit_ats = st.button("📊 ATS Match Score")

with col3:
    threshold = st.number_input("🎯 Threshold %", min_value=0, max_value=100, value=70, step=5, label_visibility="collapsed")

with col4:
    shortlist_button = st.button("🏆 Shortlist")

# ---- HR Evaluation Logic ----
if submit_hr:
    if uploaded_files and job_description.strip():
        for file in uploaded_files:
            with st.spinner(f"🧠 Evaluating {file.name} from HR perspective..."):
                resume_text = extract_resume_text(file)
                if resume_text:
                    prompt = create_hr_prompt(resume_text, job_description)
                    response = generate_cohere_response(prompt)
                    if response:
                        display_result(f"💬 HR Evaluation: {file.name}", response)
    else:
        st.warning("⚠️ Please upload resumes and a job description.")

# ---- ATS Match Score Logic ----
if submit_ats or shortlist_button:
    if uploaded_files and job_description.strip():
        ats_results = []

        for file in uploaded_files:
            with st.spinner(f"⚙️ Evaluating ATS compatibility for {file.name}..."):
                resume_text = extract_resume_text(file)
                if resume_text:
                    prompt = create_ats_prompt(resume_text, job_description)
                    response = generate_cohere_response(prompt)
                    if response:
                        match = re.search(r'(\d{1,3})\s*%?', response)
                        percentage = int(match.group(1)) if match else 0
                        ats_results.append((file.name, percentage, response))

        ats_results.sort(key=lambda x: x[1], reverse=True)

        if submit_ats:
            st.markdown("## ✅ Sorted ATS Results")
            for name, percent, result in ats_results:
                display_result(f"📄 {name} - {percent}%", result)

        if shortlist_button:
            st.markdown(f"## 🏆 Shortlisted Candidates (≥ {threshold}%)")
            shortlisted = [res for res in ats_results if res[1] >= threshold]
            if shortlisted:
                for name, percent, _ in shortlisted:
                    st.success(f"{name} - {percent}% match")
            else:
                st.warning(f"❌ No resumes met the {threshold}% ATS match threshold.")
    else:
        st.warning("⚠️ Please upload resumes and a job description.")
