#!/usr/bin/env python3

import os
import base64

def read_file(filepath):
    """Leggi file con encoding utf-8"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"❌ Errore lettura {filepath}: {e}")
        return ""

def read_binary_file(filepath):
    """Leggi file binario e converti in base64"""
    try:
        with open(filepath, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    except Exception as e:
        print(f"❌ Errore lettura {filepath}: {e}")
        return ""

def create_self_contained_html():
    """Crea una versione self-contained di index.html"""

    print("🔧 Creazione frontend self-contained...")

    # Leggi CSS
    css_content = read_file('css/styles.css')

    # Leggi JS
    js_content = read_file('js/main.js')

    # Leggi HTML originale
    html_content = read_file('index.html')

    # Converti immagini in base64
    images = {}
    for img_file in ['DKG daft.png', 'what-is-the-european-parliament.png']:
        if os.path.exists(img_file):
            img_data = read_binary_file(img_file)
            if img_data:
                img_type = 'png' if img_file.endswith('.png') else 'jpeg'
                images[img_file] = f"data:image/{img_type};base64,{img_data}"
                print(f"✅ Immagine {img_file} convertita in base64")
        else:
            print(f"⚠️ Immagine {img_file} non trovata")

    # Sostituisci i link CSS con CSS inline
    html_content = html_content.replace(
        '<link rel="stylesheet" href="css/styles.css">',
        f'<style>\n{css_content}\n</style>'
    )

    # Sostituisci i link JS con JS inline
    html_content = html_content.replace(
        '<script src="js/main.js"></script>',
        f'<script>\n{js_content}\n</script>'
    )

    # Sostituisci i percorsi delle immagini con base64
    for img_file, img_data in images.items():
        html_content = html_content.replace(img_file, img_data)

    # Aggiorna i link API per puntare al backend live
    api_replacements = {
        "'/api/": "'https://svagnoni.linkeddata.es/api/",
        '"/api/': '"https://svagnoni.linkeddata.es/api/',
        "fetch('/api/": "fetch('https://svagnoni.linkeddata.es/api/",
        'fetch("/api/': 'fetch("https://svagnoni.linkeddata.es/api/',
    }

    for old, new in api_replacements.items():
        html_content = html_content.replace(old, new)

    # Scrivi il file self-contained
    with open('index_self_contained.html', 'w', encoding='utf-8') as f:
        f.write(html_content)

    print("✅ Frontend self-contained creato: index_self_contained.html")

    # Crea anche le altre pagine
    for page in ['contributions.html', 'visualize_kg.html', 'sparql.html']:
        if os.path.exists(page):
            page_content = read_file(page)

            # Sostituisci CSS con inline
            page_content = page_content.replace(
                '<link rel="stylesheet" href="css/styles.css">',
                f'<style>\n{css_content}\n</style>'
            )

            # Sostituisci JS con inline se presente
            if 'js/main.js' in page_content:
                page_content = page_content.replace(
                    '<script src="js/main.js"></script>',
                    f'<script>\n{js_content}\n</script>'
                )

            # Aggiorna API links
            for old, new in api_replacements.items():
                page_content = page_content.replace(old, new)

            # Sostituisci immagini
            for img_file, img_data in images.items():
                page_content = page_content.replace(img_file, img_data)

            output_name = page.replace('.html', '_self_contained.html')
            with open(output_name, 'w', encoding='utf-8') as f:
                f.write(page_content)

            print(f"✅ Pagina {page} → {output_name}")

if __name__ == "__main__":
    create_self_contained_html()
    print("\n🎉 Frontend self-contained completato!")
    print("📋 File creati:")
    print("   - index_self_contained.html")
    print("   - contributions_self_contained.html")
    print("   - visualize_kg_self_contained.html")
    print("   - sparql_self_contained.html")