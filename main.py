from flask import Flask, jsonify, request
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

BASE_URL = "http://p.onlineradiobox.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
}

RADIOS_MADAGASCAR = [
    {"id": "rdj", "country": "mg"},
    {"id": "rnm", "country": "mg"},
    {"id": "rta", "country": "mg"},
    {"id": "viva", "country": "mg"},
    {"id": "mbs", "country": "mg"},
    {"id": "tvm", "country": "mg"},
    {"id": "antsiva", "country": "mg"},
    {"id": "lazan", "country": "mg"},
    {"id": "fm-plus", "country": "mg"},
    {"id": "radiodon", "country": "mg"},
]


def get_radio_info(radio_id, country="mg"):
    try:
        url = f"{BASE_URL}/{country}/{radio_id}/player/?played=1&cs={country}.{radio_id}&os=android"
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")
        
        button = soup.select_one("button#set_radio_button")
        
        if button:
            stream_url = button.get("stream", "")
            radio_name = button.get("radioname", "")
            radio_img = button.get("radioimg", "")
            
            if radio_img and radio_img.startswith("//"):
                radio_img = "https:" + radio_img
            
            return {
                "nom": radio_name,
                "image_url": radio_img,
                "url_stream": stream_url,
                "radio_id": radio_id
            }
        
    except Exception as e:
        print(f"Erreur lors du scraping de {radio_id}: {e}")
    
    return None


def get_all_radios():
    radios = []
    for radio in RADIOS_MADAGASCAR:
        info = get_radio_info(radio["id"], radio["country"])
        if info:
            radios.append({
                "nom": info["nom"],
                "image_url": info["image_url"]
            })
    return radios


def search_radio(query):
    query_lower = query.lower().strip()
    
    for radio in RADIOS_MADAGASCAR:
        if query_lower in radio["id"].lower():
            info = get_radio_info(radio["id"], radio["country"])
            if info:
                return info
    
    info = get_radio_info(query_lower, "mg")
    if info and info["nom"]:
        return info
    
    return None


@app.route("/")
def home():
    return jsonify({
        "message": "API Radio Scraper - OnlineRadioBox Madagascar",
        "routes": {
            "GET /radios": "Liste toutes les radios (nom, image_url)",
            "GET /recherche?radio=NOM": "Recherche une radio et retourne nom, image_url, url_stream"
        },
        "exemple": "/recherche?radio=rdj"
    })


@app.route("/radios")
def list_radios():
    radios = get_all_radios()
    return jsonify({
        "count": len(radios),
        "radios": radios
    })


@app.route("/recherche")
def recherche():
    radio_query = request.args.get("radio", "")
    
    if not radio_query:
        return jsonify({"error": "Paramètre 'radio' requis. Ex: /recherche?radio=rdj"}), 400
    
    result = search_radio(radio_query)
    
    if result:
        return jsonify(result)
    else:
        return jsonify({"error": f"Radio '{radio_query}' non trouvée"}), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
