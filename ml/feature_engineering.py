"""
MuleWatch - Account-Level Feature Engineering

Transforms raw transaction data into account-level behavioral
features for mule-account risk detection.

Important:
    Synthetic scenario-construction fields such as
    behavior_profile, rapid_transfer, and new_beneficiary
    are NOT used as model features because they would cause
    target/scenario leakage.
"""

from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# PATHS
# ============================================================

ML_DIR = Path(__file__).resolve().parent

INPUT_FILE = ML_DIR / "data" / "synthetic_transactions.csv"

OUTPUT_DIR = ML_DIR / "data"
OUTPUT_FILE = OUTPUT_DIR / "account_features.csv"


# ============================================================
# CONFIGURATION
# ============================================================

# A transaction gap of <= 10 minutes is considered rapid
RAPID_GAP_MINUTES = 10

# A short-term money movement window
SHORT_WINDOW_MINUTES = 30


# ============================================================
# LOAD DATA
# ============================================================

def load_transaction_data() -> pd.DataFrame:
    """Load and validate the raw transaction dataset."""

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input dataset not found: {INPUT_FILE}"
        )

    df = pd.read_csv(INPUT_FILE)

    required_columns = {
        "transaction_id",
        "sender_account_id",
        "receiver_account_id",
        "amount",
        "txn_time",
        "risk_label",
    }

    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    df["txn_time"] = pd.to_datetime(df["txn_time"])

    df["amount"] = pd.to_numeric(
        df["amount"],
        errors="coerce"
    )

    if df["amount"].isna().any():
        raise ValueError("Invalid transaction amounts detected.")

    if (df["amount"] <= 0).any():
        raise ValueError("Transaction amounts must be positive.")

    return df


# ============================================================
# BASIC ACCOUNT FEATURES
# ============================================================

def create_basic_features(
    transactions: pd.DataFrame,
    account_ids: pd.Series
) -> pd.DataFrame:
    """
    Create basic transaction and monetary features
    for every account.
    """

    outgoing = (
        transactions
        .groupby("sender_account_id")
        .agg(
            outgoing_transaction_count=(
                "transaction_id",
                "count"
            ),
            outgoing_total_amount=(
                "amount",
                "sum"
            ),
            outgoing_average_amount=(
                "amount",
                "mean"
            ),
            outgoing_max_amount=(
                "amount",
                "max"
            ),
            outgoing_min_amount=(
                "amount",
                "min"
            ),
            outgoing_std_amount=(
                "amount",
                "std"
            ),
            unique_receivers=(
                "receiver_account_id",
                "nunique"
            ),
        )
    )

    incoming = (
        transactions
        .groupby("receiver_account_id")
        .agg(
            incoming_transaction_count=(
                "transaction_id",
                "count"
            ),
            incoming_total_amount=(
                "amount",
                "sum"
            ),
            incoming_average_amount=(
                "amount",
                "mean"
            ),
            incoming_max_amount=(
                "amount",
                "max"
            ),
            unique_senders=(
                "sender_account_id",
                "nunique"
            ),
        )
    )

    features = pd.DataFrame({
        "account_id": account_ids
    })

    features = features.merge(
        outgoing,
        left_on="account_id",
        right_index=True,
        how="left"
    )

    features = features.merge(
        incoming,
        left_on="account_id",
        right_index=True,
        how="left"
    )

    numeric_columns = [
        column
        for column in features.columns
        if column != "account_id"
    ]

    features[numeric_columns] = (
        features[numeric_columns]
        .fillna(0)
    )

    # Coefficient of variation:
    # measures how variable transaction amounts are.
    features["amount_variability"] = np.where(
        features["outgoing_average_amount"] > 0,
        features["outgoing_std_amount"]
        / features["outgoing_average_amount"],
        0
    )

    # Incoming/outgoing relationship.
    features["incoming_outgoing_amount_ratio"] = np.where(
        features["outgoing_total_amount"] > 0,
        features["incoming_total_amount"]
        / features["outgoing_total_amount"],
        0
    )

    # Difference between incoming and outgoing money.
    features["net_money_flow"] = (
        features["incoming_total_amount"]
        - features["outgoing_total_amount"]
    )

    # Total activity.
    features["total_transaction_count"] = (
        features["incoming_transaction_count"]
        + features["outgoing_transaction_count"]
    )

    features["total_money_movement"] = (
        features["incoming_total_amount"]
        + features["outgoing_total_amount"]
    )

    return features


