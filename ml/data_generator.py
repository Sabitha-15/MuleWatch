"""
MuleWatch - Synthetic Transaction Data Generator

Generates reproducible transaction behavior patterns for
training and evaluating the MuleWatch risk-scoring model.
"""

from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

RANDOM_SEED = 42

NUM_ACCOUNTS = 1000
DAYS_OF_HISTORY = 90

OUTPUT_DIR = Path(__file__).resolve().parent / "data"
OUTPUT_FILE = OUTPUT_DIR / "synthetic_transactions.csv"


# Reproducible random-number generator.
RNG = np.random.default_rng(RANDOM_SEED)

# ============================================================
# BEHAVIORAL PROFILES
# ============================================================

BEHAVIOR_PROFILES = {
    "normal": {
        "transaction_rate": 0.08,
        "amount_mean": 3000,
        "amount_std": 1500,
        "rapid_transfer_probability": 0.01,
        "new_beneficiary_probability": 0.05,
    },

    "high_value": {
        "transaction_rate": 0.05,
        "amount_mean": 50000,
        "amount_std": 15000,
        "rapid_transfer_probability": 0.03,
        "new_beneficiary_probability": 0.08,
    },

    "rapid_movement": {
        "transaction_rate": 0.12,
        "amount_mean": 35000,
        "amount_std": 12000,
        "rapid_transfer_probability": 0.45,
        "new_beneficiary_probability": 0.15,
    },

    "transaction_burst": {
        "transaction_rate": 0.30,
        "amount_mean": 12000,
        "amount_std": 6000,
        "rapid_transfer_probability": 0.30,
        "new_beneficiary_probability": 0.20,
    },

    "beneficiary_anomaly": {
        "transaction_rate": 0.10,
        "amount_mean": 18000,
        "amount_std": 8000,
        "rapid_transfer_probability": 0.15,
        "new_beneficiary_probability": 0.55,
    },

    "behavioral_deviation": {
        "transaction_rate": 0.10,
        "amount_mean": 25000,
        "amount_std": 18000,
        "rapid_transfer_probability": 0.20,
        "new_beneficiary_probability": 0.30,
    },
}


# Probability of assigning each behavioral profile
PROFILE_PROBABILITIES = {
    "normal": 0.55,
    "high_value": 0.10,
    "rapid_movement": 0.10,
    "transaction_burst": 0.10,
    "beneficiary_anomaly": 0.075,
    "behavioral_deviation": 0.075,
}

# ============================================================
# ACCOUNT POPULATION
# ============================================================

def generate_accounts() -> pd.DataFrame:
    """
    Create the synthetic account population and assign each
    account a behavioral profile.
    """

    profile_names = list(PROFILE_PROBABILITIES.keys())
    profile_weights = list(PROFILE_PROBABILITIES.values())

    profiles = RNG.choice(
        profile_names,
        size=NUM_ACCOUNTS,
        p=profile_weights,
    )

    accounts = pd.DataFrame(
        {
            "account_id": np.arange(1, NUM_ACCOUNTS + 1),
            "behavior_profile": profiles,
        }
    )

    return accounts

# ============================================================
# TRANSACTION GENERATION
# ============================================================

