# Account Intel Dashboard 🕵️

Dashboard d'**account intelligence** pour équipes commerciales : une revue de
presse par client suivi, limitée aux grands médias reconnus (Reuters, WSJ,
Le Monde, BBC, Le Figaro, CNN...), avec un résumé du jour par entreprise, en
agrégeant **uniquement des données publiques**. Se met à jour
automatiquement, sans intervention manuelle une fois configuré.

## Ce que montre le dashboard

Une page avec un onglet par client suivi, et pour chacun : un résumé du jour
généré à partir des dernières actualités, puis les grands titres — média,
date, extrait, lien vers l'article.

## Fonctionnement

```
clients.json (liste des clients suivis)
      │
      ▼
1. Recherche presse (Tavily)      ── par client, filtrée aux grands médias
2. Rendu HTML statique            ── docs/index.html
3. GitHub Actions (quotidien)     ── régénère et republie automatiquement
```

Python pur, 2 dépendances (`requests`, `python-dotenv`), pas de framework
d'agent. Le dashboard tourne sur GitHub (Actions + Pages) : une fois publié,
personne n'a besoin d'exécuter de code pour le consulter ou pour qu'il reste
à jour.

## Installation (pour développer / tester en local)

```bash
git clone https://github.com/<votre-compte>/account-intel-agent.git
cd account-intel-agent
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

```bash
cp .env.example .env
```

Renseignez dans `.env` :

| Variable | Rôle | Où l'obtenir |
|---|---|---|
| `TAVILY_API_KEY` | Recherche de presse | [tavily.com](https://tavily.com/) (plan gratuit) |
| `DEFAULT_LANG` | *(optionnel)* `fr` ou `en` | défaut : `fr` |
| `CLIENTS_PATH` | *(optionnel)* chemin du fichier de clients | défaut : `clients.json` |

`clients.json` liste les clients suivis (ce fichier est suivi par git — ce
sont juste des noms d'entreprises, pas des données sensibles) :

```json
["Safran", "Sanofi", "Airbus"]
```

`.env` reste ignoré par git ; aucun secret n'est stocké dans le code.

## Utilisation en local

```bash
# Régénère le dashboard pour tous les clients de clients.json
python -m account_intel

# Ajoute durablement un client à clients.json puis régénère
python -m account_intel --add "Danone"

# Inclut ponctuellement une entreprise sans l'enregistrer
python -m account_intel "L'Oréal"
```

Sortie par défaut : `output/dashboard.html` (`open output/dashboard.html`
sur macOS).

## Publication automatique (GitHub Pages + Actions)

Le dashboard publié vit dans `docs/index.html` et se régénère **tout seul**,
sans PC ni intervention : un workflow GitHub Actions
([.github/workflows/refresh-dashboard.yml](.github/workflows/refresh-dashboard.yml))
tourne chaque jour, relance la collecte et republie `docs/index.html` si le
contenu a changé.

Mise en place (une seule fois) :

1. Dans les paramètres du repo GitHub : **Settings → Secrets and variables →
   Actions**, ajoutez un secret `TAVILY_API_KEY` avec votre clé Tavily.
2. **Settings → Pages** : Source = branche `main`, dossier `/docs`.
3. C'est tout. Le lien obtenu (`https://<compte>.github.io/<repo>/`)
   affiche désormais un dashboard qui se rafraîchit chaque jour tout seul —
   à partager tel quel, aucune action requise de la personne qui le
   consulte.

Pour ajouter/retirer un client suivi : éditez `clients.json` sur GitHub (pas
besoin de repasser en local), le prochain passage du workflow régénère le
dashboard avec la nouvelle liste.

## Respect des sources

- ✅ API de recherche officielle (Tavily), limitée à une liste de grands
  médias reconnus (voir `MAJOR_NEWS_DOMAINS` dans
  [account_intel/search.py](account_intel/search.py))
- ✅ Chaque article pointe vers sa source d'origine
- ❌ Pas de scraping de LinkedIn ni d'aucune plateforme l'interdisant dans
  ses CGU

## Limites connues

- La couverture dépend de l'empreinte d'un client dans les grands médias
  suivis : une entreprise peu couverte par la presse généraliste peut
  afficher « aucun article trouvé » — c'est volontaire (mieux vaut rien
  qu'un résultat hors sujet).
- Risque d'homonymie sur les noms ambigus : précisez si besoin (ex.
  `"Mistral AI"` plutôt que `"Mistral"`, `"TotalEnergies"` plutôt que
  `"Total"`).
- Le résumé du jour est généré par l'API de recherche (Tavily), pas par un
  LLM dédié : pas de déduplication poussée, et il peut occasionnellement
  sortir en anglais même pour une recherche en français.
- Habillage visuel inspiré des couleurs de Cisco Blue à titre de projet de
  stage personnel ; ce n'est pas un produit officiel Cisco.

## Licence

[MIT](LICENSE)
