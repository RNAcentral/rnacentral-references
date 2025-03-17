import joblib
import pandas as pd

from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, recall_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import ComplementNB, MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC


def main():
    """
    Testing four text classifiers: LinearSVC, ComplementNB, MultinomialNB, and RandomForestClassifier.
    The following TfidfVectorizer parameters were tested:
    - stop_words="english"
    - min_df=5
    """
    df = pd.read_csv("data.csv")
    print(df["rna_related"].value_counts(), "\n")
    # rna_related
    # 1    3363
    # 0    3331

    X = df["abstract"]
    y = df["rna_related"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    classifiers = {
        "MultinomialNB": Pipeline(steps=[("tfidf", TfidfVectorizer()), ("clf", MultinomialNB())]),
        "ComplementNB": Pipeline(steps=[("tfidf", TfidfVectorizer()), ("clf", ComplementNB())]),
        "LinearSVC": Pipeline(steps=[("tfidf", TfidfVectorizer()), ("clf", CalibratedClassifierCV(LinearSVC()))]),
        "RandomForest": Pipeline(steps=[("tfidf", TfidfVectorizer()), ("clf", RandomForestClassifier())])
    }

    best_accuracy = 0
    best_classifier_name = None
    best_pipeline = None

    for name, pipeline in classifiers.items():
        pipeline.fit(X_train, y_train)
        y_pred = pipeline.predict(X_test)

        accuracy = accuracy_score(y_test, y_pred)
        sensitivity = recall_score(y_test, y_pred, pos_label=1)
        specificity = recall_score(y_test, y_pred, pos_label=0)
        print(
            f"{name} - Accuracy: {accuracy:.2f}, "
            f"Sensitivity: {sensitivity:.2f}, "
            f"Specificity: {specificity:.2f}"
        )
        # MultinomialNB - Accuracy: 0.93, Sensitivity: 0.99, Specificity: 0.88
        # ComplementNB - Accuracy: 0.93, Sensitivity: 0.99, Specificity: 0.88
        # LinearSVC - Accuracy: 0.98, Sensitivity: 0.98, Specificity: 0.98
        # RandomForest - Accuracy: 0.96, Sensitivity: 0.98, Specificity: 0.93

        if accuracy > best_accuracy:
            best_accuracy = accuracy
            best_classifier_name = name
            best_pipeline = pipeline

    if best_pipeline is not None:
        # save the best classifier pipeline
        joblib.dump(best_pipeline, f"{best_classifier_name}_pipeline.pkl")
        print(
            f"\nSaved the best classifier ({best_classifier_name}) "
            f"with accuracy {best_accuracy:.2f} "
            f"to '{best_classifier_name}_pipeline.pkl'"
        )
        # Saved the best classifier (LinearSVC) with accuracy 0.98 to 'LinearSVC_pipeline.pkl'

    # display classification report for the best classifier pipeline
    print(f"\nClassification Report for {best_classifier_name}:")
    print(classification_report(y_test, classifiers[best_classifier_name].predict(X_test)))

    # Classification Report for LinearSVC:
    #               precision    recall  f1-score   support
    #
    #            0       0.98      0.98      0.98       665
    #            1       0.98      0.98      0.98       674
    #
    #     accuracy                           0.98      1339
    #    macro avg       0.98      0.98      0.98      1339
    # weighted avg       0.98      0.98      0.98      1339

if __name__ == "__main__":
    main()
