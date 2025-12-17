from flask import Flask, jsonify, request
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

BASE_URL = "http://p.onlineradiobox.com"
SEARCH_URL = "https://onlineradiobox.com/search"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
}


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


def search_radios_online(query, country="mg"):
    results = []
    try:
        search_params = {"q": query, "c": country}
        response = requests.get(SEARCH_URL, params=search_params, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")
        
        stations = soup.select("li.stations__station")
        
        for station in stations:
            link = station.select_one("a.ajax")
            if link:
                href = link.get("href", "")
                match = re.match(r"^/(\w+)/([^/]+)/?$", href)
                if match:
                    station_country = match.group(1)
                    station_id = match.group(2)
                    
                    img = station.select_one("img.station__title__logo")
                    name_tag = station.select_one("figcaption.station__title__name")
                    
                    name = name_tag.get_text(strip=True) if name_tag else ""
                    image_url = ""
                    if img:
                        image_url = img.get("src", "")
                        if image_url.startswith("//"):
                            image_url = "https:" + image_url
                    
                    results.append({
                        "nom": name,
                        "image_url": image_url,
                        "radio_id": station_id,
                        "country": station_country
                    })
        
    except Exception as e:
        print(f"Erreur recherche: {e}")
    
    return results


def search_radio(query, country="mg"):
    search_results = search_radios_online(query, country)
    
    if search_results:
        first_result = search_results[0]
        info = get_radio_info(first_result["radio_id"], first_result["country"])
        if info:
            return info
    
    info = get_radio_info(query.lower().strip(), country)
    if info and info["nom"]:
        return info
    
    return None


def get_all_radios(query="", country="mg"):
    if query:
        return search_radios_online(query, country)
    
    common_radios = ["rdj", "rnm", "viva", "mbs", "antsiva"]
    radios = []
    for radio_id in common_radios:
        info = get_radio_info(radio_id, country)
        if info:
            radios.append({
                "nom": info["nom"],
                "image_url": info["image_url"],
                "radio_id": radio_id
            })
    return radios


@app.route("/")
def home():
    return jsonify({
        "message": "API Radio Scraper - OnlineRadioBox",
        "routes": {
            "GET /radios": "Liste des radios populaires",
            "GET /radios?q=QUERY": "Recherche des radios par nom",
            "GET /recherche?radio=NOM": "Recherche une radio et retourne nom, image_url, url_stream"
        },
        "exemples": [
            "/recherche?radio=rdj",
            "/recherche?radio=rna",
            "/radios?q=rna"
        ]
    })


@app.route("/radios")
def list_radios():
    query = request.args.get("q", "")
    radios = get_all_radios(query)
    return jsonify({
        "count": len(radios),
        "radios": radios
    })


@app.route("/recherche")
def recherche():
    radio_query = request.args.get("radio", "")
    
    if not radio_query:
        return jsonify({"error": "Paramètre 'radio' requis. Ex: /recherche?radio=rna"}), 400
    
    result = search_radio(radio_query)
    
    if result:
        return jsonify(result)
    else:
        return jsonify({"error": f"Radio '{radio_query}' non trouvée"}), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
