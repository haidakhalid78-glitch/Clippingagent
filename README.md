# Agent de clipping autonome — 0 dirham

Un agent qui analyse un transcript de vidéo longue et te propose automatiquement
les meilleurs clips à découper (titre, hook, hashtags, timecodes) — pour
alimenter ton activité de clipping (Whop, Vyro, FindClout...).

## Ce que fait l'agent, honnêtement

✅ Automatique et gratuit :
- Repérer les meilleurs passages "clippables" dans un long texte
- Générer titres, hooks, descriptions, hashtags pour chaque clip
- Tourner tout seul 2x/jour via GitHub Actions
- **Ne jamais retraiter deux fois le même transcript** (vérifié par hash de contenu, pas juste par nom de fichier)
- **Découper automatiquement le fichier vidéo** en clips séparés avec ffmpeg — *si* tu fournis un transcript horodaté (voir plus bas)

❌ Pas automatique (nécessite ton clic, comme convenu) :
- Télécharger/fournir la vidéo source (droits d'auteur — c'est à toi de l'avoir légalement, ex. via les campagnes sponsors Whop)
- Fournir un transcript horodaté si tu veux la découpe automatique (sinon, découpe manuelle avec la durée estimée donnée)
- Publier sur les plateformes (comptes/API tiers, à connecter séparément)

## Mise en route (10 minutes, 0 dirham)

1. **Crée un compte GitHub** (gratuit) si tu n'en as pas : github.com
2. **Crée un nouveau repo** (peut être privé) et mets-y tout ce dossier
3. **Récupère une clé API Anthropic** sur console.anthropic.com
   → Anthropic offre des crédits gratuits de démarrage aux nouveaux comptes
4. **Ajoute la clé comme secret GitHub** :
   Repo → Settings → Secrets and variables → Actions → New repository secret
   Nom : `ANTHROPIC_API_KEY`
5. **Ajoute tes transcripts** dans le dossier `sources/` (un fichier `.txt` par vidéo)
6. **Lance-le manuellement une première fois** :
   Onglet "Actions" du repo → "Agent de clipping autonome" → "Run workflow"
7. Après ça, il tourne **tout seul** 2x/jour (8h et 20h UTC) et pousse les
   résultats dans le dossier `output/` de ton repo.

## Où trouver tes résultats

Chaque passage génère deux fichiers dans `output/` :
- `clips-<date>.json` — données structurées (si tu veux les brancher ailleurs)
- `clips-<date>.md` — rapport lisible avec titres, hooks, hashtags prêts à copier

## Pour avoir des timecodes réels (et la découpe 100% automatique)

Par défaut, un transcript brut (sans horodatage) donne seulement une **durée
estimée** par clip — tu dois encore repérer le passage toi-même dans la vidéo.

Si ton transcript contient des timecodes au format `[MM:SS]` ou `[HH:MM:SS]`
au début des lignes, l'agent les utilise pour donner un **timecode de début
et de fin réel** pour chaque clip. Exemple de format attendu :
