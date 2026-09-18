import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import google.generativeai as genai

# Configuration de Gemini
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Configuration SMTP (Envoi d'emails gratuit via Gmail)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD")

# Dictionnaire de recherche d'adresses DPO / Privacy
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

def resolve_dpo_email(company_name):
    """Trouve automatiquement l'adresse DPO d'un service"""
    key = company_name.strip().lower()
    if key in DPO_DIRECTORY:
        return DPO_DIRECTORY[key]
    return f"privacy@{key.replace(' ', '')}.com"

def generate_rgpd_letter(company, user_name, user_email):
    """Génère la lettre légale via Gemini 1.5 Flash"""
    prompt = f"Rédige une demande officielle d'effacement de données personnelles (Article 17 RGPD) destinée à la société {company}. L'expéditeur est {user_name} ({user_email}). Reste formel et concis."
    
    if not GEMINI_API_KEY:
        return f"Objet: Demande d'effacement de données (Art. 17 RGPD) - {company}\n\nMadame, Monsieur,\n\nConformément à l'article 17 du RGPD, je vous demande de supprimer toutes mes données personnelles enregistrées sous l'adresse {user_email}.\n\nCordialement,\n{user_name}"
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        return model.generate_content(prompt).text
    except Exception as e:
        print(f"Erreur Gemini: {e}")
        return f"Erreur de génération pour {company}."

def send_email(to_email, subject, body):
    """Envoie l'e-mail de suppression en réel via SMTP"""
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        print("⚠️ Les identifiants SMTP (SENDER_EMAIL/SENDER_PASSWORD) ne sont pas configurés.")
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"❌ Échec de l'envoi d'email à {to_email}: {e}")
        return False

def main():
    # Informations de test (ou lues depuis un fichier de requête)
    user_name = "Haida Khalid"
    user_email = SENDER_EMAIL or "user@example.com"
    companies_to_clean = ["Canva", "Pinterest"]

    results = []

    for company in companies_to_clean:
        dpo_email = resolve_dpo_email(company)
        print(f"🔍 Service: {company} | Email DPO identifié: {dpo_email}")

        letter_content = generate_rgpd_letter(company, user_name, user_email)
        subject = f"Demande d'effacement de données (Art. 17 RGPD) - {company}"

        sent_status = send_email(dpo_email, subject, letter_content)

        results.append({
            "company": company,
            "email": dpo_email,
            "status": "Envoyé 🚀" if sent_status else "Généré (Non envoyé)",
            "letter": letter_content
        })

    os.makedirs("state", exist_ok=True)
    with open("state/cleaning_report.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("=== Rapport mis à jour dans state/cleaning_report.json ===")

if __name__ == "__main__":
    main()
