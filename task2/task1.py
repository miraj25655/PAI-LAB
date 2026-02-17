import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.model_selection import cross_val_score, StratifiedKFold
import warnings
warnings.filterwarnings("ignore")

train = pd.read_csv("train.csv")
test = pd.read_csv("test.csv")

print("Train shape:", train.shape)
print("Test shape:", test.shape)
print(train.dtypes)
print(train.head())

missing = train.isnull().sum().sort_values(ascending=False)
print(missing)

plt.figure(figsize=(10, 4))
missing[missing > 0].plot(kind="bar", color="steelblue")
plt.title("Missing Values per Column")
plt.xlabel("Column")
plt.ylabel("Count")
plt.tight_layout()
plt.show()

print(train.describe())

print(train["Transported"].value_counts())

plt.figure(figsize=(5, 4))
train["Transported"].value_counts().plot(kind="bar", color=["steelblue", "salmon"])
plt.title("Transported Distribution")
plt.tight_layout()
plt.show()

plt.figure(figsize=(7, 4))
train["Age"].hist(bins=30, color="steelblue", edgecolor="white")
plt.title("Age Distribution")
plt.xlabel("Age")
plt.ylabel("Frequency")
plt.tight_layout()
plt.show()

spend_cols = ["RoomService", "FoodCourt", "ShoppingMall", "Spa", "VRDeck"]
total_spending = train[spend_cols].sum(axis=1)

plt.figure(figsize=(7, 4))
total_spending.hist(bins=30, color="teal", edgecolor="white")
plt.title("Total Spending Distribution")
plt.xlabel("Total Spending")
plt.ylabel("Frequency")
plt.tight_layout()
plt.show()

plt.figure(figsize=(5, 4))
train.assign(TotalSpending=total_spending).groupby("CryoSleep")["TotalSpending"].mean().plot(kind="bar", color=["coral", "mediumseagreen"])
plt.title("Average Spending by CryoSleep Status")
plt.tight_layout()
plt.show()

plt.figure(figsize=(5, 4))
train.groupby("CryoSleep")["Transported"].mean().plot(kind="bar", color=["coral", "mediumseagreen"])
plt.title("Transport Rate by CryoSleep Status")
plt.tight_layout()
plt.show()

plt.figure(figsize=(6, 4))
train["HomePlanet"].value_counts().plot(kind="bar", color="slateblue")
plt.title("Passengers by HomePlanet")
plt.tight_layout()
plt.show()

plt.figure(figsize=(6, 4))
train.groupby("HomePlanet")["Transported"].mean().plot(kind="bar", color="slateblue")
plt.title("Transport Rate by HomePlanet")
plt.tight_layout()
plt.show()

plt.figure(figsize=(5, 4))
train.groupby("VIP")["Transported"].mean().plot(kind="bar", color=["gray", "gold"])
plt.title("Transport Rate by VIP Status")
plt.tight_layout()
plt.show()

train[["Deck", "CabinNum", "Side"]] = train["Cabin"].str.split("/", expand=True)

plt.figure(figsize=(7, 4))
train["Deck"].value_counts().plot(kind="bar", color="mediumpurple")
plt.title("Passengers by Deck")
plt.tight_layout()
plt.show()

numeric_cols = ["Age", "RoomService", "FoodCourt", "ShoppingMall", "Spa", "VRDeck"]
corr_df = train[numeric_cols].copy()
corr_df["TotalSpending"] = total_spending
plt.figure(figsize=(10, 8))
sns.heatmap(corr_df.corr(), annot=True, cmap="coolwarm", fmt=".2f")
plt.title("Correlation Heatmap")
plt.tight_layout()
plt.show()

print("KEY INSIGHTS:")
print("CryoSleep passengers spend almost nothing.")
print("High spenders are less likely to be transported.")
print("Europa passengers have the highest transport rate.")
print("Dataset has missing values that need handling before modelling.")


