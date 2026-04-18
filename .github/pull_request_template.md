## What does this PR do?

<!-- One paragraph describing the change and why. -->

## Type of change

- [ ] New source plugin
- [ ] Bug fix
- [ ] Enhancement to existing source
- [ ] Documentation
- [ ] Other (describe below)

## PR checklist

- [ ] `pytest tests/` passes locally
- [ ] New source plugin: `src/sources/<name>.py` with class named `Source`
- [ ] New source plugin: all 9 required fields returned by `fetch()`
- [ ] New source plugin: `SourceFetchError` raised on failure (not bare exceptions)
- [ ] New source plugin: entry in `config/sources.yaml` (`enabled: false` is fine)
- [ ] New source plugin: `tests/sources/test_<name>.py` with VCR cassette
- [ ] VCR cassette scanned for secrets (`grep -i "api.key\|authorization\|bearer" tests/sources/cassettes/*.yaml`)

## Notes for reviewer

<!-- Anything else the reviewer should know — edge cases, tradeoffs, follow-up work. -->
