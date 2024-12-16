import joblib
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import ComplementNB, MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC


def main():
    """
    Testing four text classifiers: LinearSVC, ComplementNB, MultinomialNB, and RandomForestClassifier.
    """
    df = pd.read_csv("data.csv")
    print(df["rna_related"].value_counts())
    # rna_related
    # 1    3347
    # 0    3347

    X = df["abstract"]
    y = df["rna_related"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    pipeMNB = Pipeline(steps=[("tfidf", TfidfVectorizer()), ("clf", MultinomialNB())])
    pipeMNB.fit(X_train, y_train)
    predictMNB = pipeMNB.predict(X_test)

    pipeCNB = Pipeline(steps=[("tfidf", TfidfVectorizer()), ("clf", ComplementNB())])
    pipeCNB.fit(X_train, y_train)
    predictCNB = pipeCNB.predict(X_test)

    pipeSVC = Pipeline(steps=[("tfidf", TfidfVectorizer()), ("clf", LinearSVC())])
    pipeSVC.fit(X_train, y_train)
    predictSVC = pipeSVC.predict(X_test)

    pipeRF = Pipeline(steps=[("tfidf", TfidfVectorizer()), ("clf", RandomForestClassifier())])
    pipeRF.fit(X_train, y_train)
    predictRF = pipeRF.predict(X_test)

    print(f"MNB: {accuracy_score(y_test, predictMNB):.2f}")
    print(f"CNB: {accuracy_score(y_test, predictCNB):.2f}")
    print(f"SVC: {accuracy_score(y_test, predictSVC):.2f}")
    print(f"RF: {accuracy_score(y_test, predictRF):.2f}")
    # MNB: 0.94
    # CNB: 0.94
    # SVC: 0.99
    # RF: 0.96

    print(classification_report(y_test, predictSVC))
    #               precision    recall  f1-score   support
    #
    #            0       0.99      0.98      0.98       669
    #            1       0.98      0.99      0.99       670
    #
    #     accuracy                           0.99      1339
    #    macro avg       0.99      0.99      0.99      1339
    # weighted avg       0.99      0.99      0.99      1339

    joblib.dump(pipeSVC, "svc_pipeline.pkl")


if __name__ == "__main__":
    main()
