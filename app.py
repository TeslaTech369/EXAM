import streamlit as st
from pymongo import MongoClient
from PIL import Image
import io,os
import random
from datetime import datetime
from dotenv import load_dotenv

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["exam_database"]

USERNAME = st.secrets.get("USERNAME")
PASSWORD = st.secrets.get("PASSWORD")

# Admin Login
def admin_login():
    st.title("Admin Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username == USERNAME and password == PASSWORD:
            st.session_state["admin_logged_in"] = True
            st.success("Logged in as Admin")
            st.rerun()
        else:
            st.error("Invalid credentials")

# Admin Panel

def admin_panel():
    st.title("Admin Panel")

    # Create Exam
    st.subheader("Create New Exam")
    exam_name = st.text_input("Exam Name")
    exam_duration = st.number_input("Duration (minutes)", min_value=1)
    if st.button("Create Exam"):
        db.exams.insert_one({"name": exam_name, "duration": exam_duration})
        st.success(f"Exam '{exam_name}' created.")

    # Add Question
    st.subheader("Add Question")
    exams = list(db.exams.find())
    exam_options = [exam["name"] for exam in exams]
    selected_exam = st.selectbox("Select Exam", exam_options)
    question_text = st.text_area("Question")
    options = [st.text_input(f"Option {i}") for i in range(1, 5)]
    correct_answer = st.selectbox("Correct Answer", options)
    image = st.file_uploader("Upload Image (optional)", type=["jpg", "png", "jpeg"])

    if st.button("Add Question"):
        question_data = {
            "exam": selected_exam,
            "question": question_text,
            "options": options,
            "answer": correct_answer,
            "image": image.read() if image else None
        }
        db.questions.insert_one(question_data)
        st.success("Question added successfully.")

# Student Portal

def student_interface():
    st.title("Student Exam Portal")
    name = st.text_input("Name")
    roll = st.text_input("Roll Number")
    exams = list(db.exams.find())
    exam_options = [exam["name"] for exam in exams]
    selected_exam = st.selectbox("Select Exam", exam_options)

    if st.button("Start Exam") and name and roll:
        st.session_state["student"] = {"name": name, "roll": roll}
        st.session_state["exam"] = selected_exam
        st.session_state["start_time"] = datetime.now()
        st.session_state["questions"] = list(db.questions.find({"exam": selected_exam}))
        random.shuffle(st.session_state["questions"])
        st.session_state["responses"] = {}
        st.session_state["current_question"] = 0
        st.session_state["exam_duration"] = next(exam["duration"] for exam in exams if exam["name"] == selected_exam)
        st.rerun()

# Timer & Question Loop

def exam_interface():
    elapsed_time = (datetime.now() - st.session_state["start_time"]).seconds
    remaining_time = st.session_state["exam_duration"] * 60 - elapsed_time
    timer_placeholder = st.empty()

    if remaining_time <= 0:
        st.warning("Time's up! Submitting exam...")
        submit_exam()
        return

    minutes, seconds = divmod(remaining_time, 60)
    st.info(f"Time Remaining: {minutes} minutes {seconds} seconds")

    questions = st.session_state["questions"]
    
    current = st.session_state["current_question"]

    if current < len(questions):
        q = questions[current]
        st.subheader(f"Question {current + 1}")
        st.write(q["question"])
        if q.get("image"):
            st.image(Image.open(io.BytesIO(q["image"])))
        
        selected_option = st.radio("Options", q["options"], index=None, key=current)
        
        # If we are on the last question, show the Submit button
        if current == len(questions) - 1:
            if st.button("Submit Exam"):
                st.session_state["responses"][q["question"]] = selected_option
                submit_exam()
                st.stop()  # Prevent any further execution after submit

        # Button to move to the next question
        if st.button("Next"):
            # Save response for the current question
            st.session_state["responses"][q["question"]] = selected_option
            st.session_state["current_question"] += 1
            st.rerun()
    else:
        submit_exam()

        
        
# Submit Exam

def submit_exam():
    responses = st.session_state["responses"]
    questions = st.session_state["questions"]
    correct = sum(1 for q in questions if responses.get(q["question"]) == q["answer"])
    total = len(questions)
    st.success(f"Exam Completed! Score: {correct}/{total}")

    result = {
        "name": st.session_state["student"]["name"],
        "roll": st.session_state["student"]["roll"],
        "exam": st.session_state["exam"],
        "score": correct,
        "total": total,
        "timestamp": datetime.now()
    }
    db.results.insert_one(result)

    for key in ["student", "exam", "start_time", "questions", "responses", "current_question", "exam_duration"]:
        st.session_state.pop(key, None)

# Leaderboard

def leaderboard():
    st.title("Leaderboard")
    exams = list(db.exams.find())
    exam_options = [exam["name"] for exam in exams]
    selected_exam = st.selectbox("Select Exam", exam_options)

    results = list(db.results.find({"exam": selected_exam}))
    sorted_results = sorted(results, key=lambda x: x["score"], reverse=True)

    st.subheader(f"Top Performers in {selected_exam}")
    for idx, res in enumerate(sorted_results[:10], start=1):
        st.write(f"{idx}. {res['name']} ({res['roll']}) - Score: {res['score']}/{res['total']}")

# Main App

def main():
    st.set_page_config(page_title="Exam Portal", page_icon="📝")
    menu = ["Student", "Admin", "Leaderboard"]
    choice = st.sidebar.selectbox("Menu", menu)

    if choice == "Admin":
        if st.session_state.get("admin_logged_in"):
            admin_panel()
        else:
            admin_login()
    elif choice == "Student":
        if "student" in st.session_state:
            exam_interface()
        else:
            student_interface()
    elif choice == "Leaderboard":
        leaderboard()

if __name__ == '__main__':
    main()
