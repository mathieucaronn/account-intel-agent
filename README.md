# Cisco Manufacturing — Account News 🕵️

Dashboard d'**account intelligence** pour équipes commerciales : une revue de
presse par client suivi, limitée aux grands médias mondiaux reconnus
(France, États-Unis, Royaume-Uni, presse tech de référence), orientée
technologie/IA/réseaux/acquisitions plutôt que pure actualité financière,
avec un résumé du jour et les communiqués officiels de chaque entreprise, en
agrégeant **uniquement des données publiques**. Se met à jour
automatiquement, sans intervention manuelle une fois configuré.

## Ce que montre le dashboard

Une page avec un onglet par client suivi, et pour chacun :
un **résumé du jour** (avec ses sources cliquables), les **grands titres**
datés issus des grands médias — presse française en priorité (Les Echos,
Le Figaro, Le Monde, L'Usine Nouvelle, LeMagIT, ChannelNews...) complétée
par la presse États-Unis/Royaume-Uni/tech de référence — les **communiqués
officiels** de l'entreprise, et ses **publications sur les réseaux sociaux**
publics (LinkedIn, X, YouTube, Instagram, Facebook).

## Fonctionnement

```
clients.json (liste des clients suivis)
      │
      ▼
1. Presse française (Tavily)      ── par client, en priorité
2. Presse internationale (Tavily) ── par client, en complément
3. Communiqués officiels (Tavily) ── par client, sur le site de l'entreprise
4. Réseaux sociaux (Tavily)       ── par client, contenu public déjà indexé
5. Rendu HTML statique            ── docs/index.html
6. GitHub Actions (quotidien)     ── régénère et republie automatiquement
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

Pour un dashboard **entièrement en français ou entièrement en anglais**
(labels, requêtes et sources interrogées) : **Settings → Secrets and
variables → Actions → onglet Variables** (pas Secrets, `DEFAULT_LANG` n'est
pas sensible), ajoutez une variable `DEFAULT_LANG` = `fr` ou `en`. En `fr`,
la presse française reste mélangée aux grands médias internationaux (déjà
demandé) ; en `en`, seuls les médias internationaux sont interrogés.

## Respect des sources

- ✅ API de recherche officielle (Tavily), limitée à une liste de grands
  médias reconnus (voir `FRENCH_NEWS_DOMAINS` / `INTERNATIONAL_NEWS_DOMAINS`
  dans [account_intel/search.py](account_intel/search.py))
- ✅ Chaque article pointe vers sa source d'origine
- ✅ Réseaux sociaux : aucune connexion, aucune automatisation de navigateur
  — uniquement du contenu public déjà indexé par Tavily, comme le ferait
  n'importe quel moteur de recherche
- ❌ Pas de scraping de LinkedIn (au sens automatisation de compte) ni
  d'aucune plateforme l'interdisant dans ses CGU

## Limites connues

- La couverture dépend de l'empreinte d'un client dans les grands médias
  suivis : une entreprise peu couverte par la presse généraliste peut
  afficher « aucun article trouvé » — c'est volontaire (mieux vaut rien
  qu'un résultat hors sujet).
- Pour les filiales au nom composé (ex. « Airbus Defence and Space »), la
  presse écrit rarement le nom complet mot pour mot : le filtre accepte donc
  le nom principal + au moins un mot du nom secondaire, ce qui peut laisser
  passer un article un peu moins ciblé plutôt que de ne rien afficher.
- Risque d'homonymie sur les noms ambigus : précisez si besoin (ex.
  `"Mistral AI"` plutôt que `"Mistral"`, `"TotalEnergies"` plutôt que
  `"Total"`).
- Le résumé du jour est généré par l'API de recherche (Tavily), pas par un
  LLM dédié : pas de vraie synthèse croisée multi-articles, et il peut
  occasionnellement sortir en anglais même pour une recherche en français.
  Passer sur un vrai résumé par IA (Claude) est possible mais ajoute un coût
  et une clé API — non fait par défaut, à activer sciemment.
- Pas de barre de recherche libre sur la page publiée : GitHub Pages ne peut
  exécuter aucun code serveur, et la clé Tavily ne doit jamais être exposée
  côté navigateur. Un vrai correctif existe (petite fonction serverless
  gratuite, ex. Cloudflare Workers) mais nécessite de créer un compte tiers
  — non fait par défaut.
- Habillage visuel inspiré des couleurs et du motif « onde sonore » de
  Cisco (dessiné en CSS, pas le logo déposé) à titre de projet de stage
  personnel ; ce n'est pas un produit officiel Cisco.
- ⚠️ Avec ~21 clients suivis × 4 requêtes chacun (presse FR, presse
  internationale, communiqués officiels, réseaux sociaux), l'automatisation
  quotidienne consomme environ 84 requêtes/jour, soit ~2 500/mois : à
  surveiller de près, un plan Tavily gratuit standard (souvent ~1 000/mois)
  risque d'être dépassé en cours de mois, ce qui ferait échouer le
  rafraîchissement quotidien jusqu'au mois suivant. Si ça arrive : passer à
  un plan Tavily payant, réduire la fréquence du cron dans
  `.github/workflows/refresh-dashboard.yml`, ou réduire le nombre de
  clients suivis.

## Licence

[MIT](LICENSE)
