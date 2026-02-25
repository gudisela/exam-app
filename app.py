from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
import base64
import cloudinary
import cloudinary.uploader

# ---------------------------------------
# FLASK APP
# ---------------------------------------

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ---------------------------------------
# CLOUDINARY CONFIG
# ---------------------------------------

cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET")
)

# ---------------------------------------
# DATABASE MODELS
# ---------------------------------------

class Exam(db.Model):
    exam_id = db.Column(db.String(50), primary_key=True)
    title = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.String(50),
                        db.ForeignKey('exam.exam_id', ondelete="CASCADE"))
    question_index = db.Column(db.Integer)
    question_text = db.Column(db.Text)
    answer_diagram = db.Column(db.Text)
    drawing_enabled = db.Column(db.Boolean, default=False)


class EmbeddedDiagram(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer,
                            db.ForeignKey('question.id', ondelete="CASCADE"))
    image_url = db.Column(db.Text)


class Attempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.String(50),
                        db.ForeignKey('exam.exam_id', ondelete="CASCADE"))
    student_name = db.Column(db.Text)
    submitted = db.Column(db.Boolean, default=False)


class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer,
                           db.ForeignKey('attempt.id', ondelete="CASCADE"))
    question_index = db.Column(db.Integer)
    answer_text = db.Column(db.Text)
    overlay_image = db.Column(db.Text)

# ---------------------------------------
# INIT DATABASE
# ---------------------------------------

@app.route("/initdb")
def initdb():
    db.create_all()
    return "Database initialized"

# ---------------------------------------
# HOME
# ---------------------------------------

@app.route("/")
def index():
    return redirect("/teacher/create_exam")

# ---------------------------------------
# TEACHER — CREATE EXAM
# ---------------------------------------

@app.route("/teacher/create_exam")
def teacher_create_exam():
    return render_template("create_exam.html")

# ---------------------------------------
# TEACHER — SAVE EXAM
# ---------------------------------------

@app.route("/teacher/save_exam", methods=["POST"])
def teacher_save_exam():

    exam_id = request.form.get("exam_id").lower()
    exam_title = request.form.get("title")

    existing_exam = Exam.query.get(exam_id)
    if existing_exam:
        return f"Exam '{exam_id}' already exists"

    exam = Exam(exam_id=exam_id, title=exam_title)
    db.session.add(exam)
    db.session.flush()

    question_index = 1

    for key in request.form.keys():

        if key.startswith("qtext_"):

            qnum = key.split("_")[1]
            qtext = request.form.get(key)

            q = Question(
                exam_id=exam_id,
                question_index=question_index,
                question_text=qtext
            )

            db.session.add(q)
            db.session.flush()

            for subkey in sorted(request.form.keys()):

                if subkey.startswith(f"embedded_{qnum}_"):

                    dataurl = request.form.get(subkey)

                    if dataurl and dataurl.startswith("data:image"):

                        img_data = base64.b64decode(dataurl.split(",")[1])
                        upload_result = cloudinary.uploader.upload(img_data)

                        db.session.add(EmbeddedDiagram(
                            question_id=q.id,
                            image_url=upload_result["secure_url"]
                        ))

            answer_dataurl = request.form.get(f"answer_diagram_{qnum}")
            answer_enabled = request.form.get(f"answer_enabled_{qnum}")

            if answer_dataurl and answer_dataurl.startswith("data:image"):

                img_data = base64.b64decode(answer_dataurl.split(",")[1])
                upload_result = cloudinary.uploader.upload(img_data)

                q.answer_diagram = upload_result["secure_url"]
                q.drawing_enabled = bool(answer_enabled)

            question_index += 1

    db.session.commit()

    return redirect(f"/exam/start/{exam_id}")

# ---------------------------------------
# STUDENT — START EXAM
# ---------------------------------------

@app.route("/exam/start/<exam_id>")
def start_exam(exam_id):

    exam = Exam.query.get(exam_id)

    if not exam:
        return "Exam not found", 404

    questions = Question.query.filter_by(exam_id=exam_id)\
        .order_by(Question.question_index).all()

    for q in questions:
        q.embedded_diagrams = EmbeddedDiagram.query\
            .filter_by(question_id=q.id).all()

    return render_template(
        "student_exam.html",
        exam_id=exam_id,
        exam_title=exam.title,
        questions=questions
    )

# ---------------------------------------
# AUTOSAVE ANSWER
# ---------------------------------------

@app.route("/exam/autosave", methods=["POST"])
def exam_autosave():

    data = request.get_json()

    exam_id = data.get("exam_id")
    student = data.get("studentName")
    qindex = int(data.get("qindex"))
    answer_text = data.get("answerText")
    overlay = data.get("overlayImage")

    attempt = Attempt.query.filter_by(
        exam_id=exam_id,
        student_name=student
    ).first()

    if not attempt:
        attempt = Attempt(exam_id=exam_id, student_name=student)
        db.session.add(attempt)
        db.session.flush()

    answer = Answer.query.filter_by(
        attempt_id=attempt.id,
        question_index=qindex
    ).first()

    if not answer:
        answer = Answer(attempt_id=attempt.id, question_index=qindex)

    overlay_url = None

    if overlay and overlay.startswith("data:image"):

        print("\n--- OVERLAY RECEIVED ---")
        print("Length:", len(overlay))

        img_data = base64.b64decode(overlay.split(",")[1])
        upload_result = cloudinary.uploader.upload(img_data)

        overlay_url = upload_result["secure_url"]

        print("\n--- CLOUDINARY UPLOAD OK ---")
        print("Overlay URL:", overlay_url)

    answer.answer_text = answer_text
    answer.overlay_image = overlay_url

    db.session.add(answer)
    db.session.commit()

    return jsonify({"status": "saved"})

# ---------------------------------------
# FINAL SUBMIT
# ---------------------------------------

@app.route("/exam/submit", methods=["POST"])
def exam_submit():

    data = request.get_json()

    exam_id = data.get("exam_id")
    student = data.get("studentName")

    attempt = Attempt.query.filter_by(
        exam_id=exam_id,
        student_name=student
    ).first()

    if not attempt:
        return jsonify({"status": "error", "message": "No attempt found"})

    attempt.submitted = True
    db.session.commit()

    return jsonify({"status": "submitted"})

# ---------------------------------------
# RUN
# ---------------------------------------

if __name__ == "__main__":
    app.run()
