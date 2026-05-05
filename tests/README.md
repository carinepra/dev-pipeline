# Tests

Testes automatizados para `onze-dev-pipeline`.

## Quick Start

```bash
# Install dependencies
make install-dev

# Run all tests
make test

# Run with coverage
make test-cov
```

## Test Categories

### Integration Tests (`tests/integration/`)

End-to-end tests for pipeline v2.0 state machines:

- `test_v2_pipelines.py` - StoryPipeline init, TaskPipeline init, persistence list

**Run:**
```bash
pytest tests/integration/ -v
```

## Fixtures

### `env_setup` (session-scoped, autouse)

Sets test environment variables (Jira credentials, AWS region).
Defined in `tests/conftest.py`.

## Coverage

Current test coverage: Run `make test-cov` to see.

## See Also

- [conftest.py](conftest.py) - Fixture definitions
