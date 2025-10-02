import os
import logging
import re
import math
import threading
import time
import requests
from io import BytesIO
from datetime import datetime

import pandas as pd
from flask import Flask, render_template, request, send_file, jsonify
from flask_cors import CORS

# — explicitly base directory for templates/static —
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Initialize Flask app with absolute paths so Jinja always finds your templates
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static')
)

# Enable CORS for frontend-backend communication
CORS(app, origins=['https://carbon-calculator-frontend.vercel.app', 'http://localhost:3000'])

app.logger.setLevel(logging.DEBUG)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctctime)s - %(levelname)s - %(message)s"
)

# Global variables for health monitoring
app_start_time = datetime.now()
health_status = {
    "status": "healthy",
    "uptime": 0,
    "last_check": datetime.now().isoformat(),
    "total_requests": 0
}

# Constants
CARBON_FRACTION = 0.5
CO2E_FACTOR     = 44 / 12  # ≈ 3.6667

# Species metadata (IDs, full names, equations, RSR)
SPECIES_METADATA = [
    {"species_id": "CASEQ", "species_name": "Casuarina equisetifolia",
     "allometric_equation": "EXP(-1.17)*(DBH^2.119)/1000", "rsr": 0.351},
    {"species_id": "SWMAC", "species_name": "Swietenia macrophylla",
     "allometric_equation": "0.048*(DBH^2.68)/1000", "rsr": 0.351},
    {"species_id": "TEGRA", "species_name": "Tectona grandis",
     "allometric_equation": "0.054*(DBH^2.579)/1000", "rsr": 0.351},
    {"species_id": "EURO", "species_name": "Eucalyptus urophylla",
     "allometric_equation": "exp(-0.751)*(DBH^2.016)*(exp(0.517^2/2))/1000", "rsr": 0.351},
    {"species_id": "SANT", "species_name": "Santalum album",
     "allometric_equation":
       "exp(-1.803-0.976*0.2739+0.976*ln(0.752)"
       "+2.673*ln(DBH)-0.0299*(ln(DBH)^2))/1000",
     "rsr": 0.351},
    {"species_id": "NEO", "species_name": "Neolamarckia cadamba",
     "allometric_equation": "0.014*(DBH^2.958)/1000", "rsr": 0.351},
    {"species_id": "PTERO", "species_name": "Pterocarpus indicus",
     "allometric_equation": "0.065*(DBH^2.28)/1000", "rsr": 0.351},
    {"species_id": "FALFA", "species_name": "Falcataria falcata",
     # Aboveground biomass eqn: B = 0.3196 * D^1.9834
     "allometric_equation": "0.3196*(DBH**1.9834)/1000", "rsr": 0.351},
    # Add Acacia mangium
    {"species_id": "ACMAN", "species_name": "Acacia mangium",
     "allometric_equation": "0.1173*(DBH**2.454)/1000", "rsr": 0.351},
]

