#!/bin/bash
# Test end-to-end della pipeline HYS-EP
# Esegue tutti gli step su un campione ridotto per verificare il funzionamento

set -e  # Exit on error

echo "================================================================================"
echo "HYS-EP Pipeline - End-to-End Test"
echo "================================================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SAMPLE_SIZE=2000  # Numero feedback per test

echo -e "${BLUE}Step 1: Export Database HYS → CSV${NC}"
echo "Exporting $SAMPLE_SIZE feedback samples..."
python3 scripts/integrate_hys_full.py \
  --db /home/svagnoni/haveyoursay/haveyoursay_full_fixed.db \
  --output /tmp/hys_export \
  --limit-feedback $SAMPLE_SIZE \
  --verbose

echo -e "${GREEN}✓ Step 1 completed${NC}"
echo ""

echo -e "${BLUE}Step 2: Conversione CSV → RDF${NC}"
echo "Converting to RDF with batch processing..."
python3 data/EU_have_your_say/convert_hys_csv_to_del_rdf_batched.py \
  --input-dir /tmp/hys_export \
  --output-dir data/EU_have_your_say \
  --batch-size 500 \
  --verbose

echo -e "${GREEN}✓ Step 2 completed${NC}"
echo ""

echo -e "${BLUE}Step 3: Analisi Rappresentatività${NC}"
mkdir -p results
python3 analysis/representativity_analysis.py \
  --feedback /tmp/hys_export/feedback.csv \
  --initiatives /tmp/hys_export/initiatives.csv \
  --output results/test_representativity.json

echo -e "${GREEN}✓ Step 3 completed${NC}"
echo ""

echo -e "${BLUE}Step 4: Verifica Output${NC}"
echo "Checking generated files..."

# Check RDF files
if [ -f "data/EU_have_your_say/hys_initiatives.ttl" ]; then
    INIT_SIZE=$(du -h data/EU_have_your_say/hys_initiatives.ttl | cut -f1)
    INIT_TRIPLES=$(grep -c "^\s*:" data/EU_have_your_say/hys_initiatives.ttl || true)
    echo "  ✓ hys_initiatives.ttl: $INIT_SIZE (~$INIT_TRIPLES entities)"
else
    echo "  ✗ hys_initiatives.ttl not found"
    exit 1
fi

if [ -f "data/EU_have_your_say/hys_feedback_full.ttl" ]; then
    FB_SIZE=$(du -h data/EU_have_your_say/hys_feedback_full.ttl | cut -f1)
    echo "  ✓ hys_feedback_full.ttl: $FB_SIZE"
else
    echo "  ✗ hys_feedback_full.ttl not found"
    exit 1
fi

# Check analysis results
if [ -f "results/test_representativity.json" ]; then
    echo "  ✓ test_representativity.json created"

    # Extract key metrics
    TOTAL_FB=$(jq '.metadata.total_feedback' results/test_representativity.json)
    UNIQUE_COUNTRIES=$(jq '.geographic_distribution.unique_countries' results/test_representativity.json)
    GINI=$(jq '.concentration_metrics.gini_coefficient' results/test_representativity.json)

    echo ""
    echo "  Key Metrics:"
    echo "    - Total feedback: $TOTAL_FB"
    echo "    - Unique countries: $UNIQUE_COUNTRIES"
    echo "    - Gini coefficient: $GINI"
else
    echo "  ✗ test_representativity.json not found"
    exit 1
fi

echo -e "${GREEN}✓ Step 4 completed${NC}"
echo ""

echo "================================================================================"
echo -e "${GREEN}✅ All tests passed!${NC}"
echo "================================================================================"
echo ""
echo "Generated files:"
echo "  • data/EU_have_your_say/hys_initiatives.ttl"
echo "  • data/EU_have_your_say/hys_feedback_full.ttl"
echo "  • results/test_representativity.json"
echo ""
echo "Next steps:"
echo "  1. Review results: cat results/test_representativity.json | jq ."
echo "  2. Test EUR-Lex linking (requires network access)"
echo "  3. Scale up to full dataset (remove --limit-feedback)"
echo ""
echo "For full documentation, see:"
echo "  • HYS_EP_PIPELINE_README.md"
echo "  • analysis/EXPERIMENT_HYS_EP.md"
echo ""
