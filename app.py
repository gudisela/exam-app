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
# SERVE DIAGRAMS
# ---------------------------------------


@app.route("/drawing/<filename>")
def serve_drawing(filename):

    fullpath = os.path.join(DRAWINGS_DIR, filename)

    print("Serving file:", fullpath)
    print("Exists:", os.path.exists(fullpath))

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

            # ----------------------
            # SAVE EMBEDDED IMAGES
            # ----------------------

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

            # ----------------------
            # SAVE ANSWER DIAGRAM
            # ----------------------

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

    # ----------------------
    # SAVE META
    # ----------------------

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

    with open(os.path.join(exam_folder, "meta.json")) as f:
        meta = json.load(f)

    with open(os.path.join(exam_folder, "questions.json")) as f:
        questions = json.load(f)

    return render_template(
        "student_exam.html",
        exam_id=exam_id,
        exam_title=meta.get("title"),
        questions=questions
    )


# ✅ ADD IT HERE (good location)

@app.route("/exam_file/<exam_id>/<filename>")
def exam_file(exam_id, filename):

    exam_folder = os.path.join(EXAMS_DIR, exam_id)

    print("\n--- FILE DEBUG ---")
    print("EXAMS_DIR =", EXAMS_DIR)
    print("Exam folder =", exam_folder)
    print("Filename =", filename)
    print("Full path =", os.path.join(exam_folder, filename))
    print("Exists =", os.path.exists(os.path.join(exam_folder, filename)))

    return send_from_directory(exam_folder, filename)


