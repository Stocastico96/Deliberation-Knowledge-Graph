#!/usr/bin/env python3
"""
Completely fix hys_data_10k.ttl by removing all malformed blocks
Strategy: Parse line by line, identify complete RDF statements, validate structure
"""

import re

print("Loading and analyzing hys_data_10k.ttl...")

with open('knowledge_graph/hys_data_10k.ttl', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")

# First pass: identify all statement boundaries
statements = []
current_statement = []
statement_start_line = 0

for i, line in enumerate(lines):
    # A new statement starts with <http at column 0
    if line.startswith('<http://data.cogenta.org/deliberation/hys_'):
        # Save previous statement
        if current_statement and len(current_statement) > 0:
            first_line = current_statement[0]
            if first_line.strip():
                subject = first_line.split()[0].strip('<>') if first_line.startswith('<') else 'unknown'
                statements.append({
                    'start_line': statement_start_line,
                    'end_line': i - 1,
                    'lines': current_statement,
                    'subject': subject
                })

        # Start new statement
        current_statement = [line]
        statement_start_line = i

    elif line.startswith('@prefix') or line.startswith('@base'):
        # Prefix/base declarations
        if current_statement:
            statements.append({
                'start_line': statement_start_line,
                'end_line': i - 1,
                'lines': current_statement,
                'subject': 'prefix'
            })
            current_statement = []

        statements.append({
            'start_line': i,
            'end_line': i,
            'lines': [line],
            'subject': 'prefix'
        })
        statement_start_line = i + 1

    else:
        current_statement.append(line)

# Don't forget last statement
if current_statement:
    statements.append({
        'start_line': statement_start_line,
        'end_line': len(lines) - 1,
        'lines': current_statement,
        'subject': current_statement[0].split()[0].strip('<>') if current_statement[0].startswith('<') else 'unknown'
    })

print(f"Found {len(statements)} RDF statements")

# Second pass: validate each statement
valid_statements = []
invalid_count = 0

for stmt in statements:
    # Prefixes are always valid
    if stmt['subject'] == 'prefix':
        valid_statements.append(stmt)
        continue

    # Check if statement is well-formed
    is_valid = True
    reason = ""

    # Get statement text
    stmt_text = ''.join(stmt['lines'])

    # Check 1: Statement should end with '.'
    if not stmt_text.rstrip().endswith('.'):
        is_valid = False
        reason = "doesn't end with '.'"

    # Check 2: Initiative statements should have proper structure
    if 'hys_initiative_' in stmt['subject']:
        # Should have: a del:DeliberationProcess
        if 'a del:DeliberationProcess' not in stmt_text:
            is_valid = False
            reason = "missing 'a del:DeliberationProcess'"

        # Should have: dcterms:title
        if 'dcterms:title' not in stmt_text:
            is_valid = False
            reason = "missing dcterms:title"

    # Check 3: Publication statements should have proper structure
    elif 'hys_publication_' in stmt['subject']:
        # Should have: a del:Publication or similar
        if ' a ' not in stmt_text:
            is_valid = False
            reason = "missing type declaration"

    # Check 4: Feedback statements should have proper structure
    elif 'hys_feedback_' in stmt['subject']:
        # Should have: a deldata:Contribution or similar
        if ' a ' not in stmt_text:
            is_valid = False
            reason = "missing type declaration"

    # Check 5: No orphaned property lists (lines starting with 8 spaces at statement start)
    first_content_line = stmt['lines'][0] if stmt['lines'] else ''
    if first_content_line.startswith('        ') and not first_content_line.strip().startswith('<http://data.cogenta.org/deliberation/hys_'):
        is_valid = False
        reason = "orphaned property list"

    # Check 6: Detect property list without subject (multiple lines starting with spaces)
    if len(stmt['lines']) > 1:
        # Check if first line is indented (orphaned)
        if first_content_line.startswith('        '):
            is_valid = False
            reason = "orphaned multi-line property list"

    if is_valid:
        valid_statements.append(stmt)
    else:
        invalid_count += 1
        print(f"Invalid statement at line {stmt['start_line']+1}: {reason}")
        print(f"  Subject: {stmt['subject'][:80]}")
        print(f"  Preview: {''.join(stmt['lines'][:2])[:100].strip()}...")

print(f"\nValid statements: {len(valid_statements)}")
print(f"Invalid statements removed: {invalid_count}")

# Write corrected file
print("\nWriting corrected file...")

with open('knowledge_graph/hys_data_10k_clean.ttl', 'w', encoding='utf-8') as f:
    for stmt in valid_statements:
        f.writelines(stmt['lines'])

import os
original_size = os.path.getsize('knowledge_graph/hys_data_10k.ttl') / (1024**2)
fixed_size = os.path.getsize('knowledge_graph/hys_data_10k_clean.ttl') / (1024**2)

print(f"\n✓ Corrected file created: hys_data_10k_clean.ttl")
print(f"  Original: {original_size:.2f} MB")
print(f"  Fixed: {fixed_size:.2f} MB")
print(f"  Removed: {original_size - fixed_size:.2f} MB ({invalid_count} statements)")
