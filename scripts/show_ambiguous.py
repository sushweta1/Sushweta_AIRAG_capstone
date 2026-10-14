import json

with open("data/pairwise-001-results.json", encoding="utf-8") as f:
    data = json.load(f)

for row in data["results"]:
    if row["overall_winner"] == "ambiguous":
        print("\n" + "=" * 60)
        print(row["id"], "-", row["question"])
        print("Forward:", row["forward"]["winner"])
        print(row["forward"]["reasoning"])
        print("Reverse:", row["reverse"]["winner"])
        print(row["reverse"]["reasoning"])