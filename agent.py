#!/usr/bin/env python3
"""
Agent de clipping autonome — 0 dirham
========================================
Ce script :
  1. Lit une source (transcript texte d'une vidéo longue : podcast, interview, live, etc.)
  2. Demande à Claude d'identifier les 5 meilleurs segments "clippables"
     (moments forts, punchlines, révélations, émotion, controverse)
  3. Génère pour chaque segment : titre accrocheur, hook (1ère phrase), 
     description, hashtags, et le timecode approximatif à découper
  4. Sauvegarde tout dans un fichier JSON + un rapport lisible (Markdown)
  5. Garde un historique pour ne jamais proposer deux fois la même vidéo

Coût : 0 dirham si tu restes dans le tier gratuit de l'API Claude
(https://console.anthropic.com -> Plans & Billing -> free tier / credits).
Aucun serveur payant nécessaire : ce script est fait pour tourner
automatiquement via GitHub Actions (voir .github/workflows/run-agent.yml).

CE QUE L'AGENT NE FAIT PAS (et c'est important de le savoir) :
  - Il ne télécharge pas la vidéo lui-même (droits d'auteur / ToS des plateformes)
  - Il ne découpe pas le fichier vidéo (ça demande ffmpeg + le fichier source)
  - Il ne poste pas automatiquement sur Whop/Vyro/FindClout (comptes/API tiers)
  -> Il fait la partie "intelligence" (repérer quoi couper, comment le vendre),
     toi tu gardes le contrôle sur la publication (comme demandé : autonomie
     max, sauf ce qui nécessite littéralement un clic de ta part).
"""

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib import request, error

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-6"
STATE_FILE = Path("state/history.json")
OUTPUT_DIR = Path("output")

TIMECODE_RE = re.compile(r"\[(\d{1,2}:)?\d{1,2}:\d{2}\]")

SYSTEM_PROMPT = """Tu es un expert en clipping viral pour réseaux sociaux \
(TikTok, Reels, Shorts). Ton travail : analyser un transcript de vidéo longue \
et repérer les segments qui ont le plus fort potentiel viral.

Critères de sélection (par ordre d'importance) :
- Punchline ou révélation choc dans les 3 premières secondes du segment
- Émotion forte (surprise, indignation, humour, vulnérabilité)
- Le segment se comprend SEUL, sans contexte de la vidéo entière
- Durée idéale : 20 à 60 secondes de contenu parlé

Si le transcript contient des timecodes au format [MM:SS] ou [HH:MM:SS] \
au début de certaines lignes, utilise-les pour donner le timecode de \
DÉBUT et de FIN réel de chaque clip (les plus proches du passage choisi, \
format identique à celui du transcript, ex "12:34" ou "1:02:34"). \
Si le transcript n'a AUCUN timecode, laisse "debut_timecode" et \
"fin_timecode" à null et remplis seulement "duree_estimee_secondes".

Réponds UNIQUEMENT en JSON valide, aucun texte avant/après, format :
{
  "clips": [
    {
      "rang": 1,
      "extrait_transcript": "citation exacte du passage (max 40 mots)",
      "titre_accrocheur": "titre pour la miniature/description, en français, percutant",
      "hook_premiere_phrase": "la phrase d'accroche à dire/afficher dans les 2 premières secondes",
      "pourquoi_ca_marche": "1 phrase expliquant le potentiel viral",
      "hashtags": ["3 à 5 hashtags pertinents sans le #"],
      "duree_estimee_secondes": 30,
      "debut_timecode": null,
      "fin_timecode": null
    }
  ]
}
"""


def call_claude(transcript: str) -> dict:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERREUR: variable d'environnement ANTHROPIC_API_KEY manquante.")
        print("-> Sur GitHub: Settings > Secrets and variables > Actions > New secret")
        sys.exit(1)

    payload = {
        "model": MODEL,
        "max_tokens": 2000,
        "system": SYSTEM_PROMPT,
        "messages": [
            {
                "role": "user",
                "content": f"Voici le transcript à analyser :\n\n{transcript}",
            }
        ],
    }

    req = request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as e:
        print(f"Erreur API ({e.code}): {e.read().decode('utf-8')}")
        sys.exit(1)

    text_blocks = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
    raw = "\n".join(text_blocks).strip()

    # Nettoyage au cas où le modèle ajoute des balises markdown
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        print("ERREUR: réponse non-JSON reçue :")
        print(raw)
        sys.exit(1)


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def already_processed(history: dict, source_name: str, h: str) -> bool:
    for run in history.get("runs", []):
        if run.get("source") == source_name and run.get("hash") == h:
            return True
    return False


def load_history() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"runs": []}


def save_history(history: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")


def write_report(source_name: str, result: dict) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    json_path = OUTPUT_DIR / f"clips-{ts}.json"
    md_path = OUTPUT_DIR / f"clips-{ts}.md"

    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [f"# Clips proposés — {source_name}", f"_Généré le {ts} UTC_", ""]
    for clip in result.get("clips", []):
        debut = clip.get("debut_timecode")
        fin = clip.get("fin_timecode")
        if debut and fin:
            timecode_line = f"**Timecode réel :** {debut} → {fin}"
        else:
            timecode_line = f"**Durée estimée :** {clip.get('duree_estimee_secondes')}s (pas de timecode — transcript sans horodatage)"
        lines += [
            f"## #{clip.get('rang')} — {clip.get('titre_accrocheur')}",
            f"**Hook :** {clip.get('hook_premiere_phrase')}",
            f"**Extrait :** \"{clip.get('extrait_transcript')}\"",
            f"**Pourquoi ça marche :** {clip.get('pourquoi_ca_marche')}",
            timecode_line,
            f"**Hashtags :** {' '.join('#' + h for h in clip.get('hashtags', []))}",
            "",
            "---",
            "",
        ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path


def main():
    if len(sys.argv) < 2:
        print("Usage: python agent.py <chemin_vers_transcript.txt>")
        sys.exit(1)

    source_path = Path(sys.argv[1])
    if not source_path.exists():
        print(f"Fichier introuvable : {source_path}")
        sys.exit(1)

    transcript = source_path.read_text(encoding="utf-8")
    if len(transcript.strip()) < 50:
        print("Transcript trop court ou vide — rien à analyser.")
        sys.exit(1)

    h = content_hash(transcript)
    history = load_history()
    if already_processed(history, source_path.name, h):
        print(f"{source_path.name} déjà traité (contenu identique) — on saute.")
        return

    has_timecodes = bool(TIMECODE_RE.search(transcript))
    print(f"Analyse de {source_path.name} ({len(transcript)} caractères, timecodes: {'oui' if has_timecodes else 'non'})...")
    result = call_claude(transcript)

    history["runs"].append(
        {
            "source": source_path.name,
            "hash": h,
            "date": datetime.now(timezone.utc).isoformat(),
            "nb_clips": len(result.get("clips", [])),
        }
    )
    save_history(history)

    report_path = write_report(source_path.name, result)
    print(f"OK — {len(result.get('clips', []))} clips proposés.")
    print(f"Rapport : {report_path}")


if __name__ == "__main__":
    main()
