import json

output = {}
with open("emoji-test.txt", "r", encoding="utf-8") as f:
    group = ""
    subgroup = ""
    for line in f:
        if line.startswith("# group"):
            # removing from line first "# group: " end putting result to group
            group = line[9:].strip()
            if not group in output.keys():
                output[group] = {}
        elif line.startswith("# subgroup: "):
            # removing from line first "# subgroup: " end putting result to subgroup
            subgroup = line[12:].strip()

            if not subgroup in output[group].keys():
                output[group][subgroup] = []
            output[group][subgroup] = []
        elif line == "\n" or line.startswith("#"):
            continue
        else:
            print(line)
            print(line[78], line[79], end=" ")
            output[group][subgroup].append(line[79])

with open("output.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

