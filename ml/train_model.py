"""
MuleWatch - ML Risk Model Training

Trains and compares multiple machine-learning models for
account-level mule-account risk detection.

Models:
    1. Logistic Regression
    2. Decision Tree
    3. Random Forest
    4. Extra Trees
    5. Gradient Boosting
    6. HistGradientBoosting
    7. Stacking Classifier

Evaluation metrics:
    - Precision
    - Recall
    - F1-score
    - ROC-AUC
    - PR-AUC

The selected production model is saved for later integration
with the MuleWatch FastAPI backend.
"""

from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import (
    ExtraTreesClassifier,
    GradientBoostingClassifier,
    HistGradientBoostingClassifier,
    RandomForestClassifier,
    StackingClassifier,
)
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier


# ============================================================
# PATHS
# ============================================================

ML_DIR = Path(__file__).resolve().parent

DATA_FILE = (
    ML_DIR
    / "data"
    / "account_features.csv"
)

MODEL_DIR = ML_DIR / "models"

MODEL_DIR.mkdir(
    parents=True,
    exist_ok=True
)

BEST_MODEL_FILE = (
    MODEL_DIR
    / "mulewatch_risk_model.joblib"
)

COMPARISON_FILE = (
    MODEL_DIR
    / "model_comparison.csv"
)

FEATURE_IMPORTANCE_FILE = (
    MODEL_DIR
    / "feature_importance.csv"
)


# ============================================================
# CONFIGURATION
# ============================================================

RANDOM_STATE = 42

TEST_SIZE = 0.20

TARGET_COLUMN = "risk_label"

ID_COLUMN = "account_id"


# ============================================================
# LOAD FEATURE DATASET
# ============================================================

def load_feature_data() -> pd.DataFrame:
    """Load and validate the account-level feature dataset."""

    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Feature dataset not found: {DATA_FILE}"
        )

    df = pd.read_csv(DATA_FILE)

    required_columns = {
        ID_COLUMN,
        TARGET_COLUMN,
    }

    missing_columns = (
        required_columns - set(df.columns)
    )

    if missing_columns:
        raise ValueError(
            f"Missing required columns: "
            f"{sorted(missing_columns)}"
        )

    if df.empty:
        raise ValueError(
            "Feature dataset is empty."
        )

    if df[ID_COLUMN].duplicated().any():
        raise ValueError(
            "Duplicate account IDs detected."
        )

    if df[TARGET_COLUMN].isna().any():
        raise ValueError(
            "Missing target labels detected."
        )

    return df


# ============================================================
# PREPARE FEATURES AND TARGET
# ============================================================

def prepare_data(
    df: pd.DataFrame
):
    """
    Separate behavioral features from the target label.

    account_id is excluded because it is only an identifier.
    """

    feature_columns = [
        column
        for column in df.columns
        if column not in {
            ID_COLUMN,
            TARGET_COLUMN,
        }
    ]

    X = df[feature_columns].copy()

    y = (
        df[TARGET_COLUMN]
        .astype(int)
        .copy()
    )

    if X.empty:
        raise ValueError(
            "No ML features available."
        )

    if y.nunique() < 2:
        raise ValueError(
            "Target must contain at least two classes."
        )

    return X, y, feature_columns


# ============================================================
# ACCOUNT-LEVEL TRAIN / TEST SPLIT
# ============================================================

def split_data(
    X: pd.DataFrame,
    y: pd.Series
):
    """
    Split accounts into training and testing sets.

    The split happens at account level so the same account
    cannot appear in both sets.
    """

    (
        X_train,
        X_test,
        y_train,
        y_test,
    ) = train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=y,
    )

    return (
        X_train,
        X_test,
        y_train,
        y_test,
    )


# ============================================================
# MODEL 1 - LOGISTIC REGRESSION
# ============================================================

def build_logistic_regression_model():
    """
    Build an interpretable Logistic Regression baseline.
    """

    return Pipeline(
        steps=[
            (
                "scaler",
                StandardScaler()
            ),
            (
                "classifier",
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=2000,
                    random_state=RANDOM_STATE,
                ),
            ),
        ]
    )


# ============================================================
# MODEL 2 - DECISION TREE
# ============================================================

def build_decision_tree_model():
    """
    Build a single Decision Tree classifier.
    """

    return DecisionTreeClassifier(
        max_depth=8,
        min_samples_split=5,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=RANDOM_STATE,
    )


# ============================================================
# MODEL 3 - RANDOM FOREST
# ============================================================

def build_random_forest_model():
    """
    Build a Random Forest classifier.
    """

    return RandomForestClassifier(
        n_estimators=400,
        max_depth=10,
        min_samples_split=5,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )


# ============================================================
# MODEL 4 - EXTRA TREES
# ============================================================

def build_extra_trees_model():
    """
    Build an Extra Trees classifier.

    Extra Trees introduces additional randomness into the
    tree construction process.
    """

    return ExtraTreesClassifier(
        n_estimators=400,
        max_depth=10,
        min_samples_split=5,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )


# ============================================================
# MODEL 5 - GRADIENT BOOSTING
# ============================================================

