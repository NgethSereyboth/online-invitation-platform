from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
build=json.loads((ROOT/'BUILD_INFO.json').read_text(encoding='utf-8'))
assert int(build['schemaVersion'])>=18
assert build.get('productionPlatformV32') or build.get('selectedRoadmapV34V52') or build.get('version') in {'32.0','0.52'}
for name in ('platform_v32/schema.py','platform_v32/storage.py','platform_v32/jobs.py','platform_v32/service.py','platform_worker_v32.py','platform_scheduler_v32.py','.env.example','docker-compose.production.example.yml'):assert (ROOT/name).is_file(),name
server=(ROOT/'server.py').read_text(encoding='utf-8')
for token in ('/api/health/ready','/api/platform/v32/status','ensure_platform_schema','snapshot_fingerprint','workspace_id'):assert token in server
print('V32_PLATFORM_CONTRACT_TEST_PASSED')
