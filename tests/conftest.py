"""Shared fixtures for the Glacier AI test suite."""

from __future__ import annotations

from pathlib import Path
import sys
import types

import pytest

from app.core.cache_config import get_cache_settings
from app.core.config import get_settings


def _install_google_bigquery_test_shim() -> None:
    """Install a minimal BigQuery shim when the package is unavailable."""

    google_module = sys.modules.setdefault("google", types.ModuleType("google"))
    cloud_module = sys.modules.setdefault(
        "google.cloud", types.ModuleType("google.cloud")
    )
    api_core_module = sys.modules.setdefault(
        "google.api_core", types.ModuleType("google.api_core")
    )
    exceptions_module = sys.modules.setdefault(
        "google.api_core.exceptions",
        types.ModuleType("google.api_core.exceptions"),
    )
    bigquery_module = types.ModuleType("google.cloud.bigquery")

    class GoogleAPIError(Exception):
        """Fallback Google API error used in unit tests."""

    class ScalarQueryParameter:
        """Fallback scalar query parameter."""

        def __init__(self, name: str, type_: str, value: object) -> None:
            self.name = name
            self.type_ = type_
            self.value = value

    class ArrayQueryParameter:
        """Fallback array query parameter."""

        def __init__(self, name: str, type_: str, values: list[object]) -> None:
            self.name = name
            self.type_ = type_
            self.values = values

    class QueryJobConfig:
        """Fallback query job config."""

        def __init__(self, query_parameters: list[object] | None = None) -> None:
            self.query_parameters = query_parameters or []

    class Client:
        """Fallback BigQuery client placeholder."""

        def query(self, query: str, job_config: QueryJobConfig | None = None) -> None:
            raise NotImplementedError("BigQuery client shim should be mocked in tests.")

    exceptions_module.GoogleAPIError = GoogleAPIError
    api_core_module.exceptions = exceptions_module
    bigquery_module.ArrayQueryParameter = ArrayQueryParameter
    bigquery_module.Client = Client
    bigquery_module.QueryJobConfig = QueryJobConfig
    bigquery_module.ScalarQueryParameter = ScalarQueryParameter
    cloud_module.bigquery = bigquery_module
    google_module.cloud = cloud_module
    google_module.api_core = api_core_module

    sys.modules["google.cloud.bigquery"] = bigquery_module


def _install_openai_test_shim() -> None:
    """Install a minimal OpenAI shim when the package is unavailable."""

    openai_module = types.ModuleType("openai")

    class _Completions:
        def create(self, *args, **kwargs) -> None:
            raise NotImplementedError("OpenAI client shim should be mocked in tests.")

    class _Chat:
        def __init__(self) -> None:
            self.completions = _Completions()

    class OpenAI:
        def __init__(self, *args, **kwargs) -> None:
            self.chat = _Chat()

    openai_module.OpenAI = OpenAI
    sys.modules["openai"] = openai_module


def _install_langgraph_test_shim() -> None:
    """Install a minimal LangGraph shim when the package is unavailable."""

    langgraph_module = types.ModuleType("langgraph")
    graph_module = types.ModuleType("langgraph.graph")
    start_token = "__start__"
    end_token = "__end__"

    class CompiledGraph:
        def __init__(self, nodes: dict, edges: dict, conditional_edges: dict) -> None:
            self._nodes = nodes
            self._edges = edges
            self._conditional_edges = conditional_edges

        def invoke(self, state: dict) -> dict:
            current = self._edges[start_token]
            current_state = dict(state)

            while current != end_token:
                update = self._nodes[current](current_state)
                if update:
                    current_state.update(update)
                if current in self._conditional_edges:
                    router, mapping = self._conditional_edges[current]
                    current = mapping[router(current_state)]
                else:
                    current = self._edges[current]
            return current_state

    class StateGraph:
        def __init__(self, state_type) -> None:
            self._nodes = {}
            self._edges = {}
            self._conditional_edges = {}

        def add_node(self, name: str, node) -> None:
            self._nodes[name] = node

        def add_edge(self, source: str, target: str) -> None:
            self._edges[source] = target

        def add_conditional_edges(self, source: str, router, mapping: dict) -> None:
            self._conditional_edges[source] = (router, mapping)

        def compile(self) -> CompiledGraph:
            return CompiledGraph(self._nodes, self._edges, self._conditional_edges)

    graph_module.END = end_token
    graph_module.START = start_token
    graph_module.StateGraph = StateGraph
    langgraph_module.graph = graph_module
    sys.modules["langgraph"] = langgraph_module
    sys.modules["langgraph.graph"] = graph_module


try:
    from google.cloud import bigquery as _bigquery  # noqa: F401
except ImportError:
    _install_google_bigquery_test_shim()

try:
    from openai import OpenAI as _openai  # noqa: F401
except ImportError:
    _install_openai_test_shim()

try:
    from langgraph.graph import StateGraph as _state_graph  # noqa: F401
except ImportError:
    _install_langgraph_test_shim()


@pytest.fixture(autouse=True)
def isolate_settings_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate settings resolution between tests."""

    get_settings.cache_clear()
    get_cache_settings.cache_clear()
    runtime_dir = Path.cwd() / ".test_runtime"
    runtime_dir.mkdir(exist_ok=True)
    monkeypatch.chdir(runtime_dir)
    for env_var in (
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "LOCAL_CACHE_DB_PATH",
        "CACHE_REFRESH_MINUTES",
        "DATA_SOURCE_MODE",
    ):
        monkeypatch.delenv(env_var, raising=False)

    yield

    get_settings.cache_clear()
    get_cache_settings.cache_clear()


@pytest.fixture
def valid_env(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Provide a complete set of valid environment variables."""

    env = {
        "OPENAI_API_KEY": "test-openai-key",
        "OPENAI_MODEL": "gpt-4.1-mini",
        "GOOGLE_APPLICATION_CREDENTIALS": "/tmp/fake-service-account.json",
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return env


@pytest.fixture
def valid_ask_request_payload() -> dict[str, str]:
    """Return a valid /ask request payload."""

    return {"question": "Qual canal teve melhor performance?"}


@pytest.fixture
def valid_ask_response_payload() -> dict:
    """Return a valid /ask response payload."""

    return {
        "answer": "Organic teve a melhor performance nos ultimos 30 dias.",
        "used_tool": "get_channel_performance_summary",
        "data": {"channels": []},
        "error": None,
    }


@pytest.fixture
def valid_date_range_payload() -> dict[str, str]:
    """Return a valid date range payload."""

    return {"start_date": "2026-04-01", "end_date": "2026-04-30"}


@pytest.fixture
def valid_parsed_question_payload(valid_date_range_payload: dict[str, str]) -> dict:
    """Return a valid parsed question payload."""

    return {
        "intent": "traffic_volume_by_source",
        "traffic_source": "Search",
        "date_range": valid_date_range_payload,
        "needs_data": True,
        "out_of_scope_reason": None,
    }


@pytest.fixture
def valid_channel_performance_payload() -> dict:
    """Return a valid channel performance payload."""

    return {
        "traffic_source": "Organic",
        "users": 1000,
        "converted_users": 80,
        "orders": 80,
        "revenue": 5500.0,
        "conversion_rate": 0.08,
    }
