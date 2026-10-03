"""
MuleWatch - Risk Inference Engine

Loads the trained MuleWatch ML model and converts account-level
behavioral features into:

    1. Suspicious probability
    2. 0-100 risk score
    3. Risk level
    4. Human-readable investigation reasons
"""

from pathlib import Path

import joblib
import pandas as pd


# ============================================================
# PATHS
# ============================================================

ML_DIR = Path(__file__).resolve().parent

MODEL_FILE = (
    ML_DIR
    / "models"
    / "mulewatch_risk_model.joblib"
)

FEATURE_FILE = (
    ML_DIR
    / "data"
    / "account_features.csv"
)

# ============================================================
# LOAD TRAINED MODEL
# ============================================================

def load_model():
    """
    Load the saved MuleWatch production model.
    """

    if not MODEL_FILE.exists():
        raise FileNotFoundError(
            f"Trained model not found: {MODEL_FILE}"
        )

    model_package = joblib.load(
        MODEL_FILE
    )

    if not isinstance(
        model_package,
        dict
    ):
        raise ValueError(
            "Invalid model package."
        )

    if "model" not in model_package:
        raise ValueError(
            "Model package does not contain a trained model."
        )

    return model_package

# ============================================================
# LOAD ACCOUNT FEATURES
# ============================================================

def load_account_features():
    """
    Load account-level behavioral features generated
    by the feature engineering pipeline.
    """

    if not FEATURE_FILE.exists():
        raise FileNotFoundError(
            f"Feature file not found: {FEATURE_FILE}"
        )

    df = pd.read_csv(FEATURE_FILE)

    if df.empty:
        raise ValueError(
            "Account feature dataset is empty."
        )

    if "account_id" not in df.columns:
        raise ValueError(
            "Feature dataset must contain account_id."
        )

    return df
# ============================================================
# PREPARE MODEL FEATURES
# ============================================================

def prepare_features(df):
    """
    Prepare the account feature dataframe for ML inference.

    Removes identifier/label columns and keeps only the
    behavioral features used by the trained model.
    """

    excluded_columns = {
        "account_id",
        "risk_label"
    }

    feature_columns = [
        column
        for column in df.columns
        if column not in excluded_columns
    ]

    if not feature_columns:
        raise ValueError(
            "No ML feature columns found."
        )

    X = df[feature_columns].copy()

    return X, feature_columns

# ============================================================
# PREDICT SUSPICIOUS PROBABILITY
# ============================================================

def predict_suspicious_probability(model, X):
    """
    Predict the probability that an account exhibits
    suspicious mule-account behavior.
    """

    if not hasattr(model, "predict_proba"):
        raise ValueError(
            "The trained model does not support probability prediction."
        )

    probabilities = model.predict_proba(X)

    if probabilities.shape[1] != 2:
        raise ValueError(
            "Expected a binary classification model."
        )

    suspicious_probability = probabilities[:, 1]

    return suspicious_probability
# ============================================================
# CONVERT PROBABILITY TO RISK SCORE
# ============================================================

def calculate_risk_score(suspicious_probability):
    """
    Convert suspicious probability (0-1) into a
    MuleWatch risk score (0-100).
    """

    risk_score = suspicious_probability * 100

    return round(float(risk_score), 2)

# ============================================================
# DETERMINE RISK LEVEL
# ============================================================

def determine_risk_level(risk_score):
    """
    Convert a 0-100 risk score into a MuleWatch risk level.
    """

    if risk_score >= 85:
        return "CRITICAL"

    if risk_score >= 70:
        return "HIGH"

    if risk_score >= 40:
        return "MEDIUM"

    return "LOW"

# ============================================================
# GENERATE INVESTIGATION REASONS
# ============================================================

def generate_reasons(account_features):
    """
    Generate human-readable reasons based on the account's
    behavioral characteristics.

    These reasons are investigation indicators, not proof
    of fraudulent activity.
    """

    reasons = []

    if account_features["outgoing_total_amount"] >= 100000:
        reasons.append(
            "High total outgoing transaction value"
        )

    if account_features["outgoing_max_amount"] >= 75000:
        reasons.append(
            "Large-value outgoing transaction detected"
        )

    if account_features["rapid_transaction_ratio"] >= 0.20:
        reasons.append(
            "High proportion of rapid transactions"
        )

    if account_features["minimum_transaction_gap_minutes"] <= 10:
        reasons.append(
            "Very short time gap between transactions"
        )

    if account_features["transaction_frequency_change"] >= 0.50:
        reasons.append(
            "Recent transaction frequency increased significantly"
        )

    if account_features["amount_deviation_ratio"] >= 0.50:
        reasons.append(
            "Recent transaction amounts deviate significantly from historical behavior"
        )

    if account_features["unique_receivers"] >= 10:
        reasons.append(
            "Large number of outgoing counterparties"
        )

    if account_features["incoming_outgoing_connection_ratio"] >= 0.70:
        reasons.append(
            "Strong incoming-to-outgoing account connectivity"
        )

    if not reasons:
        reasons.append(
            "No major behavioral risk indicators detected"
        )

    return reasons
# ============================================================
# PREDICT RISK FOR A SINGLE ACCOUNT
# ============================================================

def predict_account_risk(account_id):
    """
    Generate a complete MuleWatch risk assessment
    for a single account.
    """

    model_package = load_model()
    model = model_package["model"]

    feature_df = load_account_features()

    account_rows = feature_df[
        feature_df["account_id"] == account_id
    ]

    if account_rows.empty:
        raise ValueError(
            f"Account {account_id} not found in feature dataset."
        )

    X, feature_columns = prepare_features(
        account_rows
    )

    suspicious_probability = predict_suspicious_probability(
        model,
        X
    )[0]

    risk_score = calculate_risk_score(
        suspicious_probability
    )

    risk_level = determine_risk_level(
        risk_score
    )

    account_features = account_rows.iloc[0]

    reasons = generate_reasons(
        account_features
    )

    return {
        "account_id": int(account_id),
        "suspicious_probability": round(
            float(suspicious_probability),
            4
        ),
        "risk_score": risk_score,
        "risk_level": risk_level,
        "reasons": reasons,
        "model_version": model_package.get(
            "model_version",
            "1.0"
        )
    }

# ============================================================
# LOCAL TEST
# ============================================================

if __name__ == "__main__":
    test_account_id = 5

    result = predict_account_risk(
        test_account_id
    )

    print("\n" + "=" * 60)
    print("MULEWATCH RISK ASSESSMENT")
    print("=" * 60)

    print(f"Account ID              : {result['account_id']}")
    print(
        f"Suspicious Probability  : "
        f"{result['suspicious_probability']:.2%}"
    )
    print(
        f"Risk Score              : "
        f"{result['risk_score']:.2f}/100"
    )
    print(
        f"Risk Level              : "
        f"{result['risk_level']}"
    )
    print(
        f"Model Version           : "
        f"{result['model_version']}"
    )

    print("\nInvestigation Indicators:")

    for index, reason in enumerate(
        result["reasons"],
        start=1
    ):
        print(f"{index}. {reason}")

    print("=" * 60)