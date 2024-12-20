import joblib
import streamlit as st
import re


def clean_text(text: str) -> str:
    """
    Change abstract by removing HTML tags, URLs, content inside brackets,
    and extra whitespace, and converts it to lowercase.

    :param text: abstract text
    :return: cleaned text
    """
    text = text.lower()
    text = re.sub(r'<[^>]*>', " ", text)
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"https?://\S+|www\.\S+", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


model = joblib.load("training/svc_pipeline.pkl")
st.title("Text Classification - RNA Related or Not")
user_input = st.text_area("Enter text for classification:", "")

if st.button("Classify"):
    if user_input:
        user_input = clean_text(user_input)
        prediction = model.predict([user_input])[0]
        if prediction:
            st.success(f"Prediction: RNA-related")
        else:
            st.error("Prediction: Not RNA-related")
    else:
        st.warning("Please enter some text before classifying.")
