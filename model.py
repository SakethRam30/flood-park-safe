import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split


# ─────────────────────────────────────────────
# STREET DATABASE
# ─────────────────────────────────────────────
STREETS = {
    "Observer Highway":  {"elevation_ft": 2.1,  "base_risk": 85},
    "1st Street":        {"elevation_ft": 2.5,  "base_risk": 78},
    "2nd Street":        {"elevation_ft": 3.0,  "base_risk": 72},
    "3rd Street":        {"elevation_ft": 3.8,  "base_risk": 65},
    "4th Street":        {"elevation_ft": 4.2,  "base_risk": 58},
    "5th Street":        {"elevation_ft": 5.2,  "base_risk": 45},
    "Washington Street": {"elevation_ft": 8.5,  "base_risk": 25},
    "14th Street":       {"elevation_ft": 14.0, "base_risk": 8},
    "15th Street":       {"elevation_ft": 15.5, "base_risk": 5},
}


# ─────────────────────────────────────────────
# GENERATE TRAINING DATA
# ─────────────────────────────────────────────
def generate_training_data(n=2000):
    np.random.seed(42)

    elevation  = np.clip(np.random.normal(8, 3, n), 0, 25)
    rainfall   = np.clip(np.random.normal(15, 10, n), 0, None)
    wind_speed = np.clip(np.random.normal(20, 8, n), 0, None)
    humidity   = np.clip(np.random.normal(75, 10, n), 0, 100)
    hour       = np.random.randint(0, 24, n)
    tide       = np.clip(np.random.normal(3, 1, n), 0, None)

    risk = (
        0.35 * rainfall +
        0.30 * tide +
        0.20 * wind_speed -
        0.25 * elevation +
        0.05 * rainfall * tide
    )

    risk = np.clip(risk, 0, None)
    risk = (risk - risk.min()) / (risk.max() - risk.min())
    risk = risk * 100

    return pd.DataFrame({
        "elevation_ft":   elevation,
        "rainfall_mmhr":  rainfall,
        "wind_speed_mph": wind_speed,
        "humidity_pct":   humidity,
        "hour_of_day":    hour,
        "tide_level_ft":  tide,
        "risk_score":     risk,
    })


# ─────────────────────────────────────────────
# TRAIN MODEL
# ─────────────────────────────────────────────
def train_model():
    df = generate_training_data()

    features = [
        "elevation_ft",
        "rainfall_mmhr",
        "wind_speed_mph",
        "humidity_pct",
        "hour_of_day",
        "tide_level_ft"
    ]

    X = df[features]
    y = df["risk_score"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = RandomForestRegressor(
        n_estimators=2000,
        max_depth=12,
        random_state=42
    )

    model.fit(X_train, y_train)

    from sklearn.metrics import mean_absolute_error, r2_score
    y_pred = model.predict(X_test)

    print("✅ Model trained!")
    print(f"   MAE: {mean_absolute_error(y_test, y_pred):.2f}")
    print(f"   R²:  {r2_score(y_test, y_pred):.3f}")

    return model, features


# ─────────────────────────────────────────────
# FETCH LIVE WEATHER
# ─────────────────────────────────────────────
def get_live_weather():
    import requests

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": 40.7440,
        "longitude": -74.0324,
        "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "timezone": "America/New_York"
    }

    res = requests.get(url, params=params, timeout=5)
    c = res.json()["current"]

    return {
        "temp_f":   c["temperature_2m"],
        "humidity": c["relative_humidity_2m"],
        "rain_mm":  c["precipitation"] * 25.4,
        "wind_mph": c["wind_speed_10m"],
    }


# ─────────────────────────────────────────────
# PREDICT RISK
# ─────────────────────────────────────────────
def predict_risk(model, features, street_name, hour=None):
    import datetime

    if hour is None:
        hour = datetime.datetime.now().hour

    street = STREETS.get(street_name)
    if not street:
        return None

    weather = get_live_weather()

    input_data = pd.DataFrame([{
        "elevation_ft":   street["elevation_ft"],
        "rainfall_mmhr":  weather["rain_mm"],
        "wind_speed_mph": weather["wind_mph"],
        "humidity_pct":   weather["humidity"],
        "hour_of_day":    hour,
        "tide_level_ft":  4.5
    }], columns=features)

    risk_score = round(model.predict(input_data)[0])
    risk_score = max(0, min(100, risk_score))

    if risk_score >= 70:
        level = "HIGH"
        advice = "Move your vehicle immediately to an elevated garage."
    elif risk_score >= 40:
        level = "MODERATE"
        advice = "Monitor conditions closely."
    else:
        level = "LOW"
        advice = "Conditions look safe."

    return {
        "street": street_name,
        "risk_score": risk_score,
        "risk_level": level,
        "advice": advice,
        "elevation_ft": street["elevation_ft"],
        "weather": weather,
    }


# ─────────────────────────────────────────────
# INITIALIZE MODEL ON IMPORT
# ─────────────────────────────────────────────

model, features = train_model()


# ─────────────────────────────────────────────
# RUN WHEN FILE IS EXECUTED DIRECTLY
# ─────────────────────────────────────────────
if __name__ == "__main__":
    model, features = train_model()

    result = predict_risk(model, features, "Observer Highway")

    print("\nPrediction Example:")
    print(result)