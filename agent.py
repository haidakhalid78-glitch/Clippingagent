import os
import json
import google.generativeai as genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

TARGET_SERVICES = [
    {"company": "Canva", "email": "privacy@canva.com"},
    {"company": "Pinterest", "email": "privacy@pinterest.com"}
]

USER_INFO = {
    "full_name": "Haida Khalid",
    "email": "user@example.com"
}

def generate_request(company, user_name, user_email):
    prompt = f"Rédige une lettre officielle RGPD (Article 17) de suppression de compte pour {company} par {user_name} ({user_email})."
    if not GEMINI_API_KEY:
        return f"Objet: Demande d'effacement RGPD - {company}\n\nMerci de supprimer mes données."
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        return model.generate_content(prompt).text
    except Exception as e:
        return f"Erreur Gemini: {e}"

def main():
    print("=== Démarrage de l'agent Clean Footprint ===")
    results = []
    for item in TARGET_SERVICES:
        print(f"Traitement pour {item['company']}...")
        text = generate_request(item['company'], USER_INFO['full_name'], USER_INFO['email'])
        results.append({"company": item['company'], "email_text": text})
    
    os.makedirs("state", exist_ok=True)
    with open("state/cleaning_report.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("=== Rapport enregistré dans state/cleaning_report.json ===")

if __name__ == "__main__":
    main()
