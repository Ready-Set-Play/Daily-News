"""
tests/sources/conftest.py

VCR cassette tests use record_mode="new_episodes":
  - No cassette → makes a live HTTP call and records it
  - Cassette exists → replays from cassette (no network)

To record all cassettes for the first time:
  cd <project root>
  source ~/Scripts/daily-brief/.env
  ./test.sh record

After recording, commit the cassette files so CI can run offline.
"""