def generate_transactions(accounts: pd.DataFrame) -> pd.DataFrame:
    """
    Generate synthetic transaction history based on each
    account's assigned behavioral profile.
    """

    transactions = []

    start_date = pd.Timestamp("2026-01-01")

    transaction_id = 1

    for account in accounts.itertuples(index=False):

        profile_name = account.behavior_profile
        profile = BEHAVIOR_PROFILES[profile_name]

        # Generate a baseline number of transactions
        # according to the account's transaction rate.
        expected_transactions = int(
            profile["transaction_rate"] * DAYS_OF_HISTORY
        )

        transaction_count = max(
            1,
            RNG.poisson(expected_transactions)
        )

        for _ in range(transaction_count):

            # Random transaction date within the
            # historical period.
            random_day = RNG.integers(
                0,
                DAYS_OF_HISTORY
            )

            transaction_date = (
                start_date
                + pd.Timedelta(days=int(random_day))
            )

            # Random time during the day.
            seconds_in_day = 24 * 60 * 60

            random_seconds = RNG.integers(
                0,
                seconds_in_day
            )

            transaction_time = (
                transaction_date
                + pd.Timedelta(
                    seconds=int(random_seconds)
                )
            )

            # Generate a positive transaction amount.
            amount = max(
                100,
                RNG.normal(
                    profile["amount_mean"],
                    profile["amount_std"]
                )
            )

            # Select another account as receiver.
            possible_receivers = accounts.loc[
                accounts["account_id"] != account.account_id,
                "account_id"
            ].values

            receiver_account_id = int(
                RNG.choice(possible_receivers)
            )

            # Determine whether this transaction is
            # part of a rapid movement pattern.
            rapid_transfer = (
                RNG.random()
                < profile["rapid_transfer_probability"]
            )

            # Determine whether a new beneficiary is used.
            new_beneficiary = (
                RNG.random()
                < profile["new_beneficiary_probability"]
            )

            transactions.append(
                {
                    "transaction_id": transaction_id,
                    "sender_account_id": account.account_id,
                    "receiver_account_id": receiver_account_id,
                    "amount": round(float(amount), 2),
                    "txn_time": transaction_time,
                    "rapid_transfer": int(rapid_transfer),
                    "new_beneficiary": int(new_beneficiary),
                    "behavior_profile": profile_name,
                }
            )

            transaction_id += 1

    return pd.DataFrame(transactions)

# ============================================================
# MULE-ACCOUNT SCENARIO INJECTION
# ============================================================

def inject_mule_scenarios(
    accounts: pd.DataFrame,
    transactions: pd.DataFrame,
) -> pd.DataFrame:
    """
    Inject explicit suspicious transaction patterns into the
    baseline transaction history.

    These scenarios provide structured behavioral examples
    for model training and evaluation.
    """

    injected_transactions = []

    next_transaction_id = (
        int(transactions["transaction_id"].max()) + 1
        if not transactions.empty
        else 1
    )

    suspicious_accounts = accounts[
        accounts["behavior_profile"].isin(
            [
                "rapid_movement",
                "transaction_burst",
                "beneficiary_anomaly",
                "behavioral_deviation",
            ]
        )
    ]

    # --------------------------------------------------------
    # Scenario 1: Rapid onward transfer
    # --------------------------------------------------------

    for account in suspicious_accounts.head(50).itertuples(
        index=False
    ):

        sender = account.account_id

        receiver_1 = int(
            RNG.choice(
                accounts.loc[
                    accounts["account_id"] != sender,
                    "account_id"
                ].values
            )
        )

        receiver_2 = int(
            RNG.choice(
                accounts.loc[
                    ~accounts["account_id"].isin(
                        [sender, receiver_1]
                    ),
                    "account_id"
                ].values
            )
        )

        base_time = pd.Timestamp("2026-03-15 10:00:00")

        amount = round(
            float(
                RNG.uniform(60000, 100000)
            ),
            2,
        )

        first_transaction = {
            "transaction_id": next_transaction_id,
            "sender_account_id": sender,
            "receiver_account_id": receiver_1,
            "amount": amount,
            "txn_time": base_time,
            "rapid_transfer": 1,
            "new_beneficiary": 1,
            "behavior_profile": account.behavior_profile,
        }

        injected_transactions.append(first_transaction)
        next_transaction_id += 1

        second_transaction = {
            "transaction_id": next_transaction_id,
            "sender_account_id": receiver_1,
            "receiver_account_id": receiver_2,
            "amount": round(amount * 0.96, 2),
            "txn_time": base_time + pd.Timedelta(minutes=7),
            "rapid_transfer": 1,
            "new_beneficiary": 1,
            "behavior_profile": account.behavior_profile,
        }

        injected_transactions.append(second_transaction)
        next_transaction_id += 1

    # --------------------------------------------------------
    # Scenario 2: Transaction burst
    # --------------------------------------------------------

    burst_accounts = accounts[
        accounts["behavior_profile"] == "transaction_burst"
    ].head(30)

    for account in burst_accounts.itertuples(index=False):

        sender = account.account_id

        for burst_number in range(8):

            possible_receivers = accounts.loc[
                accounts["account_id"] != sender,
                "account_id"
            ].values

            receiver = int(
                RNG.choice(possible_receivers)
            )

            transaction = {
                "transaction_id": next_transaction_id,
                "sender_account_id": sender,
                "receiver_account_id": receiver,
                "amount": round(
                    float(
                        RNG.uniform(5000, 25000)
                    ),
                    2,
                ),
                "txn_time": (
                    pd.Timestamp("2026-04-01 14:00:00")
                    + pd.Timedelta(
                        minutes=burst_number * 4
                    )
                ),
                "rapid_transfer": 1,
                "new_beneficiary": int(
                    burst_number >= 3
                ),
                "behavior_profile": account.behavior_profile,
            }

            injected_transactions.append(transaction)
            next_transaction_id += 1

    # --------------------------------------------------------
    # Scenario 3: Large-value money-flow chain
    # --------------------------------------------------------

    chain_accounts = accounts[
        accounts["behavior_profile"] == "high_value"
    ].head(20)

    for account in chain_accounts.itertuples(index=False):

        chain = [
            account.account_id
        ]

        available_accounts = accounts[
            ~accounts["account_id"].isin(chain)
        ]["account_id"].values

        for _ in range(3):

            next_account = int(
                RNG.choice(available_accounts)
            )

            chain.append(next_account)

            available_accounts = available_accounts[
                available_accounts != next_account
            ]

        base_time = pd.Timestamp(
            "2026-05-10 09:00:00"
        )

        base_amount = float(
            RNG.uniform(70000, 120000)
        )

        for hop in range(len(chain) - 1):

            transaction = {
                "transaction_id": next_transaction_id,
                "sender_account_id": chain[hop],
                "receiver_account_id": chain[hop + 1],
                "amount": round(
                    base_amount * (0.97 ** hop),
                    2,
                ),
                "txn_time": (
                    base_time
                    + pd.Timedelta(
                        minutes=8 * hop
                    )
                ),
                "rapid_transfer": 1,
                "new_beneficiary": 1,
                "behavior_profile": (
                    account.behavior_profile
                ),
            }

            injected_transactions.append(transaction)
            next_transaction_id += 1

    # --------------------------------------------------------
    # Combine baseline + injected transactions
    # --------------------------------------------------------

    injected_df = pd.DataFrame(
        injected_transactions
    )

    combined = pd.concat(
        [
            transactions,
            injected_df,
        ],
        ignore_index=True,
    )

    return combined