# ============================================================
# TEMPORAL FEATURES
# ============================================================

def create_temporal_features(
    transactions: pd.DataFrame,
    account_ids: pd.Series
) -> pd.DataFrame:
    """
    Derive transaction velocity and timing behavior.

    These features are calculated from timestamps rather than
    using the synthetic rapid_transfer flag.
    """

    outgoing = (
        transactions[
            [
                "sender_account_id",
                "txn_time",
                "amount",
            ]
        ]
        .sort_values(
            ["sender_account_id", "txn_time"]
        )
        .copy()
    )

    outgoing["previous_txn_time"] = (
        outgoing
        .groupby("sender_account_id")["txn_time"]
        .shift(1)
    )

    outgoing["gap_minutes"] = (
        outgoing["txn_time"]
        - outgoing["previous_txn_time"]
    ).dt.total_seconds() / 60

    # Count transactions occurring very close together.
    outgoing["rapid_gap"] = (
        outgoing["gap_minutes"]
        <= RAPID_GAP_MINUTES
    ).astype(int)

    rapid_features = (
        outgoing
        .groupby("sender_account_id")
        .agg(
            rapid_transaction_count=(
                "rapid_gap",
                "sum"
            ),
            minimum_transaction_gap_minutes=(
                "gap_minutes",
                "min"
            ),
        )
    )

    # Active days.
    active_days = (
        transactions
        .groupby("sender_account_id")["txn_time"]
        .agg(
            first_transaction_time="min",
            last_transaction_time="max"
        )
    )

    active_days["active_period_days"] = (
        (
            active_days["last_transaction_time"]
            - active_days["first_transaction_time"]
        )
        .dt.total_seconds()
        / 86400
    )

    # Number of distinct calendar days with activity.
    distinct_days = (
        transactions
        .assign(
            transaction_date=transactions["txn_time"].dt.date
        )
        .groupby("sender_account_id")["transaction_date"]
        .nunique()
        .rename("active_transaction_days")
    )

    temporal = pd.DataFrame({
        "account_id": account_ids
    })

    temporal = temporal.merge(
        rapid_features,
        left_on="account_id",
        right_index=True,
        how="left"
    )

    temporal = temporal.merge(
        active_days[["active_period_days"]],
        left_on="account_id",
        right_index=True,
        how="left"
    )

    temporal = temporal.merge(
        distinct_days,
        left_on="account_id",
        right_index=True,
        how="left"
    )

    temporal = temporal.fillna(0)

    # Rapid transaction ratio.
    outgoing_counts = (
        transactions
        .groupby("sender_account_id")
        .size()
        .rename("outgoing_count")
    )

    temporal = temporal.merge(
        outgoing_counts,
        left_on="account_id",
        right_index=True,
        how="left"
    )

    temporal["rapid_transaction_ratio"] = np.where(
        temporal["outgoing_count"] > 0,
        temporal["rapid_transaction_count"]
        / temporal["outgoing_count"],
        0
    )

    # Transaction frequency per active day.
    temporal["transactions_per_active_day"] = np.where(
        temporal["active_transaction_days"] > 0,
        temporal["outgoing_count"]
        / temporal["active_transaction_days"],
        0
    )

    temporal.drop(
        columns=["outgoing_count"],
        inplace=True
    )

    return temporal


# ============================================================
# AMOUNT DISTRIBUTION FEATURES
# ============================================================

def create_amount_features(
    transactions: pd.DataFrame,
    account_ids: pd.Series
) -> pd.DataFrame:
    """
    Capture unusual transaction amount patterns.
    """

    outgoing = transactions.copy()

    amount_features = (
        outgoing
        .groupby("sender_account_id")["amount"]
        .agg(
            median_outgoing_amount="median",
            amount_75th_percentile=lambda x: x.quantile(0.75),
            amount_95th_percentile=lambda x: x.quantile(0.95),
        )
    )

    features = pd.DataFrame({
        "account_id": account_ids
    })

    features = features.merge(
        amount_features,
        left_on="account_id",
        right_index=True,
        how="left"
    )

    features = features.fillna(0)

    return features


