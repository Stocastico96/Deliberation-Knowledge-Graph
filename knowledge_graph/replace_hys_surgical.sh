#!/bin/bash
# Surgical replacement of HYS data in main KG

set -e

echo "=========================================="
echo "SURGICAL HYS REPLACEMENT"
echo "=========================================="

KG_CURRENT="deliberation_kg.ttl"
KG_BACKUP="deliberation_kg.ttl.backup_surgical_$(date +%Y%m%d_%H%M%S)"
KG_OUTPUT="deliberation_kg_new.ttl"
HYS_CORRECT="../data/EU_have_your_say/eu_have_your_say_10k_ONTOLOGY_CORRECT.ttl"

# Backup
echo ""
echo "1. Creating backup..."
cp "$KG_CURRENT" "$KG_BACKUP"
echo "   ✓ Backup: $KG_BACKUP"

# Extract prefixes from current KG
echo ""
echo "2. Extracting prefixes from current KG..."
grep "^@prefix" "$KG_CURRENT" > kg_prefixes.tmp
echo "   ✓ Extracted $(wc -l < kg_prefixes.tmp) prefix declarations"

# Remove ALL HYS-related triples (subjects with hys_ in URI)
# This is the KEY: remove complete turtle blocks, not individual lines
echo ""
echo "3. Removing ALL HYS data (this may take a while)..."
echo "   Removing subjects containing 'hys_'..."

# Strategy: use awk to remove complete turtle subject blocks
awk '
BEGIN {
    in_hys_block = 0
    skip_line = 0
}

# Check if line starts a new subject (starts with <)
/^</ {
    # Check if this is an hys subject
    if ($0 ~ /hys_/) {
        in_hys_block = 1
        next
    } else {
        in_hys_block = 0
    }
}

# If we are in an hys block, skip until we find the closing period
{
    if (in_hys_block) {
        # Check if line ends the subject (ends with .)
        if ($0 ~ /\.$/) {
            in_hys_block = 0
        }
        next
    }

    # Also skip any line that references hys_ in predicates or objects
    if ($0 ~ /hys_/) {
        next
    }

    # Print everything else
    print
}
' "$KG_CURRENT" > kg_without_hys.tmp

echo "   ✓ Removed HYS data"
echo "   Original: $(wc -l < $KG_CURRENT) lines"
echo "   Without HYS: $(wc -l < kg_without_hys.tmp) lines"

# Merge: prefixes + non-HYS + HYS-correct
echo ""
echo "4. Merging with correct HYS data..."

# Start with prefixes
cat kg_prefixes.tmp > "$KG_OUTPUT"
echo "" >> "$KG_OUTPUT"

# Add non-HYS data (skip prefixes)
grep -v "^@prefix" kg_without_hys.tmp >> "$KG_OUTPUT"

# Add correct HYS data (skip prefixes from it too)
echo "" >> "$KG_OUTPUT"
echo "# === HYS DATA (ONTOLOGY CORRECT) ===" >> "$KG_OUTPUT"
grep -v "^@prefix" "$HYS_CORRECT" >> "$KG_OUTPUT"

echo "   ✓ Merged"
echo "   Output: $(wc -l < $KG_OUTPUT) lines"

# Cleanup temp files
rm kg_prefixes.tmp kg_without_hys.tmp

# Verify basic structure
echo ""
echo "5. Basic verification..."
echo "   Checking for Publication entities..."
PUB_COUNT=$(grep -c "del:Publication" "$KG_OUTPUT" || true)
echo "   Publications found: $PUB_COUNT (should be 0)"

echo "   Checking for hasPublication predicates..."
HAS_PUB_COUNT=$(grep -c "del:hasPublication" "$KG_OUTPUT" || true)
echo "   hasPublication links: $HAS_PUB_COUNT (should be 0)"

echo "   Checking for hasContribution predicates..."
HAS_CONTRIB_COUNT=$(grep -c "del:hasContribution" "$KG_OUTPUT" || true)
echo "   hasContribution links: $HAS_CONTRIB_COUNT"

# Check file size
echo ""
echo "6. File size comparison:"
echo "   Original: $(ls -lh $KG_CURRENT | awk '{print $5}')"
echo "   New:      $(ls -lh $KG_OUTPUT | awk '{print $5}')"

echo ""
echo "=========================================="
if [ "$PUB_COUNT" -eq 0 ] && [ "$HAS_PUB_COUNT" -eq 0 ]; then
    echo "✅ SUCCESS!"
    echo "=========================================="
    echo ""
    echo "To activate the new KG:"
    echo "  mv $KG_CURRENT ${KG_CURRENT}.old"
    echo "  mv $KG_OUTPUT $KG_CURRENT"
    echo ""
    echo "Backup is at: $KG_BACKUP"
else
    echo "⚠ WARNING: File may still have Publication references"
    echo "=========================================="
fi
