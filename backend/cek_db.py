import os, json
from pymongo import MongoClient

uri = os.environ.get("MONGO_URL")
dbn = os.environ.get("DB_NAME")

if not uri or not dbn:
    print("ERROR: env MONGO_URL or DB_NAME missing")
    exit(1)

client = MongoClient(uri, serverSelectionTimeoutMS=8000)
db = client[dbn]

cols = db.list_collection_names()

print("DB:", dbn)
print("Collections:", cols)

cands = [c for c in cols if any(k in c.lower() for k in ["game","games","catalog","provider","slot"])]
print("Candidates:", cands)

def summarize(d):
    keys = list(d.keys())
    img_like = []
    for k,v in d.items():
        if isinstance(v,str) and ("/assets/" in v or v.endswith((".webp",".png",".jpg",".jpeg"))):
            img_like.append(k)
    return {
        "_id": str(d.get("_id")),
        "keys": keys[:20],
        "img_fields": img_like[:10]
    }

targets = cands[:5] if cands else cols[:5]

for c in targets:
    doc = db[c].find_one()
    if not doc:
        print(f"[{c}] empty")
        continue

    print(f"\n[{c}] sample:")
    print(json.dumps(summarize(doc), indent=2, ensure_ascii=False))