# DBH lookup tables
DBH_VALUES = {
    "CASEQ": [0,0,0,6.389391911,8.159903223,9.776411409,11.25231201,12.5998354,
              13.83014812,14.95344543,15.97903576,16.9154179,17.77035138,18.55092078,
              19.26359447,19.91427818,20.50836392,21.05077473,21.5460054,21.99815978,
              22.41098473,22.78790123,23.13203266,23.44623075,23.73309918,23.99501513,
              24.23414904,24.45248252,24.65182487,24.83382796,25,25.15171802,25.29023926,
              25.4167116,25.53218309,25.63761061,25.7338678,25.82175231,25.90199244,
              25.97525309,26.04214136],
    "SWMAC": [0,0,0,7.827175326,9.817931271,11.66343205,13.38804225,15.00821858,
              16.5359994,17.98068726,19.34976239,20.64942264,21.88492382,23.06080545,
              24.18104661,25.24917743,26.26836107,27.24145547,28.17106098,29.05955766,
              29.90913507,30.72181639,31.49947817,32.24386678,32.95661213,33.63923939,
              34.29317896,34.91977504,35.52029315,36.0959266,36.64780232,37.17698589,
              37.68448609,38.17125895,38.63821142,39.08620463,39.51605687,39.92854634,
              40.32441355,40.70436369,41.06906862],
    "TEGRA": [0,0,0,5.625737863,7.742335059,9.815361302,11.81674369,13.73078541,
              15.54912214,17.26800565,18.88669559,20.40644433,21.82982668,23.16028297,
              24.40180054,25.55868821,26.63541532,27.63649633,28.56640835,29.42953265,
              30.23011396,30.97223298,31.65978862,32.29648776,32.88584041,33.43115897,
              33.93556056,34.40197147,34.83313327,35.23160987,35.59979544,35.93992261,
              36.25407096,36.54417549,36.81203507,37.05932063,37.28758318,37.49826145,
              37.69268926,37.87210255,38.03764601],
    "EURO":  [0,0,0,8.705157082,10.70957595,12.53993644,14.23146924,15.80708084,
              17.28294782,18.67116698,19.98117225,21.22056047,22.39560528,23.51159352,
              24.57305488,25.58392412,26.54765887,27.46732747,28.34567576,29.18517884,
              29.98808187,30.75643268,31.49210816,32.19683594,32.87221227,33.51971704,
              34.14072641,34.73652358,35.30830801,35.85720335,36.38426438,36.89048303,
              37.3767937,37.84407789,38.29316841,38.72485307,39.13987796,39.53895046,
              39.92274192,40.29189007,40.64700122],
    "SANT":  [0,0,0,3.202132074,4.188917796,5.137959664,6.050701354,6.928531321,
              7.772784914,8.584746407,9.365650948,10.11668644,10.83899536,11.53367648,
              12.20178654,12.84434186,13.46231989,14.05666071,14.62826841,15.17801252,
              15.70672931,16.21522305,16.70426727,17.1746059,17.6269544,18.0620009,
              18.48040718,18.88280971,19.26982064,19.64202866,20,20.34427919,20.67538994,
              20.99383594,21.3001016,21.59465283,21.87793767,22.15038707,22.41241548,
              22.66442148,22.90678844],
    "NEO":   [0,0,0,12.610662,16.42049544,19.89978132,23.05607385,25.90691031,
              28.4740003,30.78039699,32.84902839,34.70191986,36.35979395,37.84188556,
              39.16588336,40.34794554,41.40275898,42.34362257,43.18254268,43.93033324,
              44.59671561,45.19041539,45.71925432,46.19023639,46.60962769,46.98302985,
              47.31544723,47.61134813,47.87472033,48.10912121,48.31772315,48.50335427,
              48.66853511,48.81551156,48.94628436,49.06263556,49.16615211,49.2582471,
              49.3401786,49.41306655,49.47790784],
    "PTERO": [0,0,0,9.294857627,12.01162084,14.55741126,16.94298862,19.17843556,
              21.27320014,23.23613588,25.07553909,26.79918399,28.41435555,29.92788026,
              31.34615502,32.67517416,33.92055475,35.08756038,36.18112338,37.20586569,
              38.16611837,39.06593991,39.9091334,40.69926259,41.43966694,42.13347576,
              42.78362144,43.3928518,43.96374175,44.49870414,45.0,45.46974804,
              45.90993364,46.32241724,46.7089422,47.07114217,47.41054798,47.72859411,
              48.0266248,48.30589966,48.56759904],
    "FALFA": [0.0, 3.5, 6.5, 10.0, 14.5, 19.0, 23.5, 27.5, 31.0, 34.5,
              37.5, 39.0, 40.5, 42.0, 43.5, 45.0, 46.4, 47.8,
              49.2, 50.6, 52.0, 53.3, 54.6, 55.9, 57.2, 58.5, 59.6, 60.7, 61.8, 62.9,
              64.0, 64.9, 65.8, 66.7, 67.6, 68.5, 69.2, 69.9, 70.6, 71.3, 72.0],
    # Acacia mangium DBH values for years 0-10 (11 values)
    "ACMAN": [0.0, 5.05, 10.10, 15.15, 18.06, 20.97, 23.88, 26.79, 29.70, 32.61, 35.52]
}

def calculate_dbh(sid, years):
    arr = DBH_VALUES.get(sid)
    if arr is None:
        raise ValueError(f"Species {sid} not found in DBH data")
    
    max_years = len(arr) - 1  # Maximum years available (0-indexed)
    
    if years > max_years:
        raise ValueError(
            f"DBH data for {sid} only available for {max_years} years. "
            f"Requested {years} years. Plantings beyond year {max_years} not supported."
        )
    
    return [arr[t] for t in range(1, years + 1)]


def evaluate_agb(eq: str, dbh: float) -> float:
    if dbh <= 0:
        return 0.0
    tmp = eq.replace("math.", "")
    tmp = tmp.replace("^", "**")
    tmp = re.sub(r"(?i)\bexp\(", "math.exp(", tmp)
    tmp = re.sub(r"(?i)\bln\(",  "math.log(", tmp)
    return float(eval(tmp, {"__builtins__": None, "math": math}, {"DBH": dbh}))


def get_recs_for_species(sid, sched, yrs):
    df_sp = pd.DataFrame(SPECIES_METADATA).set_index("species_id")
    eq, rsr = df_sp.loc[sid, ["allometric_equation", "rsr"]]
    recs = []
    for start, cnt in sched:
        dur = yrs - start + 1
        try:
            dbh_values = calculate_dbh(sid, dur)
        except ValueError as e:
            # Wrap the error with planting year context
            raise ValueError(
                f"Error for {sid} planted in year {start}: {str(e)}"
            ) from e
            
        for age, dbh in enumerate(dbh_values, 1):
            agb = evaluate_agb(eq, dbh)
            bgb = agb * rsr
            recs.append({
                "project_year": start + age - 1,
                "agb_total": agb * cnt,
                "bgb_total": bgb * cnt
            })
    return recs