# ---------------------------------------
# AUTOSAVE
# ---------------------------------------
@app.route("/exam/autosave", methods=["POST"])
def exam_autosave():

    data = request.get_json()

    exam_id = data.get("exam_id")              # ⭐ DO NOT LOWERCASE
    qindex = str(data.get("qindex"))

    student_raw = data.get("studentName", "Unknown")
    student = student_raw.replace(" ", "_")    # Preserve display identity

    answer = data.get("answerText", "")
    overlay = data.get("overlayImage")

    exam_attempt_folder = os.path.join(ATTEMPTS_DIR, exam_id)
    os.makedirs(exam_attempt_folder, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    # ⭐ Canonicalised values ONLY for filenames
    safe_exam_id = exam_id.lower()
    safe_student = student.lower()

    overlay_filename = None

    if overlay and overlay.startswith("data:image"):
        overlay_filename = f"{safe_exam_id}_{safe_student}_{qindex}_{timestamp}.png"

        with open(os.path.join(DRAWINGS_DIR, overlay_filename), "wb") as f:
            f.write(base64.b64decode(overlay.split(",")[1]))

    attempt_file = os.path.join(exam_attempt_folder, f"{student}.json")

    if os.path.exists(attempt_file):
        with open(attempt_file) as f:
            attempt = json.load(f)
    else:
        attempt = {
            "exam_id": exam_id,     # ⭐ Preserve original ID
            "student": student,
            "answers": {}
        }

    attempt["answers"][qindex] = {
        "answerText": answer,
        "overlay_file": overlay_filename,
        "saved_at": timestamp
    }

    with open(attempt_file, "w") as f:
        json.dump(attempt, f, indent=2)

    return jsonify({"status": "success"})

                 

# ---------------------------------------
# FINAL SUBMIT
# ---------------------------------------

@app.route("/exam/submit", methods=["POST"])
def exam_submit():

    data = request.get_json()
    exam_id = data.get("exam_id")
    student = data.get("studentName", "").replace(" ", "_")

    attempt_file = os.path.join(ATTEMPTS_DIR, exam_id, f"{student}.json")

    if not os.path.exists(attempt_file):
        return jsonify({"status": "error", "message": "Attempt not found"}), 404

    with open(attempt_file) as f:
        attempt = json.load(f)

    attempt["submitted"] = True
    attempt["submitted_at"] = datetime.datetime.now().isoformat()

    with open(attempt_file, "w") as f:
        json.dump(attempt, f, indent=2)

    return jsonify({"status": "success"})

# ---------------------------------------
# TEACHER — ATTEMPTS LIST
# ---------------------------------------

@app.route("/teacher/attempts/<exam_id>")
def teacher_attempts(exam_id):

    exam_attempt_folder = os.path.join(ATTEMPTS_DIR, exam_id)
    attempts = []

    if os.path.exists(exam_attempt_folder):
        for f in os.listdir(exam_attempt_folder):
            if f.endswith(".json"):
                attempts.append(f.replace(".json", ""))

    return render_template("teacher_marking_list.html", exam_id=exam_id, attempts=attempts)

# ---------------------------------------
# TEACHER — MARK ATTEMPT
# ---------------------------------------
@app.route("/teacher/mark/<exam_id>/<student>")
def teacher_mark_attempt(exam_id, student):

    attempt_file = os.path.join(ATTEMPTS_DIR, exam_id, f"{student}.json")

    if not os.path.exists(attempt_file):
        return "Attempt not found", 404

    with open(attempt_file) as f:
        attempt = json.load(f)

    exam_folder = os.path.join(EXAMS_DIR, exam_id)

    with open(os.path.join(exam_folder, "questions.json")) as f:
        questions = json.load(f)

    meta = {}
    meta_path = os.path.join(exam_folder, "meta.json")

    if os.path.exists(meta_path):
        with open(meta_path) as f:
            meta = json.load(f)

    return render_template(
        "teacher_mark_attempt.html",
        exam_id=exam_id,
        student=student,
        attempt=attempt,
        questions=questions,
        exam_meta=meta      # ⭐ CRITICAL FIX
    )


# ---------------------------------------
# SAVE MARKS
# ---------------------------------------

@app.route("/teacher/save_marks/<exam_id>/<student>", methods=["POST"])
def teacher_save_marks(exam_id, student):

    payload = request.get_json()

    attempt_file = os.path.join(ATTEMPTS_DIR, exam_id, f"{student}.json")

    with open(attempt_file) as f:
        attempt = json.load(f)

    attempt["grading"] = {
        "marks": payload.get("marks", {}),
        "overall_comment": payload.get("overall_comment", ""),
        "graded_at": datetime.datetime.now().isoformat()
    }

    with open(attempt_file, "w") as f:
        json.dump(attempt, f, indent=2)

    return jsonify({"status": "success"})

@app.route("/student/results/<exam_id>/<student>")
def student_results(exam_id, student):

    attempt_file = os.path.join(ATTEMPTS_DIR, exam_id, f"{student}.json")

    if not os.path.exists(attempt_file):
        return "Result not available", 404

    with open(attempt_file) as f:
        attempt = json.load(f)

    return render_template(
        "student_results.html",
        exam_id=exam_id,
        student=student,
        grading=attempt.get("grading"),
        answers=attempt.get("answers", {})
    )

@app.route("/student/review/<exam_id>/<student>")
def student_review(exam_id, student):

    attempt_file = os.path.join(ATTEMPTS_DIR, exam_id, f"{student}.json")

    if not os.path.exists(attempt_file):
        return "Attempt not found", 404

    with open(attempt_file) as f:
        attempt = json.load(f)

    grading = attempt.get("grading")

    if not grading:
        return "Paper not graded yet", 403

    exam_folder = os.path.join(EXAMS_DIR, exam_id)

    with open(os.path.join(exam_folder, "questions.json")) as f:
        questions = json.load(f)

    with open(os.path.join(exam_folder, "meta.json")) as f:
        meta = json.load(f)

    return render_template(
        "student_review.html",
        exam_id=exam_id,
        student=student,
        attempt=attempt,
        grading=grading,
        questions=questions,
        exam_title=meta.get("title")
    )



# ---------------------------------------
# RUN
# ---------------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
