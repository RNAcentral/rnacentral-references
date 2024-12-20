import joblib
import streamlit as st


model = joblib.load("training/svc_pipeline.pkl")
st.title("Text Classification - RNA Related or Not")
user_input = st.text_area("Enter text for classification:", "")

if st.button("Classify"):
    if user_input.strip():
        prediction = model.predict([user_input])[0]
        if prediction:
            st.success(f"Prediction: RNA-related")
        else:
            st.error("Prediction: Not RNA-related")
    else:
        st.warning("Please enter some text before classifying.")
