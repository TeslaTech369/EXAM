import streamlit as st
from pymongo import MongoClient
from PIL import Image
import io,os
import random
from datetime import datetime
from dotenv import load_dotenv
from PIL import Image

st.set_page_config(page_title="Dreamers Online School", page_icon="📝")

image_url = "https://i.postimg.cc/0N8VLP5t/Screenshot-2025-05-05-135252.png"

st.markdown(f"""
    <style>
        .header-container {{
            display: flex;
            align-items: center;
            gap: 20px;
            margin-bottom: 20px;
        }}
        .circular-image {{
            width: 80px;
            height: 80px;
            border-radius: 50%;
            object-fit: cover;
            border: 2px solid #f0eded;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }}
        .app-title {{
            font-size: 32px;
            font-weight: bold;
            color: #f0eded;
        }}
    </style>
    <div class="header-container">
        <img src="{image_url}" class="circular-image">
        <div class="app-title">Dreamers Online School</div>
    </div>
""", unsafe_allow_html=True)

# MongoDB connection
MONGO_URI = os.getenv("mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client["exam_database"]

USERNAME = "a"
PASSWORD = "a"


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
    exam_name = st.text_input("Exam Name")
    exam_duration = st.number_input("Duration (minutes)", min_value=1)
    negative_marking = st.checkbox("Enable Negative Marking (-0.25 per wrong answer)", value=False)

    if st.button("Create Exam"):
        db.exams.insert_one({
           "name": exam_name,
           "duration": exam_duration,
           "negative_marking": negative_marking
           })
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

    if remaining_time <= 0:
        st.warning("⏰ Time's up! Submitting exam...")
        submit_exam()
        return

    minutes, seconds = divmod(remaining_time, 60)
    st.info(f"⏳ Time Remaining: {minutes} minutes {seconds} seconds")

    questions = st.session_state["questions"]

    for idx, q in enumerate(questions):
        st.markdown(f"### Question {idx + 1}")
        st.write(q["question"])
        if q.get("image"):
            st.image(Image.open(io.BytesIO(q["image"])))
        
        selected = st.radio(
            f"Select your answer for Question {idx + 1}",
            q["options"],
            index=None,
            key=f"question_{idx}"
        )
        st.session_state["responses"][q["question"]] = selected

    if st.button("✅ Submit Exam"):
        submit_exam()

        
        
# Submit Exam

# Submit Exam with success and warning messages
def submit_exam():
    responses = st.session_state["responses"]
    questions = st.session_state["questions"]
    exam_info = db.exams.find_one({"name": st.session_state["exam"]})
    negative_marking = exam_info.get("negative_marking", False)
    
    correct = 0
    wrong = 0
    score = 0

    # Calculate the score
    for q in questions:
        user_answer = responses.get(q["question"])

        if user_answer is None:
            continue
        elif user_answer == q["answer"]:
            correct += 1
        else:
            wrong += 1

        if negative_marking:
            score = correct - 0.25 * wrong
            score = max(score, 0)  # prevent negative total
        else:
            score = correct

    total = len(questions)
    
    # Save result to the database
    result = {
        "name": st.session_state["student"]["name"],
        "roll": st.session_state["student"]["roll"],
        "exam": st.session_state["exam"],
        "score": score,
        "total": total,
        "correct": correct,
        "wrong": wrong,
        "timestamp": datetime.now()
    }
    db.results.insert_one(result)

    # Show the result to the student
    st.success(f"✅ Exam Completed! Your Score: {score}/{total} (Correct: {correct}, Wrong: {wrong})")
    
    # Display the student's answers with success or warning message
    st.subheader("Your Exam Results:")
    
    for idx, q in enumerate(questions):
        st.markdown(f"### Question {idx + 1}")
        st.write(q["question"])
        
        # Show the options for the question
        for i, option in enumerate(q["options"], 1):
            st.write(f"{i}. {option}")
        
        # Show the selected answer by the student
        student_answer = responses.get(q["question"], "No Answer")
        
        # Determine if the answer is correct or wrong
        if student_answer == "No Answer":
            st.warning(f"**Your Answer:** {student_answer} - You didn't attempt this question.")
        elif student_answer == q["answer"]:
            st.success(f"**Your Answer:** {student_answer} - Correct!")
        else:
            st.warning(f"**Your Answer:** {student_answer} - Incorrect!")
        
        # Show the correct answer with success message
        correct_answer = q["answer"]
        st.success(f"**Correct Answer:** {correct_answer}")
        
        st.write("---")  # Divider between questions

    # Clear the session state after displaying the results
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
    #st.set_page_config(page_title="Exam Portal", page_icon="📝")
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
