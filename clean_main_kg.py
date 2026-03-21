#!/usr/bin/env python3
"""
Pulisce deliberation_kg.ttl usando lo stesso processo di hys_data_10k
1. Identifica statement malformati
2. Rimuove blocchi orfani
3. Valida con RDFLib
"""

import re
import os

print("=== PULIZIA KNOWLEDGE GRAPH PRINCIPALE ===\n")

kg_file = 'knowledge_graph/deliberation_kg.ttl'
output_file = 'knowledge_graph/deliberation_kg_clean.ttl'

print(f"Caricamento {kg_file}...")
with open(kg_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Totale linee: {len(lines):,}")

# FASE 1: Rimuovi blocchi orfani (property lists senza subject)
print("\n[FASE 1] Rimozione blocchi orfani...")

output_lines = []
i = 0
removed_orphans = 0

while i < len(lines):
    if i < len(lines) - 1:
        current = lines[i]
        next_line = lines[i + 1]

        # Check se prossima linea è indentata ma non è subject URI
        is_indented = len(next_line) > 0 and next_line[0] == ' '
        # Controlla sia URI HYS che altri URI
        is_not_subject = not next_line.strip().startswith('<http')

        # Case 1: Linea vuota + contenuto indentato (non subject)
        if current.strip() == '' and is_indented and is_not_subject:
            output_lines.append(current)
            i += 1

            block_start = i
            # Skip tutti i blocchi indentati
            while i < len(lines) and len(lines[i]) > 0 and lines[i][0] == ' ':
                i += 1

            removed_orphans += 1
            if removed_orphans <= 10:  # Mostra solo primi 10
                print(f"  Rimosso blocco orfano alla linea {block_start + 1}")
            continue

        # Case 2: Statement finisce con '.' + linea indentata (non subject)
        if current.rstrip().endswith('.') and is_indented and is_not_subject and next_line.strip() != '':
            output_lines.append(current)
            i += 1

            block_start = i
            # Skip blocco orfano
            while i < len(lines) and len(lines[i]) > 0 and lines[i][0] == ' ' and lines[i].strip() != '':
                i += 1

            removed_orphans += 1
            if removed_orphans <= 10:
                print(f"  Rimosso blocco orfano alla linea {block_start + 1}")
            continue

    output_lines.append(lines[i])
    i += 1

print(f"✓ Rimossi {removed_orphans} blocchi orfani")

# FASE 2: Identifica statement incompleti
print("\n[FASE 2] Identificazione statement incompleti...")

statements = []
current_statement = []
statement_start = 0

for i, line in enumerate(output_lines):
    # Nuovo statement inizia con URI a colonna 0
    if line.startswith('<http://'):
        if current_statement:
            statements.append({
                'start': statement_start,
                'end': i - 1,
                'lines': current_statement
            })
        current_statement = [line]
        statement_start = i
    elif line.startswith('@prefix') or line.startswith('@base'):
        if current_statement:
            statements.append({
                'start': statement_start,
                'end': i - 1,
                'lines': current_statement
            })
            current_statement = []
        statements.append({
            'start': i,
            'end': i,
            'lines': [line]
        })
        statement_start = i + 1
    else:
        current_statement.append(line)

if current_statement:
    statements.append({
        'start': statement_start,
        'end': len(output_lines) - 1,
        'lines': current_statement
    })

print(f"  Trovati {len(statements):,} statement RDF")

# Valida statement
valid_statements = []
invalid_count = 0

for stmt in statements:
    # Prefixes sempre validi
    if stmt['lines'] and (stmt['lines'][0].startswith('@prefix') or stmt['lines'][0].startswith('@base')):
        valid_statements.append(stmt)
        continue

    # Verifica statement completo
    stmt_text = ''.join(stmt['lines'])

    # Statement deve finire con '.'
    if not stmt_text.rstrip().endswith('.'):
        invalid_count += 1
        if invalid_count <= 10:
            print(f"  Invalid statement alla linea {stmt['start']+1}: non termina con '.'")
        continue

    valid_statements.append(stmt)

print(f"✓ Statement validi: {len(valid_statements):,}")
print(f"✓ Statement invalidi rimossi: {invalid_count}")

# FASE 3: Scrivi file pulito
print(f"\n[FASE 3] Scrittura file pulito...")

with open(output_file, 'w', encoding='utf-8') as f:
    for stmt in valid_statements:
        f.writelines(stmt['lines'])

original_size = os.path.getsize(kg_file) / (1024**2)
clean_size = os.path.getsize(output_file) / (1024**2)

print(f"\n✓ File pulito creato: {output_file}")
print(f"  Originale: {original_size:.1f} MB")
print(f"  Pulito: {clean_size:.1f} MB")
print(f"  Rimossi: {original_size - clean_size:.1f} MB")
print(f"  Totale rimozioni: {removed_orphans} blocchi orfani + {invalid_count} statement invalidi")

# FASE 4: Validazione con RDFLib
print(f"\n[FASE 4] Validazione con RDFLib...")
print("  (Questo può richiedere qualche minuto...)")

try:
    from rdflib import Graph
    g = Graph()
    g.parse(output_file, format='turtle')
    print(f"\n✓✓✓ FILE COMPLETAMENTE VALIDO! ✓✓✓")
    print(f"  Contiene {len(g):,} triple RDF")
except Exception as e:
    print(f"\n✗ Errore durante validazione:")
    print(f"  {str(e)[:200]}")
    print("\nIl file potrebbe avere ancora alcuni errori da correggere manualmente.")
