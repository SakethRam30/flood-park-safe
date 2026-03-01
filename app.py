from flask import Flask, jsonify, request
from flask_cors import CORS
from model import train_model, predict_risk, STREETS

# ─────────────────────────────────────────────
# Flask creates your web server.
# CORS lets your frontend (HTML file) talk to this backend.
# Without CORS, the browser would block the request for security reasons.
# ─────────────────────────────────────────────
app = Flask(__name__)
CORS(app)

# Train the model ONCE when the server starts (not on every request)
print("Training model...")
model, features = train_model()


# ─────────────────────────────────────────────
# API ENDPOINT 1: Get list of available streets
# Frontend calls this to populate the dropdown menu
# URL: GET http://localhost:5000/streets
# ─────────────────────────────────────────────
@app.route("/streets", methods=["GET"])
def get_streets():
    return jsonify(list(STREETS.keys()))


# ─────────────────────────────────────────────
# API ENDPOINT 2: Check risk for a specific street
# Frontend sends the street name, backend returns risk data
# URL: GET http://localhost:5000/risk?street=Observer+Highway
# ─────────────────────────────────────────────
@app.route("/risk", methods=["GET"])
def check_risk():
    street = request.args.get("street")  # reads ?street=... from the URL

    if not street:
        return jsonify({"error": "Street name is required"}), 400

    if street not in STREETS:
        return jsonify({"error": f"Street '{street}' not found"}), 404

    result = predict_risk(model, features, street)
    return jsonify(result)


# ─────────────────────────────────────────────
# API ENDPOINT 3: Get risk for ALL streets at once
# Used to show the full street-by-street comparison table
# URL: GET http://localhost:5000/all-risks
# ─────────────────────────────────────────────
@app.route("/all-risks", methods=["GET"])
def all_risks():
    results = []
    for street in STREETS:
        result = predict_risk(model, features, street)
        if result:
            results.append(result)
    results.sort(key=lambda x: x["risk_score"], reverse=True)  # highest risk first
    return jsonify(results)


# Start the server on port 5000
if __name__ == "__main__":
    app.run(debug=True, port=5000)