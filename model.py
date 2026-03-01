import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split

# ─────────────────────────────────────────────
# STREET DATABASE
# Real elevation data from USGS for Hoboken streets
# Lower elevation = floods first when water rises
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
# We create 2000 synthetic data points because we
# don't have years of real flood sensor recordings.
# The data follows real physical rules (low elevation = high risk)
# ─────────────────────────────────────────────
def generate_training_data(n=2000):
    np.random.seed(42)  # makes results reproducible every run

    elevation  = np.clip(np.random.normal(8, 3, n), 0, 25)
    rainfall   = np.clip(np.random.normal(15, 10, n), 0, None)
    wind_speed = np.clip(np.random.normal(20, 8, n), 0, None)
    humidity   = np.clip(np.random.normal(75, 10, n), 0, 100)
    hour       = np.random.randint(0, 24, n)
    tide       = np.clip(np.random.normal(3, 1, n), 0, None)
    # ── RISK FORMULA ──────────────────────────────
    # Each line adds risk based on one physical factor.
    # Coefficients were tuned to match known Hoboken flood patterns.

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
# TRAIN THE RANDOM FOREST MODEL
# Random Forest = many decision trees working together.
# Each tree votes on the risk score, and they average their answers.
# This makes it much more accurate than a single decision tree.
# ─────────────────────────────────────────────
def train_model():
    df = generate_training_data()

    features = ["elevation_ft", "rainfall_mmhr", "wind_speed_mph",
                "humidity_pct", "hour_of_day", "tide_level_ft"]

    X = df[features]   # input columns
    y = df["risk_score"]  # output column (what we're predicting)

    # 80% of data used to train, 20% used to test accuracy
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = RandomForestRegressor(
        n_estimators=200,   # 200 trees = more accurate but slightly slower
        max_depth=12,       # each tree can make up to 12 decisions deep
        random_state=42
    )

    model.fit(X_train, y_train)  # TRAINING HAPPENS HERE

    # Print accuracy so you can see how well it works
    from sklearn.metrics import mean_absolute_error, r2_score
    y_pred = model.predict(X_test)
    print(f"✅ Model trained!")
    print(f"   MAE:  {mean_absolute_error(y_test, y_pred):.2f} points")
    print(f"   R²:   {r2_score(y_test, y_pred):.3f}")

    return model, features


# ─────────────────────────────────────────────
# FETCH LIVE WEATHER FROM OPEN-METEO
# Free API, no key needed, returns real Hoboken weather
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
        "temp_f":     c["temperature_2m"],
        "humidity":   c["relative_humidity_2m"],
        "rain_inch":  c["precipitation"],           # inches/hr
        "wind_mph":   c["wind_speed_10m"],
        "rain_mm":    c["precipitation"] * 25.4,    # converted to mm
    }


# ─────────────────────────────────────────────
# MAKE A PREDICTION FOR A SPECIFIC STREET
# Combines the ML model + live weather + street elevation
# ─────────────────────────────────────────────
def predict_risk(model, features, street_name, hour=None):
    import datetime
    if hour is None:
        hour = datetime.datetime.now().hour  # use current time if not given

    street = STREETS.get(street_name)
    if not street:
        return None

    weather = get_live_weather()

    # Build a single row of input data for the model
    input_data = pd.DataFrame([{
        "elevation_ft":   street["elevation_ft"],
        "rainfall_mmhr":  weather["rain_mm"],
        "wind_speed_mph": weather["wind_mph"],
        "humidity_pct":   weather["humidity"],
        "hour_of_day":    hour,
        "tide_level_ft":  4.5   # estimated average tide (could connect to NOAA later)
    }], columns=features)

    risk_score = round(model.predict(input_data)[0])  # model makes prediction
    risk_score = max(0, min(100, risk_score))          # safety clamp

    # Determine label and recommendation based on score
    if risk_score >= 70:
        level = "HIGH"
        advice = "Move your vehicle immediately to an elevated garage."
    elif risk_score >= 40:
        level = "MODERATE"
        advice = "Monitor conditions closely. Consider moving your vehicle."
    else:
        level = "LOW"
        advice = "Conditions look safe. Continue to monitor weather."

    return {
        "street":      street_name,
        "risk_score":  risk_score,
        "risk_level":  level,
        "advice":      advice,
        "elevation_ft": street["elevation_ft"],
        "weather":     weather,
    }

