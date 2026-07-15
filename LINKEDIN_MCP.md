# Extension LinkedIn (expérimentale, hors CGU) ⚠️

Cette extension est **désactivée par défaut** et **volontairement absente**
du pipeline principal (`search.py`, `README.md`). Elle existe pour les
personnes qui, en connaissance de cause, veulent enrichir leurs fiches avec
des données de profils LinkedIn de dirigeants — au prix d'une non-conformité
aux CGU LinkedIn.

## Pourquoi ce n'est pas conforme

Le serveur MCP utilisé en exemple ([felipfr/linkedin-mcpserver](https://github.com/felipfr/linkedin-mcpserver))
propose de la recherche/récupération de profils et de la messagerie. Ces
fonctionnalités ne sont **pas** accessibles via l'API officielle LinkedIn pour
un usage tiers standard (elles nécessitent un partenariat LinkedIn encadré).
Un serveur qui les propose sans un tel partenariat s'appuie très
vraisemblablement sur les **identifiants d'un compte personnel** (cookie de
session) pour automatiser la navigation — ce qui contrevient à l'article 8.2
du [LinkedIn User Agreement](https://www.linkedin.com/legal/user-agreement)
(interdiction du scraping et de l'automatisation).

**Conséquences possibles :** suspension ou bannissement du compte LinkedIn
utilisé, et plus largement non-respect des conditions d'utilisation d'un
service tiers. Cette extension est fournie « en l'état », sans garantie, pour
un usage personnel et à vos risques.

## Ce que fait (et ne fait pas) ce dépôt

- Ce dépôt **ne contient aucun identifiant LinkedIn** et **n'embarque pas** le
  code du serveur `linkedin-mcpserver`.
- [`account_intel/linkedin_optional.py`](account_intel/linkedin_optional.py)
  est un **client MCP générique** : il lance en sous-processus la commande
  que vous configurez, découvre dynamiquement les tools exposés (`list_tools`)
  et choisit heuristiquement celui qui ressemble à une recherche de profil.
  Rien n'est codé en dur sur le protocole propriétaire du serveur tiers.
- Ce module n'est importé et exécuté que si vous passez explicitement
  `--linkedin-person "Nom"` en ligne de commande.

## Installation (à vos risques)

1. Clonez et configurez séparément
   [felipfr/linkedin-mcpserver](https://github.com/felipfr/linkedin-mcpserver)
   selon ses propres instructions. Ses identifiants restent dans **son**
   `.env`, jamais dans celui de ce projet.
2. Dans ce projet :
   ```bash
   pip install -r requirements-linkedin.txt
   ```
3. Dans votre `.env` :
   ```
   LINKEDIN_MCP_COMMAND=node /chemin/vers/linkedin-mcpserver/build/index.js
   ```

## Utilisation

```bash
python -m account_intel "Doctolib" --linkedin-person "Jane Doe"
```

Un avertissement de non-conformité est affiché à chaque exécution utilisant
cette option. Dans la fiche générée, tout fait issu de LinkedIn est marqué
« (source : LinkedIn, non officielle) », sans URL LinkedIn précise.

## Alternative recommandée

Pour une couverture des dirigeants sans ce risque, la recherche presse et
site officiel (`search.py`) capte déjà interviews, communiqués et pages
équipe — souvent suffisant pour documenter priorités et parcours. Pour une
couverture LinkedIn plus systématique et conforme, des fournisseurs sous
licence avec accord commercial LinkedIn existent (ex. Proxycurl, People Data
Labs) et peuvent être branchés de façon similaire.
