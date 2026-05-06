#!/bin/bash
# Full analysis pipeline: 01b → 02 → 03 → 04 → 04b
# Run after 01_bertopic_modeling.py has finished for all cases.

set -e
cd /home/svagnoni/deliberation-knowledge-graph

LOG=/tmp/pipeline_full.log
exec > >(tee -a "$LOG") 2>&1

echo "============================================"
echo "PIPELINE START: $(date)"
echo "============================================"

echo ""
echo ">>> Step 01b: Unified BERTopic (all cases)"
python3 scripts/analysis/01b_unified_topic_model.py

echo ""
echo ">>> Step 02: Topic alignment (all cases)"
python3 scripts/analysis/02_topic_alignment.py

echo ""
echo ">>> Step 03: Stance detection (all cases) — estimated 1-2h"
python3 scripts/analysis/03_stance_detection.py

echo ""
echo ">>> Step 04: DDI calculation"
python3 scripts/analysis/04_calculate_ddi.py

echo ""
echo ">>> Step 04b: Graph metrics (CPBR, MPET, CPBC, r_BC)"
python3 scripts/analysis/04b_graph_metrics.py

echo ""
echo "============================================"
echo "PIPELINE COMPLETE: $(date)"
echo "============================================"
