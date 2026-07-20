# Extension LinkedIn (expérimentale, hors CGU) ⚠️ — désactivée pour ce projet

Cette extension est **désactivée par défaut**, et volontairement **non
utilisée** dans ce projet (livrable évalué par un tuteur de stage : le risque
et l'image renvoyée ne se justifient pas pour cette fonctionnalité). Elle
reste documentée et disponible dans le code pour qui voudrait l'activer en
toute connaissance de cause, sur un projet personnel.

## Deux serveurs MCP évalués, deux problèmes différents

**[felipfr/linkedin-mcpserver](https://github.com/felipfr/linkedin-mcpserver)**
(premier essai) : prétend utiliser l'API officielle LinkedIn via OAuth 2.0,
mais avec un type d'authentification (`client_credentials`) que LinkedIn ne
supporte pas pour les applications tierces standard, et des endpoints
(`/search/people`, `/messages`, `/connections`...) réservés à des
partenariats LinkedIn encadrés. **Non fonctionnel en pratique**, quelle que
soit la configuration. Ne propose de toute façon aucun outil pour récupérer
des posts.

**[stickerdaniel/linkedin-mcp-server](https://github.com/stickerdaniel/linkedin-mcp-server)**
(second essai, celui ciblé par le code actuel) : celui-ci **fonctionne
réellement** — il expose `get_person_profile` avec une section `posts`. Mais
il n'utilise pas l'API LinkedIn : il pilote un navigateur Chromium automatisé
(« Patchright », conçu pour échapper à la détection anti-bot) avec la
session LinkedIn personnelle de l'utilisateur (connexion réelle ou cookies
importés d'un navigateur déjà connecté). Cela contrevient à l'article 8.2 du
[LinkedIn User Agreement](https://www.linkedin.com/legal/user-agreement)
(interdiction du scraping et de l'automatisation).

**Conséquences possibles :** suspension ou bannissement du compte LinkedIn
utilisé pour la connexion. Cette extension est fournie « en l'état », sans
garantie, pour un usage personnel et à vos risques.

## Ce que fait (et ne fait pas) ce dépôt

- Ce dépôt **ne contient aucun identifiant LinkedIn** et **n'embarque pas**
  le code du serveur tiers.
- [`account_intel/linkedin_optional.py`](account_intel/linkedin_optional.py)
  cible le tool `get_person_profile` (paramètre `linkedin_username`,
  `sections=posts`) avec un repli générique par découverte dynamique
  (`list_tools`) si le nom ou le schéma diffère selon la version du serveur.
- Ce module n'est appelé que pour les dirigeants ayant un
  `"linkedin_username"` renseigné dans `clients.json`, et seulement si
  `LINKEDIN_MCP_COMMAND` est configuré dans `.env`.

## Installation (à vos risques, hors cadre de ce projet)

1. `pip install -r requirements-linkedin.txt` (nécessite Python 3.10+ — le
   paquet `mcp` ne fonctionne pas sous Python 3.9).
2. Installez [uv](https://docs.astral.sh/uv/getting-started/installation/)
   (fournit `uvx`).
3. Dans votre `.env` :
   ```
   LINKEDIN_MCP_COMMAND=uvx mcp-server-linkedin@latest
   ```
4. Premier lancement : une fenêtre de navigateur s'ouvre pour vous connecter
   à LinkedIn avec votre compte (`uvx mcp-server-linkedin@latest --login`).
   La session est ensuite sauvegardée dans `~/.linkedin-mcp/profile/`.

## Utilisation

Ajoutez l'identifiant LinkedIn (partie après `linkedin.com/in/`, ex.
`williamhgates`) des dirigeants à suivre dans `clients.json` :

```json
[
  {
    "name": "Doctolib",
    "executives": [{ "name": "Jane Doe", "linkedin_username": "janedoe" }]
  }
]
```

Puis lancez normalement :

```bash
python -m account_intel
```

Un avertissement de non-conformité est affiché à chaque exécution qui
appelle effectivement l'extension (clients avec des dirigeants configurés).
Dans le dashboard, la colonne LinkedIn porte systématiquement la mention
« ⚠️ Source non officielle, hors CGU LinkedIn ».

## Alternative recommandée

Pour une couverture des dirigeants sans ce risque, la colonne presse du
dashboard (interviews, communiqués, déclarations relayées) est souvent
suffisante pour documenter priorités et parcours. Pour une couverture
LinkedIn plus systématique et conforme, des fournisseurs sous licence avec
accord commercial LinkedIn existent (ex. Proxycurl, People Data Labs) et
peuvent être branchés de façon similaire dans `dashboard.py`.