def build_gradient_boosting_model():
    """
    Build a Gradient Boosting classifier.
    """

    return GradientBoostingClassifier(
        n_estimators=200,
        learning_rate=0.05,
        max_depth=3,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=RANDOM_STATE,
    )


# ============================================================
# MODEL 6 - HISTOGRAM GRADIENT BOOSTING
# ============================================================

def build_hist_gradient_boosting_model():
    """
    Build a histogram-based Gradient Boosting classifier.
    """

    return HistGradientBoostingClassifier(
        max_iter=200,
        learning_rate=0.05,
        max_leaf_nodes=15,
        min_samples_leaf=10,
        l2_regularization=0.1,
        random_state=RANDOM_STATE,
    )


# ============================================================
# MODEL 7 - STACKING CLASSIFIER
# ============================================================

def build_stacking_model():
    """
    Build a Stacking Classifier.

    Base learners:
        - Logistic Regression
        - Random Forest
        - Gradient Boosting

    Meta learner:
        - Logistic Regression

    The stacking model uses cross-validation internally to
    generate base-model predictions for the meta learner.
    """

    logistic_base = Pipeline(
        steps=[
            (
                "scaler",
                StandardScaler()
            ),
            (
                "classifier",
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=2000,
                    random_state=RANDOM_STATE,
                ),
            ),
        ]
    )

    random_forest_base = RandomForestClassifier(
        n_estimators=300,
        max_depth=10,
        min_samples_split=5,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )

    gradient_boosting_base = GradientBoostingClassifier(
        n_estimators=150,
        learning_rate=0.05,
        max_depth=3,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=RANDOM_STATE,
    )

    meta_classifier = LogisticRegression(
        class_weight="balanced",
        max_iter=2000,
        random_state=RANDOM_STATE,
    )

    return StackingClassifier(
        estimators=[
            (
                "logistic",
                logistic_base
            ),
            (
                "random_forest",
                random_forest_base
            ),
            (
                "gradient_boosting",
                gradient_boosting_base
            ),
        ],
        final_estimator=meta_classifier,
        cv=5,
        stack_method="predict_proba",
        n_jobs=-1,
        passthrough=False,
    )


# ============================================================
# MODEL TRAINING
# ============================================================

def train_models(
    X_train: pd.DataFrame,
    y_train: pd.Series
):
    """
    Build and train all seven models.
    """

    models = {
        "Logistic Regression":
            build_logistic_regression_model(),

        "Decision Tree":
            build_decision_tree_model(),

        "Random Forest":
            build_random_forest_model(),

        "Extra Trees":
            build_extra_trees_model(),

        "Gradient Boosting":
            build_gradient_boosting_model(),

        "HistGradientBoosting":
            build_hist_gradient_boosting_model(),

        "Stacking Classifier":
            build_stacking_model(),
    }

    trained_models = {}

    print("\n" + "=" * 60)
    print("MODEL TRAINING")
    print("=" * 60)

    for model_name, model in models.items():

        print(
            f"\nTraining {model_name}..."
        )

        model.fit(
            X_train,
            y_train
        )

        trained_models[model_name] = model

        print(
            f"{model_name} training completed."
        )

    return trained_models


# ============================================================
# MODEL EVALUATION
# ============================================================

def evaluate_model(
    model,
    model_name: str,
    X_test: pd.DataFrame,
    y_test: pd.Series
):
    """
    Evaluate a trained model.
    """

    predictions = model.predict(
        X_test
    )

    probabilities = model.predict_proba(
        X_test
    )[:, 1]

    precision = precision_score(
        y_test,
        predictions,
        zero_division=0
    )

    recall = recall_score(
        y_test,
        predictions,
        zero_division=0
    )

    f1 = f1_score(
        y_test,
        predictions,
        zero_division=0
    )

    roc_auc = roc_auc_score(
        y_test,
        probabilities
    )

    pr_auc = average_precision_score(
        y_test,
        probabilities
    )

    matrix = confusion_matrix(
        y_test,
        predictions
    )

    print("\n" + "=" * 60)
    print(
        f"{model_name.upper()} - EVALUATION"
    )
    print("=" * 60)

    print(
        f"\nPrecision : {precision:.4f}"
    )

    print(
        f"Recall    : {recall:.4f}"
    )

    print(
        f"F1-score  : {f1:.4f}"
    )

    print(
        f"ROC-AUC   : {roc_auc:.4f}"
    )

    print(
        f"PR-AUC    : {pr_auc:.4f}"
    )

    print("\nConfusion Matrix:")

    print(matrix)

    print("\nClassification Report:")

    print(
        classification_report(
            y_test,
            predictions,
            target_names=[
                "Normal",
                "Suspicious"
            ],
            zero_division=0
        )
    )

    return {
        "model": model,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "roc_auc": roc_auc,
        "pr_auc": pr_auc,
        "probabilities": probabilities,
        "predictions": predictions,
    }


# ============================================================
# MODEL COMPARISON
# ============================================================

