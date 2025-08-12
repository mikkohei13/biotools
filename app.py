from flask import Flask, render_template, request, jsonify
from livereload import Server
import csv
import io

app = Flask(__name__)

@app.route("/heatmap")
def heatmap():
    return render_template("heatmap.html")


@app.post("/api/upload")
def upload_tsv():
    if "file" not in request.files:
        return jsonify({"error": "No file part named 'file'"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    try:
        # Read as text safely from uploaded bytes
        raw_bytes = file.read()
        text = raw_bytes.decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(text), delimiter="\t")

        points = []  # [lat, lon, weight]
        for row in reader:
            try:
                lat_str = (row.get("WGS84 N") or "").strip()
                lon_str = (row.get("WGS84 E") or "").strip()
                if not lat_str or not lon_str:
                    continue
                latitude = float(lat_str)
                longitude = float(lon_str)

                weight_value = 1.0
                count_str = (row.get("Individual count (interpreted)") or "").strip()
                if count_str:
                    try:
                        weight_value = float(count_str)
                    except ValueError:
                        weight_value = 1.0

                points.append([latitude, longitude, weight_value])
            except Exception:
                # Skip problematic rows silently
                continue

        if not points:
            return jsonify({"error": "No valid coordinates found in file"}), 400

        return jsonify({"points": points, "count": len(points)})
    except Exception as exc:
        return jsonify({"error": f"Failed to parse file: {exc}"}), 500

if __name__ == "__main__":
    server = Server(app.wsgi_app)
    server.watch("templates/*.html")
    server.watch("static/*.js")
    server.serve(port=5000, host="0.0.0.0")
