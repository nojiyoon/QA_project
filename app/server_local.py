# flask_app/server.py​
import datetime
import re

#from flask_ngrok import run_with_ngrok 
from flask import Flask, request, jsonify, render_template, session, url_for, redirect
from flask_dropzone import Dropzone
import time
from urllib.parse import unquote
import os
import uuid
import secrets

from run_squad import evaluate, load_model
from run_sent_classify import sentiment_predict
from squad_generator import convert_text_input_to_squad, \
    convert_file_input_to_squad, convert_context_and_questions_to_squad
from settings import *
import requests
import pdb
import wikipediaapi

# infer를 위해 estimator와 tokenizer를 load_model 함수를 이용해 불러옵니다. 
estimator, tokenizer = load_model()

app = Flask(__name__)

# colab에서의 서빙을 위해 flask_ngrok 모듈의 run_with_ngrok 함수를 사용합니다.
#run_with_ngrok(app)

app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['DROPZONE_UPLOAD_MULTIPLE'] = True
app.config['DROPZONE_ALLOWED_FILE_TYPE'] = 'text'
app.config.update(
    SECRET_KEY=secrets.token_urlsafe(32),
    SESSION_COOKIE_NAME='InteractiveTransformer-WebSession'
)

dropzone = Dropzone(app)

def delay_func(func):
    def inner(*args, **kwargs):
        returned_value = func(*args, **kwargs)
        time.sleep(0)
        return returned_value
    return inner

# 실행 시작
@app.route("/")
def index():
    # 처음 보여지는 화면입니다. 
    return render_template("index.html")

@app.route("/", methods=['POST'])
def process_input():
    if request.files:
        if "file_urls" not in session:
            session['file_urls'] = []
            # list to hold our uploaded image urls
        file_urls = session['file_urls']

        file_obj = request.files
        for f in file_obj:
            file = request.files.get(f)
            app.logger.info("file upload {}".format(file.filename))
            os.makedirs("./uploads", exist_ok=True)
            filepath = os.path.join('./uploads', secrets.token_urlsafe(8))
            file.save(filepath)
            file_urls.append(filepath)
        return "upload"
    else:
        # client로 부터 정보를 받습니다.
        input = request.form["textbox"]
        try:
            return predict_from_text_squad(input)
        except AssertionError:
            return index()

@app.route("/_wiki_api")
def wiki_api():
    text = unquote(request.args.get("my_input", "", type=str)).strip()
    wiki = wikipediaapi.Wikipedia("ko")
    page_py = wiki.page(text)
    if page_py.exists():
        res_title = page_py.title
        res_sum = page_py.summary[:1000]
    else:
        pass

    return jsonify(context='\n'.join([res_title, res_sum]))

def predict_from_text_squad(input):
    squad_dict = convert_text_input_to_squad(input)
    return package_squad_prediction(squad_dict)

def predict_from_file_squad(input):
    try:
        squad_dict = convert_file_input_to_squad(input)
    except AssertionError:
        return []
    return package_squad_prediction(squad_dict)

def predict_from_input_squad(context, questions, id):
    squad_dict = convert_context_and_questions_to_squad(context, questions)
    return package_squad_prediction(squad_dict, id)

def package_squad_prediction(squad_dict, id="context-default"):
    prediction, dt = evaluate_input(squad_dict)
    packaged_predictions = []
    highlight_script = ""
    for entry in squad_dict["data"]:
        title = entry["title"]
        inner_package = []
        for p in entry["paragraphs"]:
            context = p["context"]
            #pdb.set_trace()
            qas = [(q["question"], prediction[q["id"]][0],
                    datetime.datetime.now().strftime("%d %B %Y %I:%M%p"),
                    "%0.02f seconds" % (dt),
                    '#' + id,
                    generate_highlight(context, id, prediction[q["id"]][1], prediction[q["id"]][2])) for q in p["qas"]]
            if not highlight_script:
                highlight_script = qas[0][5]
            inner_package.append((context, qas))
        packaged_predictions.append((title, inner_package))
    return packaged_predictions, highlight_script

def generate_highlight(context, id, start_index, stop_index):
    if start_index > -1:
        context_split = context.split()
        start_index = len(" ".join(context_split[:start_index]))
        stop_index = len(" ".join(context_split[:stop_index + 1]))
    return 'highlight(' + '"#' + id + '",' + str(start_index) + ',' + str(stop_index) + ');return false;'

def evaluate_input(squad_dict, passthrough=False):
    predict_file = squad_dict
    t = time.time()
    predictions = evaluate(predict_file, estimator, tokenizer)
    dt = time.time() - t
    app.logger.info("Loading time: %0.02f seconds" % (dt))
    if passthrough:
        return predictions, squad_dict, dt
    return predictions, dt

@app.route('/_evaluate_helper')
def evaluate_helper():
    eval_text = request.args.get("evaluate_data", "", type=str).strip()
    prediction = sentiment_predict(eval_text)
    if prediction and eval_text:
        return jsonify(result=
                       render_template('live_eval.html',
                                       predict=[prediction],
                                       eval_text=[eval_text]))
    return jsonify(result="")

@app.route('/_input_helper')
def input_helper():
    context = session['context'][-1]
    text = context[0]
    id = context[1]
    questions = unquote(request.args.get("question_data", "", type=str)).strip()
    app.logger.info("input text: {}\n\nquestions:{}".format(text, questions))
    predictions, highlight = predict_from_input_squad(text, questions, id)
    if text and questions:
        return jsonify(result=
                       render_template('live_results.html',
                                       predict=predictions),
                       highlight_script=highlight)
    return jsonify(result="")

@app.route('/_store_context')
@delay_func
def store_context():
    text = unquote(request.args.get("text_data", "", type=str)).strip()
    app.logger.info("input text: {}".format(text))

    remove_files = False
    if not text:
        if "file_urls" not in session or session['file_urls'] == []:
            return redirect(url_for('index'))
        file_urls = session['file_urls']
        session.pop('file_urls', None)
        with open(file_urls[-1], "r") as f:
            text = f.read()
        for f in file_urls:
            if os.path.exists(f):
                os.remove(f)
        remove_files = True

    if text:
        # if "context" not in session:
        session['context'] = []
        split_text = text.split("\n", 1)
        if len(split_text) > 1:
            # print(session['context'])
            curr_id = str(uuid.uuid4().hex[:8])
            session['context'].append((text, curr_id))
            session.modified = True
            return jsonify(title=split_text[0].strip(),
                           context=render_template("unique_context.html",
                                                    unique_id=curr_id,
                                                    content=re.sub("\n+", "\n", split_text[1].strip())),
                           clear_files=remove_files)
        else:
            return jsonify(context="")



if __name__ == '__main__':
    #app.run(host="0.0.0.0", debug=True, port=PORT)
    app.run()
