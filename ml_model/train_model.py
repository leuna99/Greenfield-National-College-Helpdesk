import pandas as pd
import joblib

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report


# Load training dataset
data = pd.read_csv("training_data.csv")

# Remove empty rows
data = data.dropna(subset=["question", "intent"])

# Clean text
data["question"] = data["question"].astype(str).str.strip()
data["intent"] = data["intent"].astype(str).str.strip()

# Input questions and target intents
X = data["question"]
y = data["intent"]


# Split dataset
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)


# Create improved ML pipeline
#
# Word TF-IDF:
# Understands complete words and phrases.
#
# Character TF-IDF:
# Helps recognize spelling variations and typing mistakes.
#
model = Pipeline([
    (
        "features",
        FeatureUnion([
            (
                "word_features",
                TfidfVectorizer(
                    lowercase=True,
                    ngram_range=(1, 2),
                    sublinear_tf=True
                )
            ),
            (
                "character_features",
                TfidfVectorizer(
                    lowercase=True,
                    analyzer="char_wb",
                    ngram_range=(2, 5),
                    sublinear_tf=True
                )
            )
        ])
    ),
    (
        "classifier",
        LogisticRegression(
            max_iter=2000,
            C=5.0
        )
    )
])


# Train the model
print("Training improved ML model...")
model.fit(X_train, y_train)


# Test the model
y_pred = model.predict(X_test)

accuracy = accuracy_score(y_test, y_pred)

print("\n===================================")
print("IMPROVED MODEL TRAINING COMPLETED")
print("===================================")

print(f"\nAccuracy: {accuracy * 100:.2f}%")

print("\nClassification Report:")
print(
    classification_report(
        y_test,
        y_pred,
        zero_division=0
    )
)


# Save model
joblib.dump(model, "chatbot_model.pkl")

print("\nTrained model saved as:")
print("chatbot_model.pkl")