"""Deterministic synthetic identities at real Kenyan town reference points."""

import argparse
import hashlib
import json
import random
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).parent
GIVEN = [
    "Mary",
    "Grace",
    "Faith",
    "Mercy",
    "Joy",
    "Esther",
    "Jane",
    "Ruth",
    "Ann",
    "Alice",
    "Sarah",
    "Agnes",
    "Rose",
    "Caroline",
    "Irene",
    "Elizabeth",
    "Peter",
    "John",
    "James",
    "David",
    "Joseph",
    "Daniel",
    "Samuel",
    "George",
    "Michael",
    "Paul",
    "Simon",
    "Stephen",
    "Charles",
    "Francis",
    "Brian",
    "Kevin",
    "Collins",
    "Dennis",
    "Victor",
    "Eric",
    "Kelvin",
    "Emmanuel",
    "Amos",
    "Amina",
    "Fatuma",
    "Halima",
    "Zainab",
    "Hassan",
    "Ali",
    "Ahmed",
    "Yusuf",
    "Abdi",
    "Mohamed",
    "Wanjiku",
    "Wambui",
    "Njeri",
    "Atieno",
    "Achieng",
    "Akoth",
    "Chebet",
    "Jepchirchir",
    "Jepkemboi",
    "Wairimu",
    "Nyambura",
    "Makena",
    "Kawira",
    "Mwende",
    "Mumbua",
    "Nasimiyu",
    "Nekesa",
    "Nafula",
]
FAMILY = [
    "Kamau",
    "Mwangi",
    "Njoroge",
    "Maina",
    "Kariuki",
    "Karanja",
    "Wanjohi",
    "Kimani",
    "Githinji",
    "Odhiambo",
    "Otieno",
    "Ochieng",
    "Omondi",
    "Onyango",
    "Okoth",
    "Ouma",
    "Awuor",
    "Kiptoo",
    "Kipchoge",
    "Kiprotich",
    "Korir",
    "Kiplagat",
    "Cheruiyot",
    "Langat",
    "Rono",
    "Bett",
    "Mutiso",
    "Musyoka",
    "Mwanzia",
    "Muli",
    "Kyalo",
    "Mutua",
    "Muthoka",
    "Mwendwa",
    "Musau",
    "Wekesa",
    "Wafula",
    "Barasa",
    "Wanyonyi",
    "Masinde",
    "Simiyu",
    "Wangila",
    "Naliaka",
    "M'mbijiwe",
    "Mutwiri",
    "Muriithi",
    "Mugambi",
    "Kirimi",
    "Gitonga",
    "Nyaga",
    "Omwenga",
    "Nyabuto",
    "Onyancha",
    "Nyangau",
    "Bosire",
    "Ogeto",
    "Abdi",
    "Hassan",
    "Abdullahi",
    "Mohamed",
    "Omar",
    "Noor",
    "Ibrahim",
    "Jama",
    "Salim",
    "Juma",
    "Bakari",
    "Mwakio",
    "Mwachala",
    "Saitoti",
    "Olekiyia",
]
TYPES = [
    ("Mini Market", "Retail shop"),
    ("Fresh Mart", "Retail shop"),
    ("Café", "Restaurant / café"),
    ("General Store", "Retail shop"),
    ("Wholesale", "Wholesaler"),
    ("Kitchen", "Restaurant / café"),
    ("Guest House", "Hotel"),
]


def generate(count=100000, seed=20260910, distribution="national"):
    if count < 47:
        raise ValueError("At least 47 personas are required for county coverage")
    rng = random.Random(seed)
    locations = json.loads((ROOT / "data/locations.json").read_text())
    counties = sorted({p["county"] for p in locations})
    groups = {c: [p for p in locations if p["county"] == c] for c in counties}
    weights = [
        (69 if c == "Nairobi" else 1)
        if distribution == "hotspot"
        else (
            12
            if c == "Nairobi"
            else 5
            if c in ("Mombasa", "Nakuru", "Kisumu", "Kiambu", "Uasin Gishu")
            else 1
        )
        for c in counties
    ]
    for i in range(count):
        county = counties[i] if i < 47 else rng.choices(counties, weights=weights)[0]
        location = rng.choice(groups[county])
        first = rng.choice(GIVEN)
        last = rng.choice(FAMILY)
        suffix, kind = rng.choice(TYPES)
        yield {
            "index": i,
            "county": county,
            "geoname_id": location["geoname_id"],
            "profile": {
                "businessName": f"{first} {last} {suffix} {i + 1:06d}",
                "owner": f"{first} {last}",
                "phone": f"000{i:09d}",
                "type": kind,
                "city": location["town"],
                "address": f"Synthetic shop {i + 1}, {location['town']} town centre",
                "point": {"lat": location["lat"], "lng": location["lng"]},
            },
        }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--count", type=int, default=100000)
    p.add_argument("--seed", type=int, default=20260910)
    p.add_argument("--distribution", choices=["national", "hotspot"], default="national")
    p.add_argument("--output", type=Path, default=ROOT / "data/merchants.jsonl")
    args = p.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    counts = Counter()
    digest = hashlib.sha256()
    with args.output.open("wb") as f:
        for row in generate(args.count, args.seed, args.distribution):
            data = (json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
            f.write(data)
            digest.update(data)
            counts[row["county"]] += 1
    manifest = {
        "count": args.count,
        "seed": args.seed,
        "distribution": args.distribution,
        "sha256": digest.hexdigest(),
        "counties": dict(sorted(counts.items())),
        "synthetic_identities": True,
        "coordinates": "GeoNames town reference points",
    }
    args.output.with_name("population-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "count": args.count,
                "counties": len(counts),
                "path": str(args.output),
                "sha256": digest.hexdigest(),
            }
        )
    )


if __name__ == "__main__":
    main()