# ============================================================
# BEHAVIORAL DEVIATION FEATURES
# ============================================================

def create_behavioral_deviation_features(
    transactions: pd.DataFrame,
    account_ids: pd.Series
) -> pd.DataFrame:
    """
    Compare each account's earlier behavior with its later behavior.

    Instead of using a global calendar window, each account's own
    transaction history is split into two periods. This ensures
    accounts with different activity periods still receive meaningful
    behavioral-deviation features.
    """

    data = transactions.copy()

    data = data.sort_values(
        ["sender_account_id", "txn_time"]
    )

    # Assign each transaction to an account-specific time period.
    data["account_transaction_rank"] = (
        data.groupby("sender_account_id")
        .cumcount()
    )

    data["account_transaction_count"] = (
        data.groupby("sender_account_id")["transaction_id"]
        .transform("count")
    )

    # First 70% = historical behavior
    # Last 30% = recent behavior
    data["is_recent"] = (
        data["account_transaction_rank"]
        >= data["account_transaction_count"] * 0.70
    )

    historical = data[
        ~data["is_recent"]
    ]

    recent = data[
        data["is_recent"]
    ]

    historical_stats = (
        historical
        .groupby("sender_account_id")
        .agg(
            historical_transaction_count=(
                "transaction_id",
                "count"
            ),
            historical_average_amount=(
                "amount",
                "mean"
            ),
        )
    )

    recent_stats = (
        recent
        .groupby("sender_account_id")
        .agg(
            recent_transaction_count=(
                "transaction_id",
                "count"
            ),
            recent_average_amount=(
                "amount",
                "mean"
            ),
        )
    )

    features = pd.DataFrame({
        "account_id": account_ids
    })

    features = features.merge(
        historical_stats,
        left_on="account_id",
        right_index=True,
        how="left"
    )

    features = features.merge(
        recent_stats,
        left_on="account_id",
        right_index=True,
        how="left"
    )

    numeric_columns = [
        column
        for column in features.columns
        if column != "account_id"
    ]

    features[numeric_columns] = (
        features[numeric_columns]
        .fillna(0)
    )

    # Percentage change in average transaction amount.
    features["amount_deviation_ratio"] = np.where(
        features["historical_average_amount"] > 0,
        (
            features["recent_average_amount"]
            - features["historical_average_amount"]
        )
        / features["historical_average_amount"],
        0
    )

    # Change in transaction frequency.
    features["transaction_frequency_change"] = (
        features["recent_transaction_count"]
        - features["historical_transaction_count"]
    )

    return features

# ============================================================
# NETWORK FEATURES
# ============================================================

def create_network_features(
    transactions: pd.DataFrame,
    account_ids: pd.Series
) -> pd.DataFrame:
    """
    Capture account connectivity.

    Mule accounts can participate in money-movement networks,
    so the number and diversity of counterparties are useful
    behavioral signals.
    """

    outgoing_connections = (
        transactions
        .groupby("sender_account_id")["receiver_account_id"]
        .nunique()
        .rename("unique_outgoing_accounts")
    )

    incoming_connections = (
        transactions
        .groupby("receiver_account_id")["sender_account_id"]
        .nunique()
        .rename("unique_incoming_accounts")
    )

    features = pd.DataFrame({
        "account_id": account_ids
    })

    features = features.merge(
        outgoing_connections,
        left_on="account_id",
        right_index=True,
        how="left"
    )

    features = features.merge(
        incoming_connections,
        left_on="account_id",
        right_index=True,
        how="left"
    )

    features = features.fillna(0)

    # Connectivity ratio.
    features["incoming_outgoing_connection_ratio"] = np.where(
        features["unique_outgoing_accounts"] > 0,
        features["unique_incoming_accounts"]
        / features["unique_outgoing_accounts"],
        0
    )

    return features


# ============================================================
# LABEL CREATION
# ============================================================

