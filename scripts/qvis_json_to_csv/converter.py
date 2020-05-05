# Used to convert implementation transport parameters in JSON to CSV format


import json

INPUT_FILE = "./data.json"
SEPARATOR = ","
json_data = None

with open(INPUT_FILE, "r") as fp:
    json_data = json.load(fp)


# Find all keys
keys = []
filter = ["owner"]

for dataset in json_data:
    for key in dataset:
        if key not in keys and key not in filter:
            keys.append(key)


# Create CSV
output = ""
for key in keys:
    output += key + SEPARATOR
output = output[:-1] + "\n"
for dataset in json_data:
    line = ""
    for key in keys:
        line += str(dataset.get(key, "Not set")) + SEPARATOR
    output += "{}\n".format(line[:-1])

# Let there be data!
with open("./output.csv", "w") as fp:
    fp.write(output)
