import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import lightgbm as lgbm
import catboost as cb
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report
from sklearn.ensemble import VotingClassifier

# Load data
file_path = r"C:\Users\rajk8\OneDrive\Desktop\final-year-project\copy\java_features_analysis.xlsx"
df = pd.read_excel(file_path)
print(file_path,df.head())
# Prepare features and target
X = df.drop(columns=["bug_or_not", "file_name", "topic"])
y = df["bug_or_not"]
print(X,y,df.head())
# Preprocess data
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Split data
X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y, test_size=0.2, random_state=42, stratify=y
)

# Calculate class imbalance ratio for weighting
scale_pos_weight = len(y_train[y_train == 0]) / len(y_train[y_train == 1])

# ---- LightGBM Model ----
print("Training LightGBM model...")

# LightGBM hyperparameter grid
lgbm_param_grid = {
    'n_estimators': [200, 300, 500],
    'max_depth': [5, 7, 9],
    'learning_rate': [0.01, 0.05, 0.1],
    'num_leaves': [31, 63, 127],
    'boosting_type': ['gbdt', 'dart'],
    'class_weight': ['balanced', None],
    'min_child_samples': [10, 20, 30]
}

# Initialize LightGBM classifier
lgbm_model = lgbm.LGBMClassifier(
    objective='binary',
    scale_pos_weight=scale_pos_weight,
    random_state=42
)

# Perform grid search
lgbm_grid_search = GridSearchCV(
    lgbm_model,
    lgbm_param_grid,
    scoring='accuracy',
    cv=3,
    n_jobs=-1,
    verbose=1
)

lgbm_grid_search.fit(X_train, y_train)

# Get best LightGBM model
best_lgbm_model = lgbm_grid_search.best_estimator_
lgbm_y_pred = best_lgbm_model.predict(X_test)

print(f"Best LightGBM parameters: {lgbm_grid_search.best_params_}")
print(f"LightGBM Accuracy: {accuracy_score(y_test, lgbm_y_pred):.4f}")
print("LightGBM Classification Report:\n", classification_report(y_test, lgbm_y_pred))

# Plot feature importance for LightGBM
plt.figure(figsize=(12, 6))
lgbm.plot_importance(best_lgbm_model, max_num_features=15)
plt.title("LightGBM Feature Importance")
plt.tight_layout()
plt.show()

# ---- CatBoost Model ----
print("\nTraining CatBoost model...")

# CatBoost hyperparameter grid
cat_param_grid = {
    'iterations': [200, 300, 500],
    'depth': [5, 7, 9],
    'learning_rate': [0.01, 0.05, 0.1],
    'l2_leaf_reg': [1, 3, 5],
    'border_count': [32, 64, 128],
    'bagging_temperature': [0, 1, 10]
}

# Initialize CatBoost classifier
cat_model = cb.CatBoostClassifier(
    loss_function='Logloss',
    eval_metric='Accuracy',
    scale_pos_weight=scale_pos_weight,
    random_seed=42,
    verbose=0
)

# Perform grid search
cat_grid_search = GridSearchCV(
    cat_model,
    cat_param_grid,
    scoring='accuracy',
    cv=3,
    n_jobs=-1,
    verbose=1
)

cat_grid_search.fit(X_train, y_train)

# Get best CatBoost model
best_cat_model = cat_grid_search.best_estimator_
cat_y_pred = best_cat_model.predict(X_test)

print(f"Best CatBoost parameters: {cat_grid_search.best_params_}")
print(f"CatBoost Accuracy: {accuracy_score(y_test, cat_y_pred):.4f}")
print("CatBoost Classification Report:\n", classification_report(y_test, cat_y_pred))

# Plot feature importance for CatBoost
plt.figure(figsize=(12, 6))
feature_importances = best_cat_model.get_feature_importance()
sorted_idx = np.argsort(feature_importances)[-15:]  # Top 15 features
plt.barh(range(len(sorted_idx)), feature_importances[sorted_idx])
plt.yticks(range(len(sorted_idx)), np.array(X.columns)[sorted_idx])
plt.title("CatBoost Feature Importance")
plt.tight_layout()
plt.show()

# ---- Ensemble Model (Voting Classifier) ----
print("\nCreating ensemble model...")

# Create voting classifier combining both models
ensemble_model = VotingClassifier(
    estimators=[
        ('lightgbm', best_lgbm_model),
        ('catboost', best_cat_model)
    ],
    voting='soft'  # Use probability predictions for voting
)

# Fit ensemble model
ensemble_model.fit(X_train, y_train)

# Make predictions
ensemble_y_pred = ensemble_model.predict(X_test)

# Evaluate ensemble model
ensemble_accuracy = accuracy_score(y_test, ensemble_y_pred)
print(f"Ensemble Model Accuracy: {ensemble_accuracy:.4f}")
print("Ensemble Classification Report:\n", classification_report(y_test, ensemble_y_pred))

# ---- Neural Network-like Ensemble with Feature Extraction ----
print("\nCreating neural network-like stacked ensemble...")

# Extract predicted probabilities from base models as meta-features
lgbm_proba = best_lgbm_model.predict_proba(X_train)
cat_proba = best_cat_model.predict_proba(X_train)

# Combine original features with model predictions for meta-learning
meta_features_train = np.column_stack([X_train, lgbm_proba, cat_proba])

# Create a meta-classifier (CatBoost) that learns from base model predictions
meta_model = cb.CatBoostClassifier(
    iterations=300,
    depth=6,
    learning_rate=0.05,
    verbose=0
)

# Train meta-model on the combined features
meta_model.fit(meta_features_train, y_train)

# Apply the same transformation to test data
lgbm_test_proba = best_lgbm_model.predict_proba(X_test)
cat_test_proba = best_cat_model.predict_proba(X_test)
meta_features_test = np.column_stack([X_test, lgbm_test_proba, cat_test_proba])

# Predict with meta-model
meta_y_pred = meta_model.predict(meta_features_test)

# Evaluate meta-model
meta_accuracy = accuracy_score(y_test, meta_y_pred)
print(f"Neural Network-like Stacked Ensemble Accuracy: {meta_accuracy:.4f}")
print("Stacked Ensemble Classification Report:\n", classification_report(y_test, meta_y_pred))

# Save the best model
import pickle
best_model = None
best_accuracy = max(
    accuracy_score(y_test, lgbm_y_pred),
    accuracy_score(y_test, cat_y_pred),
    ensemble_accuracy,
    meta_accuracy
)

if best_accuracy == accuracy_score(y_test, lgbm_y_pred):
    best_model = best_lgbm_model
    best_model_name = "LightGBM"
elif best_accuracy == accuracy_score(y_test, cat_y_pred):
    best_model = best_cat_model
    best_model_name = "CatBoost"
elif best_accuracy == ensemble_accuracy:
    best_model = ensemble_model
    best_model_name = "Voting Ensemble"
else:
    best_model = {
        'meta_model': meta_model,
        'lgbm_model': best_lgbm_model,
        'cat_model': best_cat_model
    }
    best_model_name = "Stacked Ensemble"

with open('best_bug_detection_model.pkl', 'wb') as f:
    pickle.dump(best_model, f)

print(f"\nThe best model was: {best_model_name} with accuracy: {best_accuracy:.4f}")
print("Model saved as 'best_bug_detection_model.pkl'")