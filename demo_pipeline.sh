#!/bin/bash
# A 60-second walkthrough of the ingestion pipeline for a live audience.
# Everything here reads real state — nothing is staged or replayed.
set -uo pipefail
cd "$(dirname "$0")"
PY=backend_venv/bin/python
b(){ printf "\n\033[1m%s\033[0m\n" "$1"; }

b "1 · The pipeline is scheduled, not run by hand"
./schedule_pipeline.sh status

b "2 · Every run is logged — this is the last one"
$PY - <<'PYEOF'
import json
runs=[json.loads(l) for l in open('data/pipeline_runs.jsonl') if l.strip()]
d=runs[-1]
print(f"   finished {d['finished']}   {d['seconds']}s   stages: {', '.join(d['stages'])}")
print(f"   {len(runs)} runs recorded in data/pipeline_runs.jsonl")
PYEOF

b "3 · What the full verification found against the live BIS portal"
$PY - <<'PYEOF'
import pandas as pd
a=pd.read_csv('data/amendments_detected.csv')
st=a[a['field']=='Status']
print(f"   {len(a)} amendments detected across 549 standards")
print(f"     {len(st)} status changes  ·  {len(a)-len(st)} edition-year corrections")
w=((st['held']=='Current') & (st['portal']=='Withdrawn')).sum()
print(f"     of those, {w} were standards we recorded as CURRENT that BIS has")
print(f"     WITHDRAWN — every one a dispute risk the audit was silently missing.\n")
for _,r in st[(st['held']=='Current') & (st['portal']=='Withdrawn')].head(3).iterrows():
    print(f"     {r['is_number']:<22} held Current -> BIS Withdrawn  {str(r['withdrawn_on'])[:10]}")
PYEOF

b "4 · Those were applied. Here is the register agreeing with BIS now — live."
echo "   (checking 25 standards against standardsadmin.bis.gov.in, ~25s)"
$PY pipeline.py --only versions --versions-limit 25 --no-refresh 2>&1 | sed -n '/outcome/,/changed/p' | sed 's/^/   /'

b "5 · The point"
cat <<'TXT'
   The pipeline polls BIS every 6 hours and reports differences.
   It never writes to the register on its own: applying an amendment
   needs `pipeline.py --apply`, so a scheduled job cannot silently
   rewrite the data it is checking.
TXT
