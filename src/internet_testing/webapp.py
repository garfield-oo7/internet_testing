from __future__ import annotations

from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import argparse
import json
from pathlib import Path
import subprocess
import sys
import threading
import time
from typing import Any
from uuid import uuid4

from internet_testing.openai_generator import DEFAULT_OPENAI_MODEL, DEFAULT_REASONING_EFFORT


@dataclass(frozen=True)
class RunConfig:
    url: str
    max_pages: int = 4
    max_depth: int = 1
    llm_command: str = ""
    use_openai: bool = False
    openai_model: str = DEFAULT_OPENAI_MODEL
    openai_reasoning_effort: str = DEFAULT_REASONING_EFFORT
    agent_max_tool_calls: int = 40
    agent_max_urls: int = 8
    agent_max_seconds: float = 120.0


@dataclass
class RunState:
    id: str
    config: RunConfig
    output_path: Path
    status: str = "queued"
    logs: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None


_RUNS: dict[str, RunState] = {}
_RUNS_LOCK = threading.Lock()


def build_run_commands(config: RunConfig, output_path: Path) -> tuple[list[str], list[str]]:
    generation = [
        sys.executable,
        "-m",
        "internet_testing.cli",
        config.url,
        "--output",
        str(output_path),
    ]
    if not config.use_openai:
        generation.extend(["--max-pages", str(config.max_pages), "--max-depth", str(config.max_depth)])
    if config.llm_command.strip():
        generation.extend(["--llm-command", config.llm_command.strip()])
    if config.use_openai:
        generation.extend(
            [
                "--openai",
                "--openai-model",
                config.openai_model,
                "--openai-reasoning-effort",
                config.openai_reasoning_effort,
                "--agent-max-tool-calls",
                str(config.agent_max_tool_calls),
                "--agent-max-urls",
                str(config.agent_max_urls),
                "--agent-max-seconds",
                str(config.agent_max_seconds),
            ]
        )

    execution = [
        sys.executable,
        "-m",
        "pytest",
        str(output_path),
        "--browser",
        "chromium",
        "--tb=short",
    ]
    return generation, execution


def create_run(config: RunConfig, runs_dir: Path, autostart: bool = True) -> RunState:
    runs_dir.mkdir(parents=True, exist_ok=True)
    run_id = uuid4().hex[:12]
    output_path = runs_dir / run_id / "test_generated.py"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    run = RunState(id=run_id, config=config, output_path=output_path)
    run.logs.append(f"Queued run {run_id} for {config.url}")

    with _RUNS_LOCK:
        _RUNS[run_id] = run

    if autostart:
        thread = threading.Thread(target=_run_pipeline, args=(run,), daemon=True)
        thread.start()
    return run


def run_server(host: str = "127.0.0.1", port: int = 8765, runs_dir: Path | None = None) -> None:
    handler = _make_handler(runs_dir or Path(".runs"))
    server = ThreadingHTTPServer((host, port), handler)
    print(f"Internet Testing UI running at http://{host}:{port}")
    server.serve_forever()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Internet Testing web UI.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--runs-dir", default=".runs")
    args = parser.parse_args(argv)
    run_server(host=args.host, port=args.port, runs_dir=Path(args.runs_dir))
    return 0


def _run_pipeline(run: RunState) -> None:
    _set_status(run, "running")
    generation, execution = build_run_commands(run.config, run.output_path)
    _append_log(run, "Generating Playwright tests")
    _append_log(run, "$ " + _shell_join(generation))

    if _run_command(run, generation) != 0:
        _set_status(run, "failed")
        return

    _append_log(run, "Running generated Playwright tests without LLM command")
    _append_log(run, "$ " + _shell_join(execution))
    if _run_command(run, execution) != 0:
        _set_status(run, "failed")
        return

    _set_status(run, "passed")


