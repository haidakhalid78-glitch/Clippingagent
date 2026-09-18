import os
import json
import smtplib
from email.mime.text import MIMEText
import google.generativeai as genai

# ==========================================
# 1. Configuration & Variables d'environnement
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD")

USER_NAME = "Haida Khalid"
USER_EMAIL = SENDER_EMAIL or "utilisateur@example.com"

# Initialisation de l'API Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Serveur SMTP Gmail
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Annuaire des adresses DPO / Privacy
DPO_DIRECTORY = {
    "canva": "privacy@canva.com",
    "pinterest": "privacy-eu@pinterest.com",
    "adobe": "privacy@adobe.com",
    "spotify": "privacy@spotify.com",
    "netflix": "privacy@netflix.com",
    "linkedin": "privacy@linkedin.com",
    "twitter": "privacy@x.com",
    "x": "privacy@x.com"
}

# ==========================================
# 2. Fonctions Utilitaires
# ==========================================
def resolve_dpo_email(company_name):
    """Trouve automatiquement l'adresse DPO d'un service"""
    key = company_name.strip().lower()
    if key in DPO_DIRECTORY:
        return DPO_DIRECTORY[key]
    return f"privacy@{key.replace(' ', '')}.com"

def generate_rgpd_letter(company, user_name, user_email):
    """Génère la lettre légale via Gemini 2.0 Flash"""
    prompt = (
        f"Rédige une demande officielle d'effacement de données personnelles (Article 17 du RGPD) "
        f"adressée au service {company}. La demande concerne l'utilisateur {user_name} "
        f"dont l'adresse e-mail rattachée au compte est {user_email}. "
        f"Sois formel, précis et mentionne explicitement le droit à l'oubli."
    )

    if not GEMINI_API_KEY:
        return (
            f"Objet: Demande d'effacement de données (Art. 17 RGPD) - {company}\n\n"
            f"Madame, Monsieur,\n\n"
            f"Je vous prie de bien vouloir procéder à la suppression définitive de l'ensemble de mes "
            f"données personnelles associées à l'adresse {user_email}, conformément à l'Article 17 du RGPD.\n\n"
            f"Cordialement,\n{user_name}"
        )

    try:
        # Modèle stable 'gemini-2.0-flash'
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Erreur lors de la génération Gemini pour {company}: {e}")
        return f"Erreur de génération pour {company}: {str(e)}"

def send_email(to_email, subject, body):
    """Expédie le courriel via SMTP Gmail"""
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        return False, "Identifiants SMTP manquants (SENDER_EMAIL / SENDER_PASSWORD)"

    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = SENDER_EMAIL
        msg["To"] = to_email

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, [to_email], msg.as_string())

        return True, "Envoyé 🚀"
    except Exception as e:
        print(f"Erreur d'envoi SMTP à {to_email}: {e}")
        return False, f"Échec d'envoi: {str(e)}"

# ==========================================
# 3. Exécution Principale
# ==========================================
def main():
    target_companies = ["Canva", "Pinterest"]
    cleaning_reports = []

    print("🚀 Démarrage de l'agent d'effacement RGPD...")

    for company in target_companies:
        dpo_email = resolve_dpo_email(company)
        print(f"🔍 Traitement de {company} ({dpo_email})...")

        # 1. Génération de la lettre
        letter = generate_rgpd_letter(company, USER_NAME, USER_EMAIL)

        # 2. Tentative d'envoi SMTP
        if letter.startswith("Erreur de génération"):
            status = "Échec (Erreur IA)"
        else:
            subject = f"Demande d'effacement de données personnelles (Art. 17 RGPD) - {USER_NAME}"
            success, status_msg = send_email(dpo_email, subject, letter)
            status = status_msg if success else f"Généré (Non envoyé : {status_msg})"

        cleaning_reports.append({
            "company": company,
            "email": dpo_email,
            "status": status,
            "letter": letter
        })

    # 3. Sauvegarde du rapport dans state/cleaning_report.json
    os.makedirs("state", exist_ok=True)
    report_path = os.path.join("state", "cleaning_report.json")
    
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(cleaning_reports, f, ensure_ascii=False, indent=2)

    print(f"=== Rapport mis à jour avec succès dans {report_path} ===")

if __name__ == "__main__":
    main()