def create_account_labels(
    transactions: pd.DataFrame,
    account_ids: pd.Series
) -> pd.DataFrame:
    """
    Convert transaction-level labels into account-level labels.

    An account is considered suspicious if at least one of its
    transactions carries the generated suspicious label.
    """

    account_labels = (
        transactions
        .groupby("sender_account_id")["risk_label"]
        .max()
        .rename("risk_label")
    )

    labels = pd.DataFrame({
        "account_id": account_ids
    })

    labels = labels.merge(
        account_labels,
        left_on="account_id",
        right_index=True,
        how="left"
    )

    labels["risk_label"] = (
        labels["risk_label"]
        .fillna(0)
        .astype(int)
    )

    return labels


# ============================================================
# BUILD COMPLETE FEATURE DATASET
# ============================================================

def build_feature_dataset(
    transactions: pd.DataFrame
) -> pd.DataFrame:
    """
    Build the complete account-level ML dataset.
    """

    # Accounts appearing as either senders or receivers.
    account_ids = pd.Series(
        pd.unique(
            pd.concat(
                [
                    transactions["sender_account_id"],
                    transactions["receiver_account_id"],
                ]
            )
        ),
        name="account_id"
    ).sort_values().reset_index(drop=True)

    basic = create_basic_features(
        transactions,
        account_ids
    )

    temporal = create_temporal_features(
        transactions,
        account_ids
    )

    amount = create_amount_features(
        transactions,
        account_ids
    )

    deviation = create_behavioral_deviation_features(
        transactions,
        account_ids
    )

    network = create_network_features(
        transactions,
        account_ids
    )

    labels = create_account_labels(
        transactions,
        account_ids
    )

    # Merge all feature groups.
    features = basic

    for feature_group in [
        temporal,
        amount,
        deviation,
        network,
        labels,
    ]:
        features = features.merge(
            feature_group,
            on="account_id",
            how="left"
        )

    # Replace numerical NaN values.
    numeric_columns = features.select_dtypes(
        include=[np.number]
    ).columns

    features[numeric_columns] = (
        features[numeric_columns]
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0)
    )

    # Sort for reproducibility.
    features = features.sort_values(
        "account_id"
    ).reset_index(drop=True)

    return features


# ============================================================
# VALIDATION
# ============================================================

def validate_features(
    features: pd.DataFrame
) -> None:
    """Validate the final account-level feature dataset."""

    if features.empty:
        raise ValueError(
            "Feature dataset is empty."
        )

    if features["account_id"].duplicated().any():
        raise ValueError(
            "Duplicate account IDs detected."
        )

    if features.isna().any().any():
        raise ValueError(
            "Missing values remain in feature dataset."
        )

    if not set(features["risk_label"].unique()).issubset({0, 1}):
        raise ValueError(
            "risk_label must contain only 0 and 1."
        )

    feature_columns = [
        column
        for column in features.columns
        if column not in {
            "account_id",
            "risk_label",
        }
    ]

    if len(feature_columns) < 10:
        raise ValueError(
            "Too few behavioral features were generated."
        )

    print("Feature validation passed.")


# ============================================================
# MAIN
# ============================================================

def main() -> None:

    print("=" * 60)
    print("MuleWatch Account-Level Feature Engineering")
    print("=" * 60)

    print("\nLoading transaction data...")

    transactions = load_transaction_data()

    print(
        f"Loaded {len(transactions):,} transactions."
    )

    print("\nBuilding behavioral features...")

    features = build_feature_dataset(
        transactions
    )

    validate_features(features)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    features.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print(
        f"\nGenerated {len(features):,} account-level records."
    )

    print(
        f"Generated {len(features.columns) - 2} ML features."
    )

    print(
        f"\nDataset saved to:\n{OUTPUT_FILE}"
    )

    print("\nFeature columns:")

    for column in features.columns:
        print(f"  - {column}")

    print("\nRisk-label distribution:")

    print(
        features["risk_label"]
        .value_counts()
        .sort_index()
    )

    print("\nSample account-level features:")

    print(
        features.head(10).to_string(
            index=False
        )
    )

    print("\nFeature engineering completed successfully.")


if __name__ == "__main__":
    main()