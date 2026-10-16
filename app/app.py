
from pathlib import Path
import json

import joblib
import numpy as np
import pandas as pd
import streamlit as st


# ---------------------------------------------------------
# UrbanPulse AI — Interactive research dashboard
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = PROJECT_ROOT / "models"
REPORTS_DIR = PROJECT_ROOT / "reports"
DATA_DIR = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "beijing"
    / "extracted"
    / "PRSA_Data_20130301-20170228"
)

MODEL_PATH = MODELS_DIR / "urbanpulse_spatial_rf.joblib"
IMPUTER_PATH = MODELS_DIR / "urbanpulse_spatial_imputer.joblib"
METADATA_PATH = REPORTS_DIR / "spatial_rf_metadata.json"

st.set_page_config(
    page_title="UrbanPulse AI",
    page_icon="🌫️",
    layout="wide",
)

st.title("UrbanPulse AI")
st.caption(
    "An exploratory air-quality forecasting and "
    "scenario-sensitivity platform"
)

st.info(
    "Research prototype: forecasts and what-if results are "
    "model outputs, not causal estimates or official air-quality alerts."
)



@st.cache_resource
def load_model_artifacts():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model not found: {MODEL_PATH}")

    if not IMPUTER_PATH.exists():
        raise FileNotFoundError(f"Imputer not found: {IMPUTER_PATH}")

    if not METADATA_PATH.exists():
        raise FileNotFoundError(f"Metadata not found: {METADATA_PATH}")

    model = joblib.load(MODEL_PATH)
    imputer = joblib.load(IMPUTER_PATH)

    with open(METADATA_PATH, "r", encoding="utf-8") as file:
        metadata = json.load(file)

    # Recover feature names from known metadata conventions.
    feature_keys = [
        "features",
        "feature_columns",
        "feature_names",
        "input_features",
        "station_features",
    ]

    features = next(
        (
            metadata[key]
            for key in feature_keys
            if key in metadata
            and isinstance(metadata[key], list)
            and metadata[key]
        ),
        None,
    )

    # A fitted scikit-learn model may retain its training column order.
    model_features = getattr(model, "feature_names_in_", None)

    if model_features is not None:
        model_features = list(model_features)

        if features is not None and features != model_features:
            raise ValueError(
                "Metadata feature order differs from the saved model's "
                "training feature order. Inspect the metadata before "
                "running predictions."
            )

        features = model_features

    if features is None:
        raise KeyError(
            "Could not find station feature names in metadata or model. "
            f"Metadata keys: {list(metadata.keys())}. "
            "Inspect spatial_rf_metadata.json and the saved model."
        )

    if len(features) != 12 or len(set(features)) != 12:
        raise ValueError(
            f"Expected 12 unique station features, got {features}"
        )

    if hasattr(model, "n_features_in_"):
        if model.n_features_in_ != len(features):
            raise ValueError(
                f"Model expects {model.n_features_in_} features, "
                f"but metadata provides {len(features)}."
            )

    if hasattr(imputer, "n_features_in_"):
        if imputer.n_features_in_ != len(features):
            raise ValueError(
                f"Imputer expects {imputer.n_features_in_} features, "
                f"but metadata provides {len(features)}."
            )

    metadata["features"] = features

    return model, imputer, metadata

@st.cache_data
def load_report_csv(filename):
    path = REPORTS_DIR / filename
    if not path.exists():
        return None
    return pd.read_csv(path)


try:
    model, imputer, metadata = load_model_artifacts()
except Exception as exc:
    st.error(f"Unable to load the saved model artifacts: {exc}")
    st.stop()

features = metadata["features"]

# ---------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------

page = st.sidebar.radio(
    "Explore UrbanPulse AI",
    [
        "Project overview",
        "Model evaluation",
        "Spatial analysis",
        "Anomaly detection",
        "What-if explorer",
        "Research limitations",
    ],
)

st.sidebar.divider()
st.sidebar.write("**Forecast target**")
st.sidebar.write("Aotizhongxin PM2.5, one hour ahead")
st.sidebar.write("**Model**")
st.sidebar.write("Saved multi-station Random Forest")
st.sidebar.write("**Historical period**")
st.sidebar.write("March 2013 – February 2017")


# ---------------------------------------------------------
# Project overview
# ---------------------------------------------------------

