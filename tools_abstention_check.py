import os, sys, pandas as pd
os.chdir('/Users/JayNaik/Desktop/SIH'); sys.path.insert(0,'.')
import retrieval as R, engine

def same(a,b):
    a,b=str(a),str(b)
    if engine._is_base(a).upper()==engine._is_base(b).upper(): return True
    da,db=engine._is_digits(a),engine._is_digits(b)
    return bool(da) and da==db

df=pd.read_csv('data/golden_queries.csv',encoding='utf-8-sig')
rows=[(str(q),str(e)) for q,e in zip(df['query'],df['expected_is'])
      if str(e).strip() and str(e).strip().lower()!='nan']

ce_abstained=[]
for q,e in rows:
    c=R.search(q, pipeline='hybrid_ce')
    if R._gate(c)['decision']=='abstain':
        ce_abstained.append((q,e))
print(f'hybrid_ce abstained on {len(ce_abstained)} of {len(rows)}', flush=True)

right=wrong=also=0
for q,e in ce_abstained:
    c=R.search(q, pipeline='hybrid_rrf')
    if R._gate(c)['decision']=='abstain':
        also+=1; continue
    if c and same(c[0]['is_number'], e): right+=1
    else: wrong+=1
print(f'  of those, hybrid_rrf also abstained : {also}')
print(f'  answered confidently and was RIGHT  : {right}')
print(f'  answered confidently and was WRONG  : {wrong}')

had=sum(1 for q,e in ce_abstained
        if any(same(c['is_number'],e) for c in R.search(q,pipeline='hybrid_ce')[:10]))
print(f'  right answer was in hybrid_ce top 10 anyway: {had}')
