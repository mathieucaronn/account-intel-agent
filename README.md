# Account Intel Agent 🕵️

Agent d'**account intelligence** pour équipes commerciales : à partir du nom
d'une entreprise, il génère une fiche de synthèse complète pour préparer un
rendez-vous commercial, en agrégeant **uniquement des données publiques**.

## Ce que contient une fiche

- 🏢 **Présentation & enjeux business** — activité, positionnement, enjeux stratégiques
- 👥 **Décideurs clés** — rôle, parcours, priorités apparentes
- 📰 **Actualités récentes exploitables** — levées de fonds, partenariats, nominations, signaux d'achat
- 🎯 **Angles d'approche suggérés** — 3 à 5 ouvertures concrètes, chacune reliée à un fait sourcé

Chaque fait important est **cité avec son URL source** ; les informations
introuvables ou incertaines sont signalées comme telles.

## Fonctionnement

```
nom d'entreprise
      │
      ▼
1. Recherche (Tavily) ── profil · presse (6 mois) · dirigeants
2. Extraction          ── contenu des pages du site officiel
3. Synthèse (Claude)   ── fiche structurée, faits sourcés
4. Rendu               ── fiche .md + .pdf dans output/
```

Python pur, 4 dépendances (`anthropic`, `requests`, `python-dotenv`,
`markdown-pdf`), pas de framework d'agent.

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
```

Puis renseignez dans `.env` :

| Variable | Rôle | Où l'obtenir |
|---|---|---|
| `ANTHROPIC_API_KEY` | Synthèse des fiches (non requise en mode `--no-llm` ou `--backend ollama`) | [console.anthropic.com](https://console.anthropic.com/) |
| `TAVILY_API_KEY` | Recherche web & presse | [tavily.com](https://tavily.com/) (plan gratuit) |
| `ANTHROPIC_MODEL` | *(optionnel)* modèle Claude | défaut : `claude-sonnet-5` |
| `DEFAULT_LANG` | *(optionnel)* `fr` ou `en` | défaut : `fr` |
| `LLM_BACKEND` | *(optionnel)* `anthropic` ou `ollama` | défaut : `anthropic` |
| `OLLAMA_MODEL` / `OLLAMA_BASE_URL` | *(optionnel)* si `LLM_BACKEND=ollama` | défaut : `llama3.1:8b` / `http://localhost:11434` |

Aucun secret n'est stocké dans le code ; `.env` est ignoré par git.

### Synthèse en local avec Ollama (sans clé Anthropic)

1. Installez [Ollama](https://ollama.com/download) (macOS : `.dmg` officiel, pas besoin de Homebrew).
2. Téléchargez un modèle : `ollama pull llama3.1:8b` (~4,7 Go, adapté à partir de 16 Go de RAM).
3. Lancez `python -m account_intel "Sanofi" --backend ollama` (ou `LLM_BACKEND=ollama` dans `.env`).

⚠️ Un modèle local de cette taille suit moins fidèlement que Claude les règles
strictes du prompt (citation systématique des sources, interdiction
d'inventer des faits) — à réserver à des tests, pas à un usage commercial
sans relecture humaine.

## Utilisation

```bash
python -m account_intel "Doctolib"

# Fiche en anglais, sans PDF, dans un dossier spécifique
python -m account_intel "Datadog" --lang en --no-pdf --out fiches/

# Mode dégradé sans synthèse IA (ANTHROPIC_API_KEY non requise) :
# résultats de recherche bruts mis en forme, sans angles d'approche
python -m account_intel "Sanofi" --no-llm
```

Sortie : `output/doctolib-2026-07-15.md` et `output/doctolib-2026-07-15.pdf`.

## Respect des sources

- ❌ Pas de scraping de LinkedIn ni d'aucune plateforme l'interdisant dans ses CGU
- ✅ API de recherche officielle (Tavily), sites d'entreprise et presse librement accessible
- ✅ Les fiches citent systématiquement leurs sources

## Extension optionnelle

Une extension expérimentale et **non conforme aux CGU LinkedIn** existe pour
enrichir les fiches avec des profils de dirigeants (désactivée par défaut,
opt-in explicite requis) : voir [LINKEDIN_MCP.md](LINKEDIN_MCP.md) avant
utilisation.

## Limites connues

- La qualité dépend de l'empreinte publique de l'entreprise (les PME discrètes
  donnent des fiches plus minces — l'agent le signale plutôt que d'inventer).
- Risque d'homonymie : pour les noms ambigus, précisez (ex. `"Mistral AI"`
  plutôt que `"Mistral"`).
- Les données sont un instantané à la date de génération, indiquée en tête de fiche.

## Licence

[MIT](LICENSE)