# ============================================================
# TRAINING LABEL GENERATION
# ============================================================

def assign_training_labels(
    transactions: pd.DataFrame,
) -> pd.DataFrame:
    """
    Assign training labels based on structured behavioral
    evidence present in the generated transaction history.

    label:
        0 -> normal / lower-risk behavior
        1 -> suspicious mule-account behavior
    """

    data = transactions.copy()

    # --------------------------------------------------------
    # Account-level behavioral indicators
    # --------------------------------------------------------

    account_stats = (
        data.groupby("sender_account_id")
        .agg(
            transaction_count=(
                "transaction_id",
                "count",
            ),
            total_amount=(
                "amount",
                "sum",
            ),
            average_amount=(
                "amount",
                "mean",
            ),
            maximum_amount=(
                "amount",
                "max",
            ),
            rapid_transfer_count=(
                "rapid_transfer",
                "sum",
            ),
            new_beneficiary_count=(
                "new_beneficiary",
                "sum",
            ),
        )
        .reset_index()
    )

    # --------------------------------------------------------
    # Normalize behavioral indicators
    # --------------------------------------------------------

    account_stats["rapid_transfer_ratio"] = (
        account_stats["rapid_transfer_count"]
        / account_stats["transaction_count"]
    )

    account_stats["new_beneficiary_ratio"] = (
        account_stats["new_beneficiary_count"]
        / account_stats["transaction_count"]
    )

       # --------------------------------------------------------
    # Strong suspicious-behavior combinations
    # --------------------------------------------------------

    account_stats["rapid_and_large"] = (
        (
            account_stats["rapid_transfer_ratio"] >= 0.25
        )
        &
        (
            account_stats["maximum_amount"] >= 75000
        )
    ).astype(int)

    account_stats["rapid_and_new_beneficiary"] = (
        (
            account_stats["rapid_transfer_ratio"] >= 0.25
        )
        &
        (
            account_stats["new_beneficiary_ratio"] >= 0.30
        )
    ).astype(int)

    account_stats["burst_and_large"] = (
        (
            account_stats["transaction_count"] >= 8
        )
        &
        (
            account_stats["maximum_amount"] >= 75000
        )
    ).astype(int)

    account_stats["high_volume_and_rapid"] = (
        (
            account_stats["total_amount"] >= 150000
        )
        &
        (
            account_stats["rapid_transfer_ratio"] >= 0.25
        )
    ).astype(int)

    # --------------------------------------------------------
    # Strong evidence score
    # --------------------------------------------------------

    account_stats["suspicious_signal_count"] = (
        account_stats["rapid_and_large"]
        + account_stats["rapid_and_new_beneficiary"]
        + account_stats["burst_and_large"]
        + account_stats["high_volume_and_rapid"]
    )

    # --------------------------------------------------------
    # Assign suspicious label when at least one
    # strong behavioral combination is present.
    # --------------------------------------------------------

    account_stats["risk_label"] = (
        account_stats["suspicious_signal_count"] >= 1
    ).astype(int)

    # --------------------------------------------------------
    # Assign suspicious label when at least one
    # strong behavioral combination is present.
    # --------------------------------------------------------

    account_stats["risk_label"] = (
        account_stats["suspicious_signal_count"] >= 1
    ).astype(int)
    # --------------------------------------------------------
    # Attach the account-level label to every transaction
    # belonging to that account.
    # --------------------------------------------------------

    data = data.merge(
        account_stats[
            [
                "sender_account_id",
                "risk_label",
            ]
        ],
        on="sender_account_id",
        how="left",
    )

    return data

