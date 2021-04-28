import pickle
from konlpy.tag import Okt
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.sequence import pad_sequences

#def load_sent_model():
#    sent_model = load_model('pretrained_lstm/best_model.h5')
#    with open("pretrained_lstm/tokenizer.pickle", "rb") as handle:
#        sent_tokenizer = pickle.load(handle)
#    okt = Okt()
#    return okt, sent_model, sent_tokenizer

def sentiment_predict(new_sentence):
    okt = Okt()
    sent_model = load_model('pretrained_lstm/best_model.h5')
    with open("pretrained_lstm/tokenizer.pickle", "rb") as handle:
        sent_tokenizer = pickle.load(handle)
    stopwords = ['의','가','이','은','들','는','좀','잘','걍','과','도','를','으로','자','에','와','한','하다']
    new_sentence = okt.morphs(new_sentence, stem=True) # 토큰화
    new_sentence = [word for word in new_sentence if not word in stopwords] # 불용어 제거
    encoded = sent_tokenizer.texts_to_sequences([new_sentence]) # 정수 인코딩
    pad_new = pad_sequences(encoded, maxlen = 30) # 패딩
    score = float(sent_model.predict(pad_new)) # 예측
    if(score > 0.5):
        answer_text = "{:.2f}% 확률로 긍정 리뷰입니다.\n".format(score * 100)
        return answer_text
    else:
        answer_text = "{:.2f}% 확률로 부정 리뷰입니다.\n".format((1 - score) * 100)
        return answer_text
