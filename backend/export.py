"""Export a reviewable internal demo bundle; not an approved UI API."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from backend.service import MissionService
from integration.adapters import utc


def export_bundle(service, *, limit=100):
    """Return JSON-safe current view and bounded history from one local service.

    This is a review artifact, not an atomic snapshot under concurrent writers.
    Producer outputs inside saved multimodal reports remain unchanged. Use only
    synthetic demo data; notes/reviewer names are included in the export.
    """
    overview = service.overview()
    run_id = overview['snapshot']['payload'].get('run_id') if overview['snapshot'] else None
    result = {
        'export_version': 'internal-review-v1',
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'analysis_clock': service.clock().isoformat(),
        'overview': overview,
        'crew_profiles': service.crew_profiles(),
        'snapshot_history': service.history(limit=limit, run_id=run_id),
        'mission_logs': service.mission_logs(limit=limit),
        'medical_incidents': service.medical_incidents(limit=limit),
        'medical_resources': service.medical_resources(),
        'limitations': [
            'Internal candidate UI handoff; owner agreement is pending.',
            'Telemetry history follows latest run when run_id exists; logs may include older runs.',
            'Profiles may include inactive crew; current roster comes from overview.snapshot.',
            'JSON bundle is static and does not establish live monitoring or safe conditions.',
        ],
    }
    json.dumps(result, allow_nan=False)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--limit', type=int, default=100)
    parser.add_argument('--replay-clock', help='Explicit scenario timestamp; omitted uses real UTC')
    args = parser.parse_args()
    if not args.database.is_file():
        parser.error('Database missing; create the demo first.')
    try:
        clock = utc(args.replay_clock) if args.replay_clock else None
        service = MissionService(args.database, clock=(lambda: clock) if clock is not None else None)
        # Source must already be initialized by the service/demo. Do not mutate it.
        bundle = export_bundle(service, limit=args.limit)
        with args.output.open('x', encoding='utf-8') as stream:
            json.dump(bundle, stream, indent=2, allow_nan=False)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(f'Exported internal demo bundle to {args.output}')


if __name__ == '__main__':
    main()
