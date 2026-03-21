#!/usr/bin/env python3
"""Find top 100 initiatives by feedback count"""

import sqlite3
from collections import Counter

db_path = '/home/svagnoni/haveyoursay/haveyoursay_full_fixed.db'
conn = sqlite3.connect(db_path)

print("Counting feedbacks per publication...")
pub_counts = Counter()
for pub_id, in conn.execute('SELECT publication_id FROM feedback'):
    pub_counts[pub_id] += 1

print(f"Found {len(pub_counts)} publications with feedbacks")

print("\nMapping publications to initiatives...")
pub_to_init = {}
for init_id, init_data in conn.execute('SELECT id, data FROM initiatives'):
    import json
    data = json.loads(init_data)
    for pub in data.get('publications', []):
        if pub.get('id'):
            pub_to_init[pub['id']] = init_id

print(f"Mapped {len(pub_to_init)} publications")

print("\nAggregating feedback counts by initiative...")
init_counts = Counter()
for pub_id, count in pub_counts.items():
    init_id = pub_to_init.get(pub_id)
    if init_id:
        init_counts[init_id] += count

top100 = init_counts.most_common(100)
print(f"\nTop 100 initiatives:")
print(f"  Total feedbacks: {sum(count for _, count in top100):,}")
print(f"  Initiative IDs: {top100[-1][0]} to {top100[0][0]}")
print(f"\nTop 10:")
for init_id, count in top100[:10]:
    print(f"  ID {init_id}: {count:,} feedbacks")

# Save to file
with open('/tmp/top100_init_ids.txt', 'w') as f:
    for init_id, count in top100:
        f.write(f"{init_id}\n")

print("\n✓ Saved IDs to /tmp/top100_init_ids.txt")
conn.close()
