import json

res = {}
with open("output.json", "r", encoding="utf-8") as f:
    res = json.load(f)

output = {}
for key in res.keys():
    output[key] = []
    for subkey in res[key].keys():
        output[key].extend(res[key][subkey])

with open("output2.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)