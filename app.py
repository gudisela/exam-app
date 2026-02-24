from flask import Flask, render_template, request, send_from_directory, jsonify, redirect, send_file
import os
import base64
import datetime
import json

app = Flask(__name__)

# ---------------------------------------
# BASE DIRECTORIES
# ---------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DIAGRAM_FOLDER = os.path.join(BASE_DIR, "diagrams")
EXAMS_DIR = os.path.join(BASE_DIR, "exams")
ATTEMPTS_DIR = os.path.join(BASE_DIR, "attempts")
DRAWINGS_DIR = os.path.join(BASE_DIR, "drawings")

for d in [DIAGRAM_FOLDER, EXAMS_DIR, ATTEMPTS_DIR, DRAWINGS_DIR]:
    os.makedirs(d, exist_ok=True)

# ---------------------------------------
# HOME REDIRECT (GitHub improvement)
# ---------------------------------------

@app.route("/")
def index():
    return redirect("/teacher/create_exam")

# ---------------------------------------
# SERVE DRAWINGS
# ---------------------------------------

@app.route("/drawing/<filename>")
def serve_drawing(filename):

    fullpath = os.path.join(DRAWINGS_DIR, filename)

    if not os.path.exists(fullpath):
        return "File NOT FOUND", 404

    return send_file(fullpath)

# ---------------------------------------
# TEACHER — CREATE EXAM
# ---------------------------------------

@app.route("/teacher/create_exam")
def teacher_create_exam():
    return render_template("create_exam.html")

@app.route("/teacher/save_exam", methods=["POST"])
def teacher_save_exam():

    exam_id = request.form.get("exam_id").lower()
    exam_title = request.form.get("title")

    exam_folder = os.path.join(EXAMS_DIR, exam_id)
    os.makedirs(exam_folder, exist_ok=True)

    questions = []

    for key in request.form.keys():

        if key.startswith("qtext_"):

            qnum = key.split("_")[1]
            qtext = request.form.get(key)

            embedded_images = []
            counter = 1

            for subkey in sorted(request.form.keys()):

                if subkey.startswith(f"embedded_{qnum}_"):

                    dataurl = request.form.get(subkey)

                    if dataurl and dataurl.startswith("data:image"):

                        img_data = base64.b64decode(dataurl.split(",")[1])
                        filename = f"q{qnum}_embedded_{counter}.png"

                        with open(os.path.join(exam_folder, filename), "wb") as f:
                            f.write(img_data)

                        embedded_images.append(filename)
                        counter += 1

            answer_dataurl = request.form.get(f"answer_diagram_{qnum}")
            answer_enabled = request.form.get(f"answer_enabled_{qnum}")

            answer_diagram = {"enabled": False}

            if answer_dataurl and answer_dataurl.startswith("data:image"):

                img_data = base64.b64decode(answer_dataurl.split(",")[1])
                filename = f"q{qnum}_answer.png"

                with open(os.path.join(exam_folder, filename), "wb") as f:
                    f.write(img_data)

                answer_diagram = {
                    "enabled": bool(answer_enabled),
                    "src": filename
                }

            questions.append({
                "text": qtext,
                "embedded_diagrams": embedded_images,
                "answer_diagram": answer_diagram
            })

    with open(os.path.join(exam_folder, "meta.json"), "w") as f:
        json.dump({
            "exam_id": exam_id,
            "title": exam_title,
            "num_questions": len(questions)
        }, f, indent=4)

    with open(os.path.join(exam_folder, "questions.json"), "w") as f:
        json.dump(questions, f, indent=4)

    return redirect(f"/exam/start/{exam_id}")

# ---------------------------------------
# STUDENT — START EXAM
# ---------------------------------------

@app.route("/exam/start/<exam_id>")
def start_exam(exam_id):

    exam_folder = os.path.join(EXAMS_DIR, exam_id)

    meta_path = os.path.join(exam_folder, "meta.json")
    questions_path = os.path.join(exam_folder, "questions.json")

    if not os.path.exists(meta_path):
        return "Exam not found", 404

    with open(meta_path) as f:
        meta = json.load(f)

    with open(questions_path) as f:
        questions = json.load(f)

    return render_template(
        "student_exam.html",
        exam_id=exam_id,
        exam_title=meta.get("title"),
        questions=questions
    )

# ---------------------------------------
# SERVE EXAM FILES
# ---------------------------------------

@app.route("/exam_file/<exam_id>/<filename>")
def exam_file(exam_id, filename):
    exam_folder = os.path.join(EXAMS_DIR, exam_id)
    return send_from_directory(exam_folder, filename)

# ---------------------------------------
# RUN (Render-safe)
# ---------------------------------------

if __name__ == "__main__":
    app.run()