if page == "Project overview":
    st.header("Project overview")

    c1, c2, c3 = st.columns(3)
    c1.metric("Monitoring stations", "12")
    c2.metric("Historical coverage", "2013–2017")
    c3.metric("Forecast horizon", "1 hour ahead")

    st.markdown(
        """
        UrbanPulse AI explores how historical pollution observations
        from multiple monitoring stations can support short-term
        PM2.5 forecasting.

        The project includes:

        - Historical data preparation and exploratory analysis
        - Machine-learning and LSTM forecasting experiments
        - Anomaly detection using complementary detectors
        - Multi-station forecasting and spatial feature analysis
        - Model explainability and what-if sensitivity analysis
        """
    )

    st.subheader("Available project reports")

    report_files = [
        "spatial_forecasting_metrics.csv",
        "spatial_test_diagnostic_metrics.csv",
        "spatial_test_metrics_by_pollution_level.csv",
        "spatial_test_monthly_metrics.csv",
        "what_if_scenario_summary.csv",
        "what_if_input_range_audit_summary.csv",
    ]

    for filename in report_files:
        path = REPORTS_DIR / filename
        if path.exists():
            st.write(f"✓ {filename}")
        else:
            st.write(f"Not available yet: {filename}")


# ---------------------------------------------------------
# Model evaluation
# ---------------------------------------------------------

elif page == "Model evaluation":
    st.header("Forecasting model evaluation")

    metrics = load_report_csv("spatial_forecasting_metrics.csv")

    if metrics is None:
        st.warning(
            "The spatial forecasting metrics report was not found."
        )
    else:
        st.dataframe(metrics, use_container_width=True)

        numeric_cols = [
            col for col in ["MAE", "RMSE", "R2", "R²"]
            if col in metrics.columns
        ]

        if "Model" in metrics.columns and "RMSE" in metrics.columns:
            st.subheader("Test or validation RMSE")
            st.bar_chart(metrics.set_index("Model")["RMSE"])

        diagnostic = load_report_csv(
            "spatial_test_diagnostic_metrics.csv"
        )

        if diagnostic is not None:
            st.subheader("Test-set diagnostic metrics")
            st.dataframe(diagnostic, use_container_width=True)

    st.caption(
        "Consult the report's split and model columns before comparing "
        "metrics. Validation and test scores must not be conflated."
    )


# ---------------------------------------------------------
# Spatial analysis
# ---------------------------------------------------------

elif page == "Spatial analysis":
    st.header("Multi-station spatial analysis")

    importance = load_report_csv(
        "spatial_test_permutation_importance.csv"
    )

    if importance is not None:
        st.subheader("Permutation importance")

        if "Station" in importance.columns:
            st.dataframe(
                importance.sort_values(
                    importance.columns[
                        importance.columns.str.contains(
                            "increase", case=False
                        )
                    ][0]
                , ascending=False),
                use_container_width=True,
            )
        else:
            st.dataframe(importance, use_container_width=True)
    else:
        st.warning(
            "The spatial permutation-importance report was not found."
        )

    correlations = load_report_csv(
        "spatial_pm25_correlation.csv"
    )

    if correlations is not None:
        st.subheader("Station correlation report")
        st.dataframe(correlations, use_container_width=True)

    st.caption(
        "Feature importance and correlation describe model dependence "
        "or statistical association. They do not establish causation."
    )


# ---------------------------------------------------------
# Anomaly detection
# ---------------------------------------------------------

elif page == "Anomaly detection":
    st.header("Historical anomaly detection")

    detector_summary = load_report_csv(
        "anomaly_detection_detector_summary.csv"
    )

    monthly_summary = load_report_csv(
        "anomaly_detection_monthly_summary.csv"
    )

    anomaly_results = load_report_csv(
        "anomaly_detection_results.csv"
    )

    if detector_summary is not None:
        st.subheader("Detector summary")
        st.dataframe(detector_summary, use_container_width=True)
    else:
        st.warning("Detector summary report not found.")

    if monthly_summary is not None:
        st.subheader("Monthly summary")
        st.dataframe(monthly_summary, use_container_width=True)

    if anomaly_results is not None:
        st.subheader("Flagged observations")
        st.dataframe(
            anomaly_results.head(500),
            use_container_width=True,
        )
        if len(anomaly_results) > 500:
            st.caption(
                "Showing the first 500 rows of the saved anomaly report."
            )

    st.warning(
        "An anomaly flag indicates an unusual observation according "
        "to a detector. It does not prove that the measurement is wrong."
    )


# ---------------------------------------------------------
# What-if explorer
# ---------------------------------------------------------

