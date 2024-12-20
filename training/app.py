import joblib
import streamlit as st


model = joblib.load("training/svc_pipeline.pkl")
st.title("Text Classification - RNA Related or Not")
user_input = st.text_area("Enter text for classification:", "")

if st.button("Classify"):
    if user_input.strip():
        prediction = model.predict([user_input])[0]
        result = "RNA-related" if prediction else "Not RNA-related"
        st.success(f"Prediction: {result}")
    else:
        st.warning("Please enter some text before classifying.")