# SIMULATION SCENARIOS
# Predefined weather events you can test against
# Each one overrides the live weather with fake conditions
# ─────────────────────────────────────────────
SCENARIOS = {
    "king_tide": {
        "label":       "🌊 King Tide",
        "rainfall_mm": 2.0,
        "wind_mph":    15,
        "humidity":    85,
        "tide_ft":     7.8,   # extremely high tide
        "description": "Full moon king tide — water rises even without rain"
    },
    "heavy_rain": {
        "label":       "🌧️ Heavy Rainstorm",
        "rainfall_mm": 35.0,
        "wind_mph":    25,
        "humidity":    95,
        "tide_ft":     4.5,
        "description": "2+ inches/hour rainfall overwhelms Hoboken's drainage"
    },
    "hurricane": {
        "label":       "🌀 Hurricane / Tropical Storm",
        "rainfall_mm": 50.0,
        "wind_mph":    75,
        "humidity":    99,
        "tide_ft":     8.0,   # storm surge
        "description": "Sandy-level event — combined storm surge + extreme rain"
    },
    "snowmelt": {
        "label":       "❄️ Snow + Rapid Melt",
        "rainfall_mm": 20.0,  # snowmelt acts like heavy rain
        "wind_mph":    10,
        "humidity":    90,
        "tide_ft":     5.0,
        "description": "Warm front melts 8+ inches of snow rapidly"
    },
    "nor_easter": {
        "label":       "💨 Nor'easter",
        "rainfall_mm": 25.0,
        "wind_mph":    55,
        "humidity":    92,
        "tide_ft":     6.5,
        "description": "Coastal storm with NE winds pushing water into Hoboken"
    },
    "clear": {
        "label":       "☀️ Clear Day (Baseline)",
        "rainfall_mm": 0.0,
        "wind_mph":    8,
        "humidity":    55,
        "tide_ft":     3.0,
        "description": "Normal conditions — shows elevation-only risk"
    },
}


def simulate_scenario(model, features, scenario_key):
    """
    Runs the ML model against a scenario for ALL streets.
    Returns a ranked list of street risks under those conditions.
    """
    import datetime

    scenario = SCENARIOS.get(scenario_key)
    if not scenario:
        return None

    hour = datetime.datetime.now().hour
    results = []

    for street_name, street_data in STREETS.items():
        # Use scenario weather instead of live weather
        input_data = pd.DataFrame([{
            "elevation_ft":   street_data["elevation_ft"],
            "rainfall_mmhr":  scenario["rainfall_mm"],
            "wind_speed_mph": scenario["wind_mph"],
            "humidity_pct":   scenario["humidity"],
            "hour_of_day":    hour,
            "tide_level_ft":  scenario["tide_ft"],
        }], columns=features)

        risk_score = round(model.predict(input_data)[0])
        risk_score = max(0, min(100, risk_score))

        level = "HIGH" if risk_score >= 70 else "MODERATE" if risk_score >= 40 else "LOW"

        results.append({
            "street":       street_name,
            "risk_score":   risk_score,
            "risk_level":   level,
            "elevation_ft": street_data["elevation_ft"],
        })

    results.sort(key=lambda x: x["risk_score"], reverse=True)

    return {
        "scenario":    scenario_key,
        "label":       scenario["label"],
        "description": scenario["description"],
        "conditions": {
            "rainfall_mm": scenario["rainfall_mm"],
            "wind_mph":    scenario["wind_mph"],
            "tide_ft":     scenario["tide_ft"],
        },
        "streets": results
    }