elif page == "What-if explorer":
    st.header("Interactive what-if explorer")

    st.markdown(
        """
        Change one or more station input concentrations and inspect
        the model's conditional next-hour prediction.

        The model was trained on historical station observations.
        Hypothetical inputs can fall outside its training distribution.
        """
    )

    # A historical input vector provides a more meaningful starting
    # point than an arbitrary hand-entered vector.
    station_frames = []

    for station in features:
        station_path = DATA_DIR / (
            f"PRSA_Data_{station}_20130301-20170228.csv"
        )

        if not station_path.exists():
            st.error(f"Station data file missing: {station_path}")
            st.stop()

        frame = pd.read_csv(station_path)

        timestamp = pd.to_datetime(
            frame[["year", "month", "day", "hour"]]
            .rename(
                columns={
                    "year": "year",
                    "month": "month",
                    "day": "day",
                    "hour": "hour",
                }
            )
        )

        station_series = pd.Series(
            pd.to_numeric(frame["PM2.5"], errors="coerce").to_numpy(),
            index=timestamp,
            name=station,
        )

        station_frames.append(station_series)

    station_wide = pd.concat(station_frames, axis=1).sort_index()

    historical_time = st.selectbox(
        "Select a historical input hour",
        options=station_wide.index,
        format_func=lambda value: value.strftime("%Y-%m-%d %H:%M"),
        index=max(0, len(station_wide.index) - 2),
    )

    base_row = station_wide.loc[[historical_time], features].copy()

    st.caption(
        "The selected timestamp is the input hour. The model estimates "
        "Aotizhongxin PM2.5 for the following hour."
    )

    st.subheader("Input station concentrations")

    edited_values = {}

    for feature in features:
        original_value = base_row.iloc[0][feature]

        if pd.isna(original_value):
            default_value = 0.0
        else:
            default_value = float(original_value)

        edited_values[feature] = st.number_input(
            feature,
            min_value=0.0,
            value=default_value,
            step=1.0,
            format="%.2f",
            key=f"whatif_{feature}",
        )

    edited_row = pd.DataFrame(
        [[edited_values[feature] for feature in features]],
        columns=features,
    )

    st.subheader("Scenario perturbation")

    mode = st.radio(
        "Apply a percentage change to",
        [
            "No additional change",
            "All 12 stations",
            "Aotizhongxin only",
            "Dingling only",
        ],
        horizontal=True,
    )

    percentage = st.slider(
        "Percentage change",
        min_value=-30,
        max_value=30,
        value=0,
        step=5,
    )

    if mode != "No additional change":
        if mode == "All 12 stations":
            changed_features = features
        elif mode == "Aotizhongxin only":
            changed_features = ["Aotizhongxin"]
        else:
            changed_features = ["Dingling"]

        edited_row.loc[:, changed_features] *= (
            1 + percentage / 100
        )

    if st.button("Run what-if prediction", type="primary"):
        if not np.isfinite(edited_row.to_numpy(dtype=float)).all():
            st.error("Please provide finite numeric inputs.")
            st.stop()

        if (edited_row.to_numpy(dtype=float) < 0).any():
            st.error("Negative concentrations are not permitted.")
            st.stop()

        transformed = imputer.transform(edited_row[features])

        prediction = float(model.predict(transformed)[0])

        st.metric(
            "Predicted next-hour Aotizhongxin PM2.5",
            f"{prediction:.2f} µg/m³",
        )

        st.write("Modified scenario inputs")
        st.dataframe(edited_row, use_container_width=True)

        st.caption(
            "This is a conditional model prediction for the supplied "
            "hypothetical input vector. It is not a causal estimate, "
            "an official warning, or a guaranteed future measurement."
        )


# ---------------------------------------------------------
# Research limitations
# ---------------------------------------------------------

elif page == "Research limitations":
    st.header("Research limitations")

    st.markdown(
        """
        **Historical coverage:** The underlying Beijing dataset spans
        March 2013 through February 2017.

        **Forecast target:** The saved spatial Random Forest predicts
        Aotizhongxin PM2.5 one hour ahead from current-hour PM2.5
        readings at twelve stations.

        **Generalization:** Historical performance does not guarantee
        equivalent performance in other cities, later years, or
        changed monitoring conditions.

        **Anomaly detection:** Flags indicate unusual patterns rather
        than confirmed data errors or health emergencies.

        **What-if analysis:** Scenario results describe model
        sensitivity to hypothetical inputs, not causal intervention
        effects.

        **Operational use:** This dashboard is a research prototype,
        not an official air-quality monitoring or public-warning system.
        """
    )

st.divider()
st.caption(
    "UrbanPulse AI | Research prototype | "
    "Historical observations and conditional model outputs"
)
