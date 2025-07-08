#!/usr/bin/env python3
import os
import subprocess
import sys
import re
import base64
from pathlib import Path

def install_requirements():
    """Installe les dépendances nécessaires"""
    try:
        import PyPDF2
    except ImportError:
        print("Installation de PyPDF2...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "PyPDF2"])
        import PyPDF2
    return PyPDF2

def extract_pin_from_pdf(pdf_path):
    """Extrait le PIN du fichier PDF"""
    PyPDF2 = install_requirements()
    
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            
            # Extraire le texte de toutes les pages
            for page in pdf_reader.pages:
                text += page.extract_text()
            
            # Rechercher le pattern "PIN #1:"
            pin_match = re.search(r'PIN #1:\s*([^\s\n]+)', text, re.IGNORECASE)
            if pin_match:
                return pin_match.group(1).strip()
            
            # Alternative: rechercher d'autres patterns possibles
            pin_patterns = [
                r'PIN\s*#1\s*:\s*([^\s\n]+)',
                r'PIN\s*1\s*:\s*([^\s\n]+)',
                r'PIN:\s*([^\s\n]+)',
                r'Password:\s*([^\s\n]+)',
                r'Code:\s*([^\s\n]+)'
            ]
            
            for pattern in pin_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return match.group(1).strip()
                    
    except Exception as e:
        print(f"Erreur lors de la lecture du PDF {pdf_path}: {e}")
        return None
    
    return None

def run_openssl_command(command):
    """Exécute une commande OpenSSL"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.returncode == 0
    except Exception as e:
        print(f"Erreur lors de l'exécution de la commande: {e}")
        return False

def encode_to_base64(input_file, output_file):
    """Encode un fichier en base64"""
    try:
        with open(input_file, 'rb') as f:
            content = f.read()
        
        encoded_content = base64.b64encode(content).decode('utf-8')
        
        with open(output_file, 'w') as f:
            f.write(encoded_content)
        
        return True
    except Exception as e:
        print(f"Erreur lors de l'encodage en base64: {e}")
        return False

def process_p12_files(input_dir="."):
    """Traite tous les fichiers .p12 dans le dossier"""
    input_path = Path(input_dir)
    
    # Vérifier si OpenSSL est installé
    try:
        subprocess.run(['openssl', 'version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Erreur: OpenSSL n'est pas installé ou n'est pas accessible")
        return
    
    # Chercher tous les fichiers .p12
    p12_files = list(input_path.glob("*.p12"))
    
    if not p12_files:
        print(f"Aucun fichier .p12 trouvé dans {input_dir}")
        return
    
    print(f"Trouvé {len(p12_files)} fichier(s) .p12")
    
    for p12_file in p12_files:
        print(f"\nTraitement de: {p12_file.name}")
        
        # Nom de base du fichier (sans extension)
        base_name = p12_file.stem
        
        # Chercher le fichier PDF correspondant
        pdf_file = input_path / f"{base_name}.pdf"
        
        if not pdf_file.exists():
            print(f"✗ Fichier PDF correspondant introuvable: {pdf_file.name}")
            continue
        
        # Extraire le PIN du PDF
        pin = extract_pin_from_pdf(pdf_file)
        
        if not pin:
            print(f"✗ Impossible d'extraire le PIN du fichier {pdf_file.name}")
            continue
        
        print(f"✓ PIN extrait: {pin}")
        
        # Définir les noms des fichiers de sortie
        key_file = input_path / f"{base_name}-key.pem"
        cert_file = input_path / f"{base_name}-cert.pem"
        key_b64_file = input_path / f"{base_name}-key-b64.txt"
        cert_b64_file = input_path / f"{base_name}-cert-b64.txt"
        
        # Extraire la clé privée sans mot de passe
        key_command = f'openssl pkcs12 -in "{p12_file}" -nocerts -out "{key_file}" -nodes -passin pass:"{pin}"'
        
        if run_openssl_command(key_command):
            print(f"✓ Clé privée extraite: {key_file.name}")
        else:
            print(f"✗ Erreur lors de l'extraction de la clé privée")
            continue
        
        # Extraire le certificat
        cert_command = f'openssl pkcs12 -in "{p12_file}" -nokeys -out "{cert_file}" -passin pass:"{pin}"'
        
        if run_openssl_command(cert_command):
            print(f"✓ Certificat extrait: {cert_file.name}")
        else:
            print(f"✗ Erreur lors de l'extraction du certificat")
            continue
        
        # Encoder la clé privée en base64
        if encode_to_base64(key_file, key_b64_file):
            print(f"✓ Clé privée encodée en base64: {key_b64_file.name}")
        else:
            print(f"✗ Erreur lors de l'encodage de la clé privée en base64")
        
        # Encoder le certificat en base64
        if encode_to_base64(cert_file, cert_b64_file):
            print(f"✓ Certificat encodé en base64: {cert_b64_file.name}")
        else:
            print(f"✗ Erreur lors de l'encodage du certificat en base64")
        
        print("----------------------------------------")
    
    print("Traitement terminé!")

if __name__ == "__main__":
    # Récupérer le dossier depuis les arguments de ligne de commande
    input_directory = sys.argv[1] if len(sys.argv) > 1 else "."
    process_p12_files(input_directory)
