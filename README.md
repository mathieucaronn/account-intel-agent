# Account Intel Dashboard 🕵️

Dashboard d'**account intelligence** pour équipes commerciales : une revue de
presse et de posts LinkedIn par client suivi, pour préparer des conversations
sans rester scotché aux alertes Google, en agrégeant **uniquement des données
publiques**.

## Ce que montre le dashboard

Un fichier HTML statique avec un sélecteur de client en haut (Sanofi,
Dassault Systèmes...) et, pour le client sélectionné, deux colonnes :

- 📰 **Presse récente** (6 derniers mois) — titre, date, extrait, lien source
- 🔗 **LinkedIn des dirigeants suivis** — profil/activité récente *(extension
  optionnelle et non conforme aux CGU LinkedIn, voir plus bas)*

## Fonctionnement

```
clients.json (clients suivis + dirigeants)
      │
      ▼
1. Recherche presse (Tavily)     ── par client
2. LinkedIn (optionnel)          ── par dirigeant configuré
3. Rendu HTML statique           ── output/dashboard.html
```

Python pur, 2 dépendances (`requests`, `python-dotenv`), pas de framework
d'agent ni de serveur web permanent : le dashboard est régénéré à la demande
en relançant la commande, puis s'ouvre comme un simple fichier HTML.

## Installation

```bash
git clone https://github.com/<votre-compte>/account-intel-agent.git
cd account-intel-agent
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

```bash
cp .env.example .env
cp clients.example.json clients.json
```

Renseignez dans `.env` :

| Variable | Rôle | Où l'obtenir |
|---|---|---|
| `TAVILY_API_KEY` | Recherche de presse | [tavily.com](https://tavily.com/) (plan gratuit) |
| `DEFAULT_LANG` | *(optionnel)* `fr` ou `en` | défaut : `fr` |
| `CLIENTS_PATH` | *(optionnel)* chemin du fichier de clients | défaut : `clients.json` |

Puis éditez `clients.json` avec vos clients suivis (ce fichier est ignoré par
git — il peut contenir des noms de clients réels) :

```json
[
  { "name": "Sanofi", "executives": [] },
  { "name": "Dassault Systèmes", "executives": [] }
]
```

`executives` alimente la colonne LinkedIn (extension optionnelle et
désactivée par défaut, voir plus bas) ; laissez `[]` si vous ne suivez que
la presse pour ce client.

Aucun secret n'est stocké dans le code ; `.env` et `clients.json` sont
ignorés par git.

## Utilisation

```bash
# Régénère le dashboard pour tous les clients de clients.json
python -m account_intel

# Ajoute durablement un client à clients.json puis régénère
python -m account_intel --add "Danone"

# Inclut ponctuellement une entreprise sans l'enregistrer
python -m account_intel "L'Oréal"

# Dashboard en anglais, chemin de sortie personnalisé
python -m account_intel --lang en --out dashboards/team.html

# Génère le dashboard, démarre un serveur local et l'ouvre dans le
# navigateur, avec la barre de recherche active (recherche n'importe
# quelle entreprise à la volée sans relancer de commande)
python -m account_intel --serve
```

Sortie par défaut : `output/dashboard.html` — ouvrez-le directement dans un
navigateur (`open output/dashboard.html` sur macOS). Il n'y a pas de
rafraîchissement automatique à chaque visite : relancez la commande quand
vous voulez des données à jour (chaque génération consomme du quota
Tavily).

## Partager un lien fixe (GitHub Pages)

Pour donner un lien à ouvrir sans rien installer (utile pour un manager, un
tuteur de stage...), publiez le dashboard sur GitHub Pages :

```bash
python -m account_intel --out docs/index.html
git add docs/index.html
git commit -m "Mise à jour du dashboard"
git push
```

Puis activez GitHub Pages une fois dans les paramètres du repo (Settings →
Pages → Source : branche `main`, dossier `/docs`). Le lien obtenu
(`https://<votre-compte>.github.io/<repo>/`) affiche une **photo figée** au
moment de la dernière publication, pas des données en temps réel — la barre
de recherche y indiquera qu'elle est indisponible (pas de serveur derrière
une page statique). Répétez ces 3 commandes pour rafraîchir le contenu vu
par la personne qui a le lien.

## Respect des sources

- ❌ Pas de scraping de LinkedIn par défaut, ni d'aucune plateforme l'interdisant dans ses CGU
- ✅ API de recherche officielle (Tavily) et presse librement accessible
- ✅ Chaque article de presse pointe vers sa source

## Extension optionnelle : LinkedIn

Une extension expérimentale et **non conforme aux CGU LinkedIn** existe pour
alimenter la colonne LinkedIn à partir des dirigeants listés dans
`clients.json` (désactivée par défaut, opt-in explicite requis) : voir
[LINKEDIN_MCP.md](LINKEDIN_MCP.md) avant utilisation.

## Limites connues

- La couverture presse dépend de l'empreinte publique du client (les PME
  discrètes remontent moins d'articles).
- Risque d'homonymie sur les noms ambigus : précisez si besoin (ex.
  `"Mistral AI"` plutôt que `"Mistral"`).
- Pas de déduplication ni de synthèse IA : c'est une revue de résultats
  bruts organisés, pas un résumé rédigé — volontairement, pour rester simple
  et éviter les coûts/erreurs d'un LLM sur du contenu non filtré.

## Licence

[MIT](LICENSE)
