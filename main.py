from flask import Flask, jsonify, request
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

BASE_URL = "https://mytuner-radio.com/fr/radio/pays/madagascar-stations"
RADIO_BROWSER_API = "https://de1.api.radio-browser.info/json/stations"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def get_all_radios():
    radios = []
    try:
        response = requests.get(BASE_URL, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")
        
        radio_list = soup.select("div.radio-list ul li a")
        
        for item in radio_list:
            href = item.get("href", "")
            img_tag = item.select_one("img")
            
            nom = ""
            image_url = ""
            
            if img_tag:
                nom = img_tag.get("alt", "").strip()
                image_url = img_tag.get("data-src") or img_tag.get("src", "")
            
            if not nom:
                text_content = item.get_text(strip=True)
                if text_content:
                    nom = text_content
            
            if nom and not nom.startswith("http"):
                radio_url = href if href.startswith("http") else "https://mytuner-radio.com" + href
                radios.append({
                    "nom": nom,
                    "image_url": image_url,
                    "url_page": radio_url
                })
        
    except Exception as e:
        print(f"Erreur lors du scraping: {e}")
    
    return radios


def search_mytuner(query):
    radios = []
    try:
        search_url = f"https://mytuner-radio.com/fr/cherche/?q={query}"
        response = requests.get(search_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")
        
        radio_list = soup.select("div.radio-list ul li a")
        
        for item in radio_list:
            href = item.get("href", "")
            img_tag = item.select_one("img")
            
            nom = ""
            image_url = ""
            
            if img_tag:
                nom = img_tag.get("alt", "").strip()
                image_url = img_tag.get("data-src") or img_tag.get("src", "")
            
            if not nom:
                text_content = item.get_text(strip=True)
                if text_content:
                    nom = text_content
            
            if nom and not nom.startswith("http"):
                radio_url = href if href.startswith("http") else "https://mytuner-radio.com" + href
                radios.append({
                    "nom": nom,
                    "image_url": image_url,
                    "url_page": radio_url
                })
        
    except Exception as e:
        print(f"Erreur recherche mytuner: {e}")
    
    return radios


def format_stream_url(url):
    if not url:
        return ""
    
    url = url.strip()
    
    if url.endswith("/;"):
        url = url[:-1] + ";"
    elif url.endswith(";"):
        pass
    elif any(url.endswith(ext) for ext in [".mp3", ".aac", ".ogg", ".m3u8"]):
        pass
    elif re.search(r':\d+/?$', url):
        url = url.rstrip("/") + "/;"
    
    return url


def get_stream_from_radio_browser(radio_name):
    try:
        api_url = f"{RADIO_BROWSER_API}/byname/{requests.utils.quote(radio_name)}"
        
        response = requests.get(api_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        stations = response.json()
        
        if stations:
            query_lower = radio_name.lower()
            best_match = None
            for station in stations:
                station_name = station.get("name", "").lower()
                if station_name == query_lower or query_lower in station_name:
                    if station.get("lastcheckok") == 1:
                        url = station.get("url_resolved") or station.get("url", "")
                        if url:
                            return format_stream_url(url), station.get("name", radio_name), station.get("favicon", "")
                    if not best_match:
                        best_match = station
            
            if best_match:
                url = best_match.get("url_resolved") or best_match.get("url", "")
                return (format_stream_url(url),
                        best_match.get("name", radio_name),
                        best_match.get("favicon", ""))
        
    except Exception as e:
        print(f"Erreur API radio-browser: {e}")
    
    return "", "", ""


def search_radio(query):
    mytuner_results = search_mytuner(query)
    query_lower = query.lower()
    
    best_match = None
    for radio in mytuner_results:
        if query_lower in radio["nom"].lower():
            best_match = radio
            break
    
    if not best_match and mytuner_results:
        best_match = mytuner_results[0]
    
    if best_match:
        stream_url, _, _ = get_stream_from_radio_browser(best_match["nom"])
        
        return {
            "nom": best_match["nom"],
            "image_url": best_match["image_url"],
            "url_stream": stream_url
        }
    
    stream_url, name, favicon = get_stream_from_radio_browser(query)
    if stream_url:
        return {
            "nom": name or query,
            "image_url": favicon,
            "url_stream": stream_url
        }
    
    return None


@app.route("/")
def home():
    return jsonify({
        "message": "API Radio Scraper - myTuner Radio",
        "routes": {
            "GET /radios": "Liste toutes les radios (nom, image_url)",
            "GET /recherche?radio=NOM": "Recherche une radio et retourne nom, image_url, url_stream"
        }
    })


@app.route("/radios")
def list_radios():
    radios = get_all_radios()
    result = [{"nom": r["nom"], "image_url": r["image_url"]} for r in radios]
    return jsonify({
        "count": len(result),
        "radios": result
    })


@app.route("/recherche")
def recherche():
    radio_query = request.args.get("radio", "")
    
    if not radio_query:
        return jsonify({"error": "Paramètre 'radio' requis. Ex: /recherche?radio=RFI"}), 400
    
    result = search_radio(radio_query)
    
    if result:
        return jsonify(result)
    else:
        return jsonify({"error": f"Radio '{radio_query}' non trouvée"}), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
