#!/usr/bin/env python3
"""
Découpe automatique des clips — étape locale (0 dirham)
========================================================
Une fois que agent.py a proposé des clips AVEC de vrais timecodes
(transcript source horodaté, format [MM:SS] ou [HH:MM:SS]), ce script
découpe automatiquement le fichier vidéo source en clips séparés,
grâce à ffmpeg.

Pourquoi c'est un script à part, lancé en local :
- Le fichier vidéo source (podcast, interview, brief sponsor...) est
  souvent trop lourd/trop sensible pour vivre dans un repo GitHub.
- ffmpeg doit avoir accès au fichier vidéo réel sur ton disque.
- C'est la seule étape qui nécessite "ton clic" (fournir le fichier),
  comme convenu — tout le reste (repérage des clips, titres, hooks,
  hashtags) est déjà fait automatiquement par agent.py.

Prérequis (0 dirham) :
  - ffmpeg installé sur ta machine (gratuit) : https://ffmpeg.org/download.html
  - Python 3 (déjà nécessaire pour agent.py)

Usage :
  python cut_clips.py <video_source.mp4> <output/clips-XXXXXXXX-XXXXXX.json>

Résultat :
  output/clips/<nom_video>-clip1-<titre-slug>.mp4
  output/clips/<nom_video>-clip2-<titre-slug>.mp4
  ...
  (uniquement pour les clips qui ont un vrai timecode début/fin —
   les autres sont listés en fin d'exécution pour découpe manuelle)
"""

import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

CLIPS_DIR = Path("output/clips")


def timecode_to_seconds(tc: str) -> float:
    parts = [float(p) for p in tc.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0.0)
    h, m, s = parts
    return h * 3600 + m * 60 + s


def slugify(text: str, max_len: int = 40) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text[:max_len] or "clip"


def check_ffmpeg() -> None:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("ERREUR : ffmpeg introuvable. Installe-le (gratuit) : https://ffmpeg.org/download.html")
        sys.exit(1)


def cut_clip(video_path: Path, start_s: float, end_s: float, out_path: Path) -> bool:
    duration = max(0.5, end_s - start_s)
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{start_s:.2f}",
        "-i", str(video_path),
        "-t", f"{duration:.2f}",
        "-c:v", "libx264", "-c:a", "aac",
        "-movflags", "+faststart",
        str(out_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ✗ Échec du découpage : {result.stderr[-400:]}")
        return False
    return True


def main():
    if len(sys.argv) < 3:
        print("Usage: python cut_clips.py <video_source.mp4> <clips-XXXX.json>")
        sys.exit(1)

    video_path = Path(sys.argv[1])
    json_path = Path(sys.argv[2])

    if not video_path.exists():
        print(f"Vidéo introuvable : {video_path}")
        sys.exit(1)
    if not json_path.exists():
        print(f"Rapport JSON introuvable : {json_path}")
        sys.exit(1)

    check_ffmpeg()
    CLIPS_DIR.mkdir(parents=True, exist_ok=True)

    data = json.loads(json_path.read_text(encoding="utf-8"))
    clips = data.get("clips", [])
    video_stem = slugify(video_path.stem, max_len=30)

    coupes_ok, sans_timecode = 0, []

    for clip in clips:
        debut = clip.get("debut_timecode")
        fin = clip.get("fin_timecode")
        rang = clip.get("rang", "?")
        titre = clip.get("titre_accrocheur", "clip")

        if not debut or not fin:
            sans_timecode.append((rang, titre))
            continue

        start_s = timecode_to_seconds(debut)
        end_s = timecode_to_seconds(fin)
        if end_s <= start_s:
            print(f"  ✗ Clip #{rang} : timecodes incohérents ({debut} → {fin}), ignoré.")
            continue

        out_name = f"{video_stem}-clip{rang}-{slugify(titre)}.mp4"
        out_path = CLIPS_DIR / out_name
        print(f"Découpe clip #{rang} ({debut} → {fin}) → {out_path}")
        if cut_clip(video_path, start_s, end_s, out_path):
            coupes_ok += 1
            print(f"  ✓ {out_path}")

    print(f"\n{coupes_ok}/{len(clips)} clips découpés automatiquement dans {CLIPS_DIR}/")
    if sans_timecode:
        print("\nClips SANS timecode réel (transcript source non horodaté) — à découper toi-même :")
        for rang, titre in sans_timecode:
            print(f"  - #{rang} : {titre}")
        print("Astuce : fournis un transcript avec des lignes [MM:SS] pour que ces clips")
        print("soient découpés automatiquement la prochaine fois.")


if __name__ == "__main__":
    main()