def _run_command(run: RunState, command: list[str]) -> int:
    process = subprocess.Popen(
        command,
        cwd=Path.cwd(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
    )
    assert process.stdout is not None
    for line in process.stdout:
        _append_log(run, line.rstrip())
    return process.wait()


def _set_status(run: RunState, status: str) -> None:
    with _RUNS_LOCK:
        run.status = status
        if status in {"passed", "failed"}:
            run.completed_at = time.time()


def _append_log(run: RunState, message: str) -> None:
    with _RUNS_LOCK:
        run.logs.append(message)


def _make_handler(runs_dir: Path):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/":
                self._send_html(INDEX_HTML)
                return
            if self.path.startswith("/api/runs/"):
                run_id = self.path.rsplit("/", 1)[-1]
                run = _get_run(run_id)
                if run is None:
                    self._send_json({"error": "run not found"}, status=404)
                    return
                self._send_json(_run_to_payload(run))
                return
            self._send_json({"error": "not found"}, status=404)

        def do_POST(self) -> None:
            if self.path != "/api/runs":
                self._send_json({"error": "not found"}, status=404)
                return

            try:
                payload = self._read_json()
                config = _config_from_payload(payload)
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=400)
                return

            run = create_run(config, runs_dir=runs_dir, autostart=True)
            self._send_json(_run_to_payload(run), status=201)

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _read_json(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8")
            if not raw:
                return {}
            return json.loads(raw)

        def _send_html(self, html: str, status: int = 200) -> None:
            body = html.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
            body = json.dumps(payload, indent=2).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def _config_from_payload(payload: dict[str, Any]) -> RunConfig:
    url = str(payload.get("url", "")).strip()
    if not (url.startswith("https://") or url.startswith("http://")):
        raise ValueError("Enter a full http:// or https:// URL.")
    max_pages = _bounded_int(payload.get("max_pages", 4), minimum=1, maximum=12)
    max_depth = _bounded_int(payload.get("max_depth", 1), minimum=0, maximum=3)
    llm_command = str(payload.get("llm_command", "")).strip()
    use_openai = bool(payload.get("use_openai", False))
    if use_openai and llm_command:
        raise ValueError("Use either OpenAI generation or an LLM command, not both.")
    openai_model = str(payload.get("openai_model", DEFAULT_OPENAI_MODEL)).strip() or DEFAULT_OPENAI_MODEL
    openai_reasoning_effort = (
        str(payload.get("openai_reasoning_effort", DEFAULT_REASONING_EFFORT)).strip()
        or DEFAULT_REASONING_EFFORT
    )
    agent_max_tool_calls = _bounded_int(payload.get("agent_max_tool_calls", 40), minimum=1, maximum=200)
    agent_max_urls = _bounded_int(payload.get("agent_max_urls", 8), minimum=1, maximum=50)
    agent_max_seconds = float(_bounded_int(payload.get("agent_max_seconds", 120), minimum=5, maximum=1800))
    return RunConfig(
        url=url,
        max_pages=max_pages,
        max_depth=max_depth,
        llm_command=llm_command,
        use_openai=use_openai,
        openai_model=openai_model,
        openai_reasoning_effort=openai_reasoning_effort,
        agent_max_tool_calls=agent_max_tool_calls,
        agent_max_urls=agent_max_urls,
        agent_max_seconds=agent_max_seconds,
    )


def _bounded_int(value: Any, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Expected integer between {minimum} and {maximum}.") from exc
    return max(minimum, min(maximum, parsed))


def _get_run(run_id: str) -> RunState | None:
    with _RUNS_LOCK:
        return _RUNS.get(run_id)


def _run_to_payload(run: RunState) -> dict[str, Any]:
    with _RUNS_LOCK:
        return {
            "id": run.id,
            "url": run.config.url,
            "status": run.status,
            "logs": list(run.logs),
            "output_path": str(run.output_path),
            "created_at": run.created_at,
            "completed_at": run.completed_at,
        }


def _shell_join(command: list[str]) -> str:
    return " ".join(_quote(part) for part in command)


def _quote(value: str) -> str:
    if not value or any(char.isspace() for char in value):
        return "'" + value.replace("'", "'\\''") + "'"
    return value


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Internet Testing Console</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #111312;
      --panel: #191d1b;
      --panel-2: #222824;
      --line: #3a443e;
      --text: #edf3ec;
      --muted: #9daa9d;
      --accent: #b7ff5a;
      --accent-2: #5ee1a0;
      --danger: #ff6b6b;
      --warn: #ffd166;
      --radius: 8px;
    }

    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background:
        linear-gradient(120deg, rgba(183, 255, 90, 0.08), transparent 32%),
        linear-gradient(220deg, rgba(94, 225, 160, 0.08), transparent 38%),
        var(--bg);
      color: var(--text);
      font: 15px/1.5 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }

    main {
      width: min(1180px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 28px 0;
      display: grid;
      grid-template-columns: 390px minmax(0, 1fr);
      gap: 18px;
    }

    header {
      grid-column: 1 / -1;
      border: 1px solid var(--line);
      background: rgba(25, 29, 27, 0.86);
      border-radius: var(--radius);
      padding: 18px;
      display: flex;
      justify-content: space-between;
      gap: 18px;
      align-items: end;
    }

    h1 {
      margin: 0;
      font-size: 24px;
      letter-spacing: 0;
    }

    .sub {
      margin: 6px 0 0;
      color: var(--muted);
      max-width: 720px;
    }

    .badge {
      border: 1px solid var(--accent);
      color: var(--accent);
      border-radius: 999px;
      padding: 6px 10px;
      white-space: nowrap;
    }

    section {
      border: 1px solid var(--line);
      background: rgba(25, 29, 27, 0.9);
      border-radius: var(--radius);
      min-width: 0;
    }

    form {
      padding: 16px;
      display: grid;
      gap: 14px;
    }

    label {
      display: grid;
      gap: 7px;
      color: var(--muted);
    }

    input {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: var(--panel-2);
      color: var(--text);
      padding: 11px 12px;
      font: inherit;
    }

    input:focus {
      outline: 2px solid rgba(183, 255, 90, 0.45);
      border-color: var(--accent);
    }

    .row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }

    button {
      border: 0;
      border-radius: var(--radius);
      background: var(--accent);
      color: #111312;
      font: inherit;
      font-weight: 700;
      padding: 12px 14px;
      cursor: pointer;
    }

    button:disabled {
      opacity: 0.55;
      cursor: not-allowed;
    }

    .hint {
      margin: 0;
      color: var(--muted);
      font-size: 13px;
    }

    .log-head {
      min-height: 58px;
      padding: 14px 16px;
      border-bottom: 1px solid var(--line);
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
    }

    .status {
      border-radius: 999px;
      padding: 5px 9px;
      background: var(--panel-2);
      color: var(--muted);
    }

    .status.running { color: var(--warn); }
    .status.passed { color: var(--accent-2); }
    .status.failed { color: var(--danger); }

    pre {
      margin: 0;
      padding: 16px;
      min-height: 520px;
      max-height: calc(100vh - 210px);
      overflow: auto;
      white-space: pre-wrap;
      word-break: break-word;
      background: #0c0f0d;
      border-radius: 0 0 var(--radius) var(--radius);
    }

    @media (max-width: 860px) {
      main { grid-template-columns: 1fr; }
      header { align-items: start; flex-direction: column; }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>Internet Testing Console</h1>
        <p class="sub">Generate Playwright tests from explored DOM evidence, then run the generated tests without sending the execution phase through an LLM.</p>
      </div>
      <div class="badge">No LLM during pytest</div>
    </header>

    <section>
      <form id="run-form">
        <label>
          Website URL
          <input id="url" name="url" type="url" value="https://www.flipkart.com/" required>
        </label>
        <div class="row">
          <label>
            Max pages
            <input id="max_pages" name="max_pages" type="number" min="1" max="12" value="4">
          </label>
          <label>
            Max depth
            <input id="max_depth" name="max_depth" type="number" min="0" max="3" value="1">
          </label>
        </div>
        <div class="row">
          <label>
            Agent tool calls
            <input id="agent_max_tool_calls" name="agent_max_tool_calls" type="number" min="1" max="200" value="40">
          </label>
          <label>
            Agent URLs
            <input id="agent_max_urls" name="agent_max_urls" type="number" min="1" max="50" value="8">
          </label>
        </div>
        <label>
          Agent seconds
          <input id="agent_max_seconds" name="agent_max_seconds" type="number" min="5" max="1800" value="120">
        </label>
        <label>
          LLM command for generation
          <input id="llm_command" name="llm_command" placeholder="python scripts/write_tests_with_model.py">
        </label>
        <label>
          <input id="use_openai" name="use_openai" type="checkbox">
          Use OpenAI for generation
        </label>
        <div class="row">
          <label>
            OpenAI model
            <input id="openai_model" name="openai_model" value="gpt-5.5">
          </label>
          <label>
            Reasoning effort
            <select id="openai_reasoning_effort" name="openai_reasoning_effort">
              <option value="medium" selected>medium</option>
              <option value="low">low</option>
              <option value="high">high</option>
              <option value="xhigh">xhigh</option>
              <option value="none">none</option>
            </select>
          </label>
        </div>
        <p class="hint">OpenAI and LLM commands only receive exploration JSON for test generation. The generated file is then run by pytest without that command or any OpenAI API call.</p>
        <button id="submit" type="submit">Run website test</button>
      </form>
    </section>

    <section>
      <div class="log-head">
        <strong>Run logs</strong>
        <span id="status" class="status">idle</span>
      </div>
      <pre id="logs">Paste a URL and start a run.</pre>
    </section>
  </main>
  <script>
    const form = document.querySelector("#run-form");
    const logs = document.querySelector("#logs");
    const status = document.querySelector("#status");
    const submit = document.querySelector("#submit");
    let timer = null;

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      submit.disabled = true;
      logs.textContent = "Starting run...";
      setStatus("queued");

      const payload = {
        url: form.url.value,
        max_pages: form.max_pages.value,
        max_depth: form.max_depth.value,
        llm_command: form.llm_command.value,
        use_openai: form.use_openai.checked,
        openai_model: form.openai_model.value,
        openai_reasoning_effort: form.openai_reasoning_effort.value,
        agent_max_tool_calls: form.agent_max_tool_calls.value,
        agent_max_urls: form.agent_max_urls.value,
        agent_max_seconds: form.agent_max_seconds.value
      };

      const response = await fetch("/api/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      if (!response.ok) {
        logs.textContent = data.error || "Unable to start run.";
        setStatus("failed");
        submit.disabled = false;
        return;
      }
      poll(data.id);
    });

    async function poll(id) {
      if (timer) clearTimeout(timer);
      const response = await fetch(`/api/runs/${id}`);
      const data = await response.json();
      setStatus(data.status);
      logs.textContent = data.logs.join("\\n");
      logs.scrollTop = logs.scrollHeight;
      if (data.status === "passed" || data.status === "failed") {
        submit.disabled = false;
        return;
      }
      timer = setTimeout(() => poll(id), 900);
    }

    function setStatus(value) {
      status.textContent = value;
      status.className = `status ${value}`;
    }
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    raise SystemExit(main())
