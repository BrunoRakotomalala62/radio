# Radio Scraper API

API Flask pour scraper les radios depuis myTuner Radio et obtenir les URLs de streaming.

## Routes

### GET /
Page d'accueil avec la documentation des routes.

### GET /radios
Liste toutes les radios populaires de myTuner Radio.

**Réponse:**
```json
{
  "count": 50,
  "radios": [
    {"nom": "RFI Monde", "image_url": "https://..."},
    ...
  ]
}
```

### GET /recherche?radio=NOM
Recherche une radio par nom et retourne ses détails avec l'URL du stream.

**Exemple:** `/recherche?radio=RFI`

**Réponse:**
```json
{
  "nom": "RFI Monde",
  "image_url": "https://static2.mytuner.mobi/media/.../rfi-monde.png",
  "url_stream": "http://live02.rfi.fr/rfimonde-64.mp3"
}
```

## Structure

- `main.py` - API Flask avec les endpoints
- `requirements.txt` - Dépendances Python

## Technologies

- Flask pour l'API REST
- BeautifulSoup4 pour le scraping de myTuner Radio
- API radio-browser.info pour obtenir les URLs de streaming
