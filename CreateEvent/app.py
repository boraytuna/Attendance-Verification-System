from flask import Flask, render_template, request, jsonify
import json
import os

app = Flask(__name__)


# Load professor and class data
def load_data():
    if not os.path.exists("data.json"):
        default_data = {
            "professors": ["Dr. Smith", "Prof. Johnson", "Dr. Brown", "Prof. Davis"],
            "classes": ["Math 101", "Physics 201", "Computer Science 301", "Biology 401"]
        }
        with open("data.json", "w") as file:
            json.dump(default_data, file, indent=4)

    with open("data.json", "r") as file:
        return json.load(file)


# Save event data
def save_event(event_data):
    if not os.path.exists("events.json"):
        with open("events.json", "w") as file:
            json.dump([], file, indent=4)

    with open("events.json", "r") as file:
        events = json.load(file)

    events.append(event_data)

    with open("events.json", "w") as file:
        json.dump(events, file, indent=4)


@app.route("/", methods=["GET"])
def create_event():
    data = load_data()
    return render_template("create_event.html", professors=data["professors"], classes=data["classes"])


@app.route("/submit_event", methods=["POST"])
def submit_event():
    event_data = request.json
    save_event(event_data)
    return jsonify({"message": "Your event has been created!"})


if __name__ == "__main__":
    app.run(debug=True)
