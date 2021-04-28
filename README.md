# korbert_qa_demo
ETRI에서 제공하는 korbert pretrained 모델을 이용해 qa_demo 를 구현합니다.

## 코드 참조
henryzxu의 bert-qa-demo를 참고하여 작성하였습니다.

[https://github.com/henryzxu/bert-qa-demo](https://github.com/henryzxu/bert-qa-demo)

감정분류 모델은 Won Joon Yoo님의 Introduction to Deep Learning for Natural Language Processing, Wikidocs 를 참고하였습니다.

[https://wikidocs.net/44249](https://wikidocs.net/44249)

## 사용 방법
1. git repository를 clone 합니다.  
    - `git clone https://github.com/JeightAn/korbert_qa_demo.git`

2. git branch를 변경합니다.
    - `git switch test`
    
3. 가상환경을 설정합니다.
    - `conda create -n qa_demo python=3.6`

4. 가상환경을 실행합니다.
    - `conda activate qa_demo`

5. 필요한 모듈을 설치합니다.
    - `pip install -r requirements.txt`

6. pretrained_model(finetuning)을 다운로드 받습니다.
    - app 폴더 안에 pretrained_korbert 디렉토리를 저장해주세요.

7. 플라스크 앱 경로를 설정합니다.
    - `export FLASK_APP=app/server_local.py`

8. 실행합니다.
    - `flask run`