def run_multi(schedule, yrs):
    from collections import defaultdict
    by_sp = defaultdict(list)
    for e in schedule:
        by_sp[e["species_id"]].append((e["year"], e["trees"]))
    all_recs = []
    for sid, sched in by_sp.items():
        try:
            all_recs += get_recs_for_species(sid, sched, yrs)
        except ValueError as e:
            # Propagate the error with species context
            raise ValueError(
                f"Error processing {sid}: {str(e)}"
            ) from e
            
    df = (
        pd.DataFrame(all_recs)
        .groupby("project_year")
        .sum()
        .reset_index()
        .sort_values("project_year")
    )
    df["annual_agb"]     = df["agb_total"].diff().fillna(df["agb_total"])
    df["annual_bgb"]     = df["bgb_total"].diff().fillna(df["bgb_total"])
    df["annual_biomass"] = df["annual_agb"] + df["annual_bgb"]
    df["carbon_total"]   = df["annual_biomass"] * CARBON_FRACTION
    df["co2e_total"]     = df["carbon_total"] * CO2E_FACTOR
    df["cumulative_co2e"]= df["co2e_total"].cumsum()
    return df


def self_ping():
    """Self-ping mechanism to keep the service alive"""
    while True:
        try:
            # Get the current URL (works for both local and production)
            base_url = os.environ.get('RENDER_EXTERNAL_URL', 'http://localhost:5001')
            if not base_url.startswith('http'):
                base_url = f'https://{base_url}'
            
            health_url = f"{base_url}/health"
            
            # Ping the health endpoint
            response = requests.get(health_url, timeout=10)
            if response.status_code == 200:
                app.logger.info(f"Self-ping successful: {health_url}")
            else:
                app.logger.warning(f"Self-ping failed with status {response.status_code}")
                
        except Exception as e:
            app.logger.error(f"Self-ping error: {str(e)}")
        
        # Wait 5 minutes (300 seconds)
        time.sleep(300)


def start_self_ping():
    """Start the self-ping thread"""
    ping_thread = threading.Thread(target=self_ping, daemon=True)
    ping_thread.start()
    app.logger.info("Self-ping mechanism started (every 5 minutes)")


@app.route("/")
def index():
    species = pd.DataFrame(SPECIES_METADATA)[["species_id", "species_name"]].to_dict("records")
    return render_template("index.html", species_list=species)


@app.route("/health")
def health():
    """Health check endpoint for monitoring and self-pinging"""
    global health_status
    
    # Update health status
    current_time = datetime.now()
    uptime_seconds = (current_time - app_start_time).total_seconds()
    
    health_status.update({
        "status": "healthy",
        "uptime": round(uptime_seconds, 2),
        "last_check": current_time.isoformat(),
        "timestamp": current_time.isoformat(),
        "version": "1.0.0"
    })
    
    return jsonify(health_status), 200


@app.route("/calculate", methods=["POST"])
def calculate():
    global health_status
    health_status["total_requests"] += 1
    
    data = request.get_json(force=True)
    yrs = int(data["project_years"])
    sched = [
        {"species_id": item["species_id"], "year": int(item["year"]), "trees": int(item["trees"])}
        for item in data["planting_schedule"]
    ]
    
    try:
        df = run_multi(sched, yrs)
    except ValueError as e:
        return jsonify(error=str(e)), 400
        
    avg = float(df["co2e_total"].mean())
    return jsonify(yearly_data=df.to_dict("records"), average_co2e=round(avg, 3))


@app.route("/download_report", methods=["POST"])
def download_report():
    data = request.get_json(force=True)
    yrs = int(data["project_years"])
    sched = [
        {"species_id": item["species_id"], "year": int(item["year"]), "trees": int(item["trees"])}
        for item in data["planting_schedule"]
    ]
    
    try:
        df = run_multi(sched, yrs)
    except ValueError as e:
        return jsonify(error=str(e)), 400

    # DBH by Year sheet
    dbh_rows = []
    for e in sched:
        dur = yrs - e["year"] + 1
        try:
            dbh_values = calculate_dbh(e["species_id"], dur)
        except ValueError as err:
            # Wrap the error with planting year context
            raise ValueError(
                f"Error for {e['species_id']} planted in year {e['year']}: {str(err)}"
            ) from err
            
        for age, dbh in enumerate(dbh_values, 1):
            dbh_rows.append({
                "project_year": e["year"] + age - 1,
                "age": age,
                "species_id": e["species_id"],
                "dbh_cm": dbh
            })
    dbh_df = pd.DataFrame(dbh_rows)

    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Summary", index=False)
        dbh_df.to_excel(writer, sheet_name="DBH by Year", index=False)
    buf.seek(0)

    return send_file(
        buf,
        as_attachment=True,
        download_name="carbon_report.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


if __name__ == "__main__":
    # Start self-ping mechanism
    start_self_ping()
    
    port = int(os.environ.get('PORT', 5001))
    app.run(host="0.0.0.0", port=port, debug=False)