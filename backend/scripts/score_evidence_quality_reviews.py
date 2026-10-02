"""Import human forms while retaining provenance, null metrics and disagreements."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.evidence_quality_reviews import import_reviews, json_bytes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packets', type=Path, required=True, help='The reviewer packet directory')
    parser.add_argument('--reviews', type=Path, required=True, help='Completed or blank JSONL forms')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('output already exists; preserve previous review imports')
    forms = [json.loads(line) for line in args.reviews.read_text().splitlines() if line.strip()]
    result = import_reviews(args.packets, forms)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(json_bytes(result))
    print(json.dumps({key: result[key] for key in ('status', 'review_rows', 'pending_forms', 'disagreements')}))


if __name__ == '__main__':
    main()