def build_features(df):
    data = df.copy()

    def parse_cabin(x):
        if pd.isna(x):
            return pd.Series([np.nan, np.nan, np.nan])
        parts = x.split("/")
        return pd.Series(parts) if len(parts) == 3 else pd.Series([np.nan, np.nan, np.nan])

    data[["Deck", "Num", "Side"]] = data["Cabin"].apply(parse_cabin)
    data["Num"] = pd.to_numeric(data["Num"], errors="coerce")

    data["Group"] = data["PassengerId"].str.split("_").str[0]
    data["GroupSize"] = data.groupby("Group")["Group"].transform("count")
    data["IsSolo"] = (data["GroupSize"] == 1).astype(int)

    data["TotalSpend"] = data[spend_cols].sum(axis=1)
    data["HasSpend"] = (data["TotalSpend"] > 0).astype(int)

    cryo_mask = data["CryoSleep"] == True
    data.loc[cryo_mask, spend_cols] = data.loc[cryo_mask, spend_cols].fillna(0)

    for col in spend_cols + ["TotalSpend"]:
        data[f"log_{col}"] = np.log1p(data[col].fillna(0))

    data["AgeGroup"] = pd.cut(
        data["Age"],
        bins=[0, 12, 18, 35, 60, 200],
        labels=["child", "teen", "young_adult", "adult", "senior"]
    ).astype(str)

    for col in ["CryoSleep", "VIP"]:
        data[col] = data[col].map({True: 1, False: 0, "True": 1, "False": 0})

    data = data.drop(["Name", "Cabin", "Group"], axis=1)
    return data


train_clean = build_features(train)
test_clean = build_features(test)

X = train_clean.drop(["PassengerId", "Transported"], axis=1)
y = train_clean["Transported"].astype(int)
X_test = test_clean.drop(["PassengerId"], axis=1)
test_ids = test_clean["PassengerId"]

X_test = X_test.reindex(columns=X.columns, fill_value=np.nan)

numerical_cols = (
    ["Age", "Num", "GroupSize", "TotalSpend", "IsSolo", "HasSpend", "CryoSleep", "VIP"]
    + spend_cols
    + [f"log_{c}" for c in spend_cols + ["TotalSpend"]]
)
numerical_cols = [c for c in numerical_cols if c in X.columns]
categorical_cols = [c for c in ["HomePlanet", "Destination", "Deck", "Side", "AgeGroup"] if c in X.columns]

num_transformer = Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("scaler", StandardScaler()),
])

cat_transformer = Pipeline([
    ("imputer", SimpleImputer(strategy="most_frequent")),
    ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
])

preprocessor = ColumnTransformer([
    ("num", num_transformer, numerical_cols),
    ("cat", cat_transformer, categorical_cols),
])

rf = Pipeline([
    ("preprocessor", preprocessor),
    ("classifier", RandomForestClassifier(n_estimators=300, min_samples_split=4, min_samples_leaf=2,
                                          max_features="sqrt", random_state=42, n_jobs=-1)),
])

gbm = Pipeline([
    ("preprocessor", preprocessor),
    ("classifier", GradientBoostingClassifier(n_estimators=300, learning_rate=0.05,
                                               max_depth=5, subsample=0.8, random_state=42)),
])

ensemble = VotingClassifier(estimators=[("rf", rf), ("gbm", gbm)], voting="soft")

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

print("\nCross-Validation Scores:")
for name, mdl in [("RandomForest", rf), ("GBM", gbm), ("Ensemble", ensemble)]:
    scores = cross_val_score(mdl, X, y, cv=cv, scoring="accuracy", n_jobs=-1)
    print(f"  {name}: {scores.mean():.4f} ± {scores.std():.4f}")

print("\nTraining final model...")
ensemble.fit(X, y)

predictions = ensemble.predict(X_test).astype(bool)

output = pd.DataFrame({
    "PassengerId": test_ids,
    "Transported": predictions
})

output.to_csv("submission.csv", index=False)
print("submission.csv saved —", len(output), "rows")
print(output.head())