# ============================================================
# DATA VALIDATION AND EXPORT
# ============================================================

def validate_dataset(data: pd.DataFrame) -> None:
    """
    Validate the generated transaction dataset before export.
    Raises ValueError if an important data-quality rule fails.
    """

    required_columns = {
        "transaction_id",
        "sender_account_id",
        "receiver_account_id",
        "amount",
        "txn_time",
        "rapid_transfer",
        "new_beneficiary",
        "behavior_profile",
        "risk_label",
    }

    missing_columns = (
        required_columns - set(data.columns)
    )

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    if data.empty:
        raise ValueError(
            "Generated dataset is empty."
        )

    if data["transaction_id"].duplicated().any():
        raise ValueError(
            "Duplicate transaction IDs detected."
        )

    if (data["sender_account_id"] == data["receiver_account_id"]).any():
        raise ValueError(
            "Self-transactions detected."
        )

    if (data["amount"] <= 0).any():
        raise ValueError(
            "Non-positive transaction amount detected."
        )

    if data["txn_time"].isna().any():
        raise ValueError(
            "Missing transaction timestamps detected."
        )

    if data["risk_label"].isna().any():
        raise ValueError(
            "Missing risk labels detected."
        )

    invalid_labels = set(
        data["risk_label"].unique()
    ) - {0, 1}

    if invalid_labels:
        raise ValueError(
            f"Invalid risk labels detected: {invalid_labels}"
        )

    print("Dataset validation passed.")


def save_dataset(data: pd.DataFrame) -> None:
    """
    Save the validated dataset to the ML data directory.
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    data = data.sort_values(
        "txn_time"
    ).reset_index(drop=True)

    data.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print(
        f"Dataset saved to: {OUTPUT_FILE}"
    )

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print("Generating synthetic MuleWatch data...")

    accounts = generate_accounts()

    print(
        f"Generated {len(accounts)} synthetic accounts."
    )

    transactions = generate_transactions(
        accounts
    )

    print(
        f"Generated {len(transactions)} baseline transactions."
    )

    transactions = inject_mule_scenarios(
        accounts,
        transactions,
    )

    print(
        f"Generated {len(transactions)} transactions "
        "after scenario injection."
    )

    dataset = assign_training_labels(
        transactions
    )

    validate_dataset(
        dataset
    )

    save_dataset(
        dataset
    )

    print("\nDataset summary:")
    print(
        dataset[
            [
                "transaction_id",
                "sender_account_id",
                "receiver_account_id",
                "amount",
                "txn_time",
                "behavior_profile",
                "risk_label",
            ]
        ].head(10)
    )

    print("\nRisk-label distribution:")
    print(
        dataset["risk_label"]
        .value_counts()
        .sort_index()
    )

    print("\nBehavior-profile distribution:")
    print(
        dataset["behavior_profile"]
        .value_counts()
    )
    
