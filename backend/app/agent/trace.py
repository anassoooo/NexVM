"""Run traces (§XIV.5): one span per model call, tool call and executed step."""

import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field

_DETAIL_MAX = 600


@dataclass
class Span:
    kind: str  # llm | tool | step
    name: str
    start_ms: int
    duration_ms: int = 0
    ok: bool = True
    tokens_in: int = 0
    tokens_out: int = 0
    detail: str = ""


@dataclass
class Trace:
    spans: list[Span] = field(default_factory=list)
    _t0: float = field(default_factory=time.perf_counter)

    def _now(self) -> int:
        return int((time.perf_counter() - self._t0) * 1000)

    @contextmanager
    def span(self, kind: str, name: str):
        s = Span(kind, name, self._now())
        self.spans.append(s)
        started = time.perf_counter()
        try:
            yield s
        except Exception as exc:
            s.ok = False
            s.detail = s.detail or str(exc)
            raise
        finally:
            s.duration_ms = int((time.perf_counter() - started) * 1000)
            s.detail = s.detail[:_DETAIL_MAX]

    @property
    def tokens(self) -> int:
        return sum(s.tokens_in + s.tokens_out for s in self.spans)

    @property
    def elapsed_ms(self) -> int:
        return self._now()

    def to_list(self, offset_ms: int = 0) -> list[dict]:
        return [{**asdict(s), "start_ms": s.start_ms + offset_ms} for s in self.spans]
