from flask import Flask, jsonify, request
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

BASE_URL = "http://p.onlineradiobox.com"
SEARCH_URL = "https://onlineradiobox.com/search"
RADIO_BROWSER_API = "https://de1.api.radio-browser.info/json/stations"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
}


def format_stream_url(url):
    if not url:
        return ""
    
    url = url.strip()
    
    if url.endswith("/;"):
        url = url[:-1] + "stream.mp3"
    elif url.endswith(";"):
        url = url[:-1] + "/stream.mp3"
    elif re.search(r':\d+/?$', url):
        url = url.rstrip("/") + "/stream.mp3"
    
    return url


def normalize_name(name):
    return re.sub(r'[^a-z0-9]', '', name.lower())


def get_radio_info(radio_id, country="mg"):
    try:
        url = f"{BASE_URL}/{country}/{radio_id}/player/?played=1&cs={country}.{radio_id}&os=android"
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")
        
        button = soup.select_one("button#set_radio_button")
        
        if button:
            stream_url = format_stream_url(button.get("stream", ""))
            radio_name = button.get("radioname", "")
            radio_img = button.get("radioimg", "")
            
            if radio_img and radio_img.startswith("//"):
                radio_img = "https:" + radio_img
            
            return {
                "nom": radio_name,
                "image_url": radio_img,
                "url_stream": stream_url,
                "radio_id": radio_id,
                "source": "onlineradiobox"
            }
        
    except Exception as e:
        print(f"Erreur lors du scraping de {radio_id}: {e}")
    
    return None


def fetch_from_radio_browser(country_code="MG"):
    radios = []
    try:
        url = f"{RADIO_BROWSER_API}/bycountrycodeexact/{country_code}"
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        stations = response.json()
        
        for station in stations:
            if station.get("lastcheckok") == 1:
                stream_url = format_stream_url(station.get("url_resolved") or station.get("url", ""))
                favicon = station.get("favicon", "")
                
                radios.append({
                    "nom": station.get("name", ""),
                    "image_url": favicon,
                    "url_stream": stream_url,
                    "radio_id": station.get("stationuuid", ""),
                    "source": "radio-browser"
                })
        
    except Exception as e:
        print(f"Erreur radio-browser: {e}")
    
    return radios


def search_radio_browser(query):
    try:
        url = f"{RADIO_BROWSER_API}/byname/{requests.utils.quote(query)}"
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        stations = response.json()
        
        for station in stations:
            if station.get("countrycode") == "MG" and station.get("lastcheckok") == 1:
                stream_url = format_stream_url(station.get("url_resolved") or station.get("url", ""))
                return {
                    "nom": station.get("name", ""),
                    "image_url": station.get("favicon", ""),
                    "url_stream": stream_url,
                    "radio_id": station.get("stationuuid", ""),
                    "source": "radio-browser"
                }
        
        for station in stations:
            if station.get("lastcheckok") == 1:
                stream_url = format_stream_url(station.get("url_resolved") or station.get("url", ""))
                return {
                    "nom": station.get("name", ""),
                    "image_url": station.get("favicon", ""),
                    "url_stream": stream_url,
                    "radio_id": station.get("stationuuid", ""),
                    "source": "radio-browser"
                }
        
    except Exception as e:
        print(f"Erreur recherche radio-browser: {e}")
    
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
                        "country": station_country,
                        "source": "onlineradiobox"
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
    
    result = search_radio_browser(query)
    if result:
        return result
    
    return None


def fetch_all_radios_from_country(country="mg"):
    radios = []
    existing_names = set()
    
    try:
        url = f"https://onlineradiobox.com/{country}/"
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")
        
        stations = soup.select("li.stations__station")
        
        for station in stations:
            link = station.select_one("a.ajax")
            if link:
                href = link.get("href", "")
                match = re.match(rf"^/{country}/([^/]+)/?$", href)
                if match:
                    station_id = match.group(1)
                    
                    if station_id.startswith("genre/"):
                        continue
                    
                    img = station.select_one("img.station__title__logo")
                    name_tag = station.select_one("figcaption.station__title__name")
                    
                    name = name_tag.get_text(strip=True) if name_tag else ""
                    image_url = ""
                    if img:
                        image_url = img.get("src", "")
                        if image_url.startswith("//"):
                            image_url = "https:" + image_url
                    
                    normalized = normalize_name(name)
                    if normalized and normalized not in existing_names:
                        existing_names.add(normalized)
                        radios.append({
                            "nom": name,
                            "image_url": image_url,
                            "radio_id": station_id,
                            "country": country,
                            "source": "onlineradiobox"
                        })
        
    except Exception as e:
        print(f"Erreur fetch radios onlineradiobox: {e}")
    
    country_code = country.upper()
    radio_browser_radios = fetch_from_radio_browser(country_code)
    
    for radio in radio_browser_radios:
        normalized = normalize_name(radio["nom"])
        if normalized and normalized not in existing_names:
            existing_names.add(normalized)
            radios.append({
                "nom": radio["nom"],
                "image_url": radio["image_url"],
                "radio_id": radio["radio_id"],
                "country": country,
                "source": radio["source"]
            })
    
    return radios


def get_all_radios(query="", country="mg"):
    if query:
        return search_radios_online(query, country)
    
    return fetch_all_radios_from_country(country)


@app.route("/")
def home():
    return jsonify({
        "message": "API Radio Scraper - Madagascar",
        "sources": ["OnlineRadioBox", "Radio-Browser.info"],
        "routes": {
            "GET /radios": "Liste toutes les radios de Madagascar",
            "GET /radios?q=QUERY": "Recherche des radios par nom",
            "GET /recherche?radio=NOM": "Recherche une radio et retourne nom, image_url, url_stream"
        },
        "exemples": [
            "/recherche?radio=rdj",
            "/recherche?radio=don bosco",
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
        return jsonify({"error": "Paramètre 'radio' requis. Ex: /recherche?radio=don bosco"}), 400
    
    result = search_radio(radio_query)
    
    if result:
        return jsonify(result)
    else:
        return jsonify({"error": f"Radio '{radio_query}' non trouvée"}), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