def create_comparison_table(
    results: dict
) -> pd.DataFrame:
    """
    Create a comparison table for all models.
    """

    rows = []

    for model_name, result in results.items():

        rows.append({
            "Model": model_name,
            "Precision": result["precision"],
            "Recall": result["recall"],
            "F1": result["f1"],
            "ROC_AUC": result["roc_auc"],
            "PR_AUC": result["pr_auc"],
        })

    comparison = pd.DataFrame(
        rows
    )

    comparison = comparison.sort_values(
        by="F1",
        ascending=False
    ).reset_index(
        drop=True
    )

    return comparison


# ============================================================
# FEATURE IMPORTANCE
# ============================================================

def save_feature_importance(
    model,
    feature_columns
):
    """
    Save feature importance for tree-based production models.

    This is useful for explaining which behavioral features
    contribute most strongly to the model.
    """

    if not hasattr(
        model,
        "feature_importances_"
    ):
        print(
            "\nSelected model does not expose "
            "direct feature importance."
        )
        return

    importance = pd.DataFrame({
        "feature": feature_columns,
        "importance": model.feature_importances_,
    })

    importance = importance.sort_values(
        by="importance",
        ascending=False
    )

    importance.to_csv(
        FEATURE_IMPORTANCE_FILE,
        index=False
    )

    print(
        "\nFeature importance saved to:"
    )

    print(
        FEATURE_IMPORTANCE_FILE
    )

    print("\nTop 10 features:")

    print(
        importance.head(10).to_string(
            index=False
        )
    )


# ============================================================
# SAVE BEST MODEL
# ============================================================

def save_best_model(
    best_model,
    best_model_name: str
):
    """
    Save the selected production model together with metadata.
    """

    model_package = {
        "model": best_model,
        "model_name": best_model_name,
        "random_state": RANDOM_STATE,
        "target_column": TARGET_COLUMN,
    }

    joblib.dump(
        model_package,
        BEST_MODEL_FILE
    )

    print(
        "\nProduction model saved to:"
    )

    print(
        BEST_MODEL_FILE
    )


# ============================================================
# MAIN PIPELINE
# ============================================================

def main():

    print("=" * 60)
    print("MuleWatch ML Risk Model Training")
    print("=" * 60)

    # --------------------------------------------------------
    # Load data
    # --------------------------------------------------------

    print(
        "\nLoading account-level features..."
    )

    df = load_feature_data()

    print(
        f"Loaded {len(df):,} accounts."
    )

    # --------------------------------------------------------
    # Prepare X and y
    # --------------------------------------------------------

    X, y, feature_columns = prepare_data(
        df
    )

    print(
        f"Using {len(feature_columns)} behavioral features."
    )

    print(
        f"Normal accounts     : {(y == 0).sum()}"
    )

    print(
        f"Suspicious accounts : {(y == 1).sum()}"
    )

    # --------------------------------------------------------
    # Train/test split
    # --------------------------------------------------------

    (
        X_train,
        X_test,
        y_train,
        y_test,
    ) = split_data(
        X,
        y
    )

    print(
        f"\nTraining accounts : {len(X_train):,}"
    )

    print(
        f"Testing accounts  : {len(X_test):,}"
    )

    # --------------------------------------------------------
    # Train all models
    # --------------------------------------------------------

    trained_models = train_models(
        X_train,
        y_train
    )

    # --------------------------------------------------------
    # Evaluate all models
    # --------------------------------------------------------

    results = {}

    for model_name, model in trained_models.items():

        results[model_name] = evaluate_model(
            model,
            model_name,
            X_test,
            y_test
        )

    # --------------------------------------------------------
    # Create comparison
    # --------------------------------------------------------

    comparison = create_comparison_table(
        results
    )

    print("\n" + "=" * 60)
    print("MODEL COMPARISON")
    print("=" * 60)

    print(
        comparison.to_string(
            index=False,
            float_format=lambda value: f"{value:.4f}"
        )
    )

    # --------------------------------------------------------
    # Save comparison
    # --------------------------------------------------------

    comparison.to_csv(
        COMPARISON_FILE,
        index=False
    )

    print(
        "\nModel comparison saved to:"
    )

    print(
        COMPARISON_FILE
    )

    # --------------------------------------------------------
    # Select production model
    # --------------------------------------------------------

    best_model_name = (
        comparison.iloc[0]["Model"]
    )

    best_model = trained_models[
        best_model_name
    ]

    best_f1 = results[
        best_model_name
    ]["f1"]

    print(
        "\n" + "=" * 60
    )

    print(
        "SELECTED PRODUCTION MODEL"
    )

    print(
        "=" * 60
    )

    print(
        f"\nModel : {best_model_name}"
    )

    print(
        f"F1    : {best_f1:.4f}"
    )

    # --------------------------------------------------------
    # Save model
    # --------------------------------------------------------

    save_best_model(
        best_model,
        best_model_name
    )

    # --------------------------------------------------------
    # Feature importance
    # --------------------------------------------------------

    save_feature_importance(
        best_model,
        feature_columns
    )

    # --------------------------------------------------------
    # Final summary
    # --------------------------------------------------------

    print(
        "\n" + "=" * 60
    )

    print(
        "ML TRAINING PIPELINE COMPLETED"
    )

    print(
        "=" * 60
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()