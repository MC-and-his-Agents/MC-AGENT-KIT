#!/usr/bin/env node
"use strict";

// SessionStart is the lifecycle boundary for the current worktree. It makes
// one bounded attempt to create or refresh the local CodeGraph index, then
// always returns context. SubagentStart only observes; it never runs a costly
// lifecycle command.
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const crypto = require("node:crypto");
const childProcess = require("node:child_process");

const EVENT = process.argv[2] || "SessionStart";
const ACTION_TIMEOUT_MS = 18_000;
const STATUS_TIMEOUT_MS = 3_000;
const KILL_GRACE_MS = 350;
const PROBE_TIMEOUT_MS = 500;
const LOCK_STALE_TIMEOUT_MS = 2 * 60 * 1000;
const MANUAL_SYNC_KEYS = "\u001b[B\r";
const MAX_REASON_LENGTH = 360;

function text(value) {
  return typeof value === "string" ? value.trim() : "";
}

function commandOutput(args, cwd) {
  try {
    const result = childProcess.spawnSync(args[0], args.slice(1), {
      cwd,
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
      timeout: PROBE_TIMEOUT_MS,
      windowsHide: true,
    });
    return result.status === 0 ? text(result.stdout) : "";
  } catch (_error) {
    return "";
  }
}

function resolveCwd() {
  const candidate =
    text(process.env.CODEX_CWD) ||
    text(process.env.CODEX_WORKSPACE_DIR) ||
    text(process.env.CLAUDE_PROJECT_DIR) ||
    process.cwd();
  try {
    return fs.realpathSync(candidate);
  } catch (_error) {
    return path.resolve(candidate);
  }
}

function canonicalPath(candidate, base) {
  const absolute = path.resolve(base, candidate);
  try {
    return fs.realpathSync(absolute);
  } catch (_error) {
    return absolute;
  }
}

function gitIdentity(cwd) {
  const worktree = commandOutput(["git", "-C", cwd, "rev-parse", "--show-toplevel"], cwd);
  if (!worktree) return { worktree_root: null, git_common_dir: null, git_hooks_dir: null };
  const common = commandOutput(["git", "-C", worktree, "rev-parse", "--git-common-dir"], worktree);
  const hooks = commandOutput(["git", "-C", worktree, "rev-parse", "--git-path", "hooks"], worktree);
  return {
    worktree_root: canonicalPath(worktree, cwd),
    git_common_dir: common ? canonicalPath(common, worktree) : null,
    git_hooks_dir: hooks ? canonicalPath(hooks, worktree) : null,
  };
}

function executableOnPath(name) {
  const pathValue = text(process.env.PATH);
  const candidates = pathValue ? pathValue.split(path.delimiter) : [];
  const names = process.platform === "win32" ? [name, `${name}.exe`, `${name}.cmd`, `${name}.bat`] : [name];
  for (const directory of candidates) {
    for (const candidate of names) {
      const file = path.join(directory || ".", candidate);
      try {
        if (!fs.statSync(file).isFile()) continue;
        if (process.platform !== "win32") fs.accessSync(file, fs.constants.X_OK);
        return canonicalPath(file, process.cwd());
      } catch (_error) {
        // A missing or inaccessible PATH entry is ordinary evidence.
      }
    }
  }
  return null;
}

function indexInfo(worktree) {
  if (!worktree) return { state: "missing", path: null };
  const directory = path.join(worktree, ".codegraph");
  const index = path.join(directory, "codegraph.db");
  let directoryStat;
  try {
    directoryStat = fs.lstatSync(directory);
  } catch (_error) {
    return { state: "missing", path: null };
  }
  if (!directoryStat.isDirectory()) return { state: "corrupt", path: directory };
  let stat;
  try {
    stat = fs.lstatSync(index);
  } catch (_error) {
    // An existing directory without the DB is safe to initialize.
    return { state: "missing", path: null };
  }
  if (!stat.isFile()) return { state: "corrupt", path: index };
  if (stat.size < 16) return { state: "corrupt", path: index };
  try {
    const header = fs.readFileSync(index).subarray(0, 16).toString("ascii");
    return header.startsWith("SQLite format 3")
      ? { state: "ready", path: index }
      : { state: "corrupt", path: index };
  } catch (_error) {
    return { state: "corrupt", path: index };
  }
}

function lockInfo(worktree) {
  if (!worktree) return { state: "unknown", path: null, present: false, active: false };
  const lockPath = path.join(worktree, ".codegraph", "codegraph.lock");
  let stat;
  try {
    stat = fs.lstatSync(lockPath);
  } catch (_error) {
    return { state: "clear", path: lockPath, present: false, active: false };
  }
  if (!stat.isFile()) {
    return { state: "unknown", path: lockPath, present: true, active: true, reason: "lock path is not a regular file" };
  }
  let content = "";
  try {
    content = fs.readFileSync(lockPath, "utf8").slice(0, 128).trim();
  } catch (_error) {
    return { state: "unknown", path: lockPath, present: true, active: true, reason: "lock file is unreadable" };
  }
  const pid = Number.parseInt(content, 10);
  const ageMs = Math.max(0, Date.now() - stat.mtimeMs);
  let alive = false;
  if (Number.isInteger(pid) && pid > 0) {
    try {
      process.kill(pid, 0);
      alive = true;
    } catch (_error) {
      // EPERM still proves that a process exists; treat it as active so the
      // lifecycle never overwrites an index owned by another user.
      alive = _error && _error.code === "EPERM";
    }
  }
  if (Number.isInteger(pid) && pid > 0 && alive) {
    return {
      state: "active",
      path: lockPath,
      present: true,
      active: true,
      pid,
      ageMs,
      reason: `CodeGraph database lock is held by live PID ${pid}`,
    };
  }
  if (ageMs < LOCK_STALE_TIMEOUT_MS && (!Number.isInteger(pid) || pid <= 0)) {
    return {
      state: Number.isInteger(pid) && pid > 0 ? "active" : "unknown",
      path: lockPath,
      present: true,
      active: true,
      pid: Number.isInteger(pid) && pid > 0 ? pid : null,
      ageMs,
      reason: Number.isInteger(pid) && pid > 0
        ? `CodeGraph database lock is held by live PID ${pid}`
        : "CodeGraph database lock is fresh but has no valid PID",
    };
  }
  return {
    state: "stale",
    path: lockPath,
    present: true,
    active: false,
    pid: Number.isInteger(pid) && pid > 0 ? pid : null,
    ageMs,
    reason: "CodeGraph database lock appears stale; the CLI may remove it safely",
  };
}

function hookSnapshot(gitHooksDir) {
  if (!gitHooksDir) return null;
  const hookDir = canonicalPath(gitHooksDir, process.cwd());
  const entries = [];
  try {
    for (const name of fs.readdirSync(hookDir).sort()) {
      const file = path.join(hookDir, name);
      try {
        const stat = fs.lstatSync(file);
        if (!stat.isFile()) {
          entries.push(`${name}:${stat.mode}:non-file`);
          continue;
        }
        const digest = crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
        entries.push(`${name}:${stat.mode}:${digest}`);
      } catch (_error) {
        return null;
      }
    }
  } catch (_error) {
    if (_error && _error.code === "ENOENT") return `${hookDir}:`;
    return null;
  }
  return `${hookDir}:${entries.join(",")}`;
}

function lifecycleTimeoutMs() {
  const configured = Number(process.env.CODEATLAS_HOOK_TIMEOUT_MS);
  return Number.isFinite(configured) && configured > 0
    ? Math.min(configured, ACTION_TIMEOUT_MS)
    : ACTION_TIMEOUT_MS;
}

function lifecycleEnvironment(action) {
  const environment = {
    ...process.env,
    CODEGRAPH_NO_DOWNLOAD: "1",
    CODEGRAPH_NO_DAEMON: "1",
    CODEGRAPH_NO_UPDATE_CHECK: "1",
    CODEGRAPH_NO_TELEMETRY: "1",
    CODEGRAPH_TELEMETRY: "0",
    DO_NOT_TRACK: "1",
    CI: "1",
  };
  if (action === "init") {
    // Init offers Git-hook fallback only when watching is disabled. Force the
    // normal policy so both supported CLI lines remain non-interactive.
    environment.CODEGRAPH_FORCE_WATCH = "1";
    delete environment.CODEGRAPH_NO_WATCH;
  } else {
    environment.CODEGRAPH_NO_WATCH = "1";
    delete environment.CODEGRAPH_FORCE_WATCH;
  }
  return environment;
}

function compactOutput(value) {
  const lines = text(value)
    .split(/\r?\n/)
    .map((line) => line.replace(/\u001b\[[0-?]*[ -/]*[@-~]/g, "").trim())
    .filter(Boolean);
  return lines.slice(-4).join(" | ").slice(-MAX_REASON_LENGTH);
}

function quoteWindowsArg(value) {
  const input = String(value);
  if (!/[\s"&|<>^]/.test(input)) return input;
  return `"${input.replace(/(\\*)"/g, "$1$1\\\"").replace(/(\\*)$/g, "$1$1")}"`;
}

function quoteDisplayArg(value) {
  const input = String(value);
  if (process.platform === "win32") return quoteWindowsArg(input);
  return /[\s'"`$\\]/.test(input) ? `'${input.replaceAll("'", "'\\''")}'` : input;
}

function exactCommand(action, worktree) {
  const root = quoteDisplayArg(worktree);
  return action === "init" ? `codegraph init ${root}` : `codegraph sync --quiet ${root}`;
}

function spawnSpec(cli, args) {
  if (process.platform !== "win32" || !/\.(?:cmd|bat)$/i.test(cli)) {
    return { command: cli, args };
  }
  const commandLine = [cli, ...args].map(quoteWindowsArg).join(" ");
  return { command: process.env.ComSpec || "cmd.exe", args: ["/d", "/s", "/c", commandLine] };
}

function sleep(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

async function terminateProcessTree(child) {
  if (!child || !child.pid) return;
  if (process.platform === "win32") {
    await new Promise((resolve) => {
      const killer = childProcess.spawn("taskkill", ["/PID", String(child.pid), "/T", "/F"], {
        stdio: "ignore",
        windowsHide: true,
      });
      const timer = setTimeout(() => {
        try { killer.kill(); } catch (_error) { /* already gone */ }
        resolve();
      }, KILL_GRACE_MS);
      killer.once("close", () => {
        clearTimeout(timer);
        resolve();
      });
      killer.once("error", () => {
        clearTimeout(timer);
        resolve();
      });
    });
    return;
  }
  try { process.kill(-child.pid, "SIGTERM"); } catch (_error) { /* process already gone */ }
  await sleep(KILL_GRACE_MS);
  try { process.kill(-child.pid, "SIGKILL"); } catch (_error) { /* process already gone */ }
}

function spawnBounded(cli, args, action, cwd) {
  return spawnBoundedWithTimeout(cli, args, action, cwd, lifecycleTimeoutMs());
}

function spawnBoundedWithTimeout(cli, args, action, cwd, timeoutMs) {
  return new Promise((resolve) => {
    const spec = spawnSpec(cli, args);
    let child;
    try {
      child = childProcess.spawn(spec.command, spec.args, {
        cwd,
        env: lifecycleEnvironment(action),
        detached: process.platform !== "win32",
        stdio: ["pipe", "pipe", "pipe"],
        windowsHide: true,
      });
    } catch (error) {
      resolve({ status: null, signal: null, error, stdout: "", stderr: "", timedOut: false });
      return;
    }
    let stdout = "";
    let stderr = "";
    let settled = false;
    let timedOut = false;
    const timer = setTimeout(async () => {
      timedOut = true;
      await terminateProcessTree(child);
    }, timeoutMs);
    child.stdout?.on("data", (chunk) => { stdout += chunk.toString(); });
    child.stderr?.on("data", (chunk) => { stderr += chunk.toString(); });
    child.once("error", (error) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve({ status: null, signal: null, error, stdout, stderr, timedOut });
    });
    child.once("close", (status, signal) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve({ status, signal, error: null, stdout, stderr, timedOut });
    });
    if (child.stdin) {
      // A fast-failing CLI may close stdin before the prompt hint is written;
      // EPIPE is evidence from the child, not a hook-fatal process error.
      child.stdin.once("error", () => {});
      try {
        if (action === "init") child.stdin.end(MANUAL_SYNC_KEYS);
        else child.stdin.end();
      } catch (_error) {
        // The close/error event below still records the bounded child result.
      }
    }
  });
}

function pendingChangesClear(value) {
  if (value === 0) return true;
  if (!value || typeof value !== "object") return false;
  return Object.values(value).every((entry) => Number(entry) === 0);
}

function statusIndexPath(worktree, value) {
  if (typeof value !== "string" || !value.trim()) return null;
  const candidate = canonicalPath(value, worktree);
  const database = canonicalPath(path.join(worktree, ".codegraph", "codegraph.db"), worktree);
  if (candidate === database) return database;
  // CodeGraph 1.5.0 reports the index directory, while 0.9.9 omits
  // indexPath. Normalize that public shape to the exact database file.
  if (candidate === canonicalPath(path.join(worktree, ".codegraph"), worktree)) return database;
  return candidate;
}

async function verifyStatus(worktree, cli) {
  const result = await spawnBoundedWithTimeout(
    cli,
    ["status", "--json", worktree],
    "status",
    worktree,
    STATUS_TIMEOUT_MS,
  );
  if (result.timedOut) {
    return { ok: false, code: "status-timeout", reason: `status --json 在 ${STATUS_TIMEOUT_MS}ms 内未完成。` };
  }
  if (result.error) {
    return { ok: false, code: "status-spawn-error", reason: `启动 status --json 失败：${result.error.message || String(result.error)}` };
  }
  if (result.signal || result.status !== 0) {
    return { ok: false, code: "status-non-zero", reason: compactOutput(`${result.stdout}\n${result.stderr}`) || `status --json 退出码 ${String(result.status)}` };
  }
  let document;
  try {
    document = JSON.parse(result.stdout);
  } catch (_error) {
    return { ok: false, code: "status-parse", reason: "status --json 没有返回可解析 JSON。" };
  }
  if (!document || document.initialized !== true) {
    return { ok: false, code: "status-uninitialized", reason: "status --json 未确认 initialized=true。" };
  }
  if (typeof document.projectPath !== "string" || canonicalPath(document.projectPath, worktree) !== canonicalPath(worktree, worktree)) {
    return { ok: false, code: "status-project-path", reason: "status --json 的 projectPath 不匹配当前 worktree。" };
  }
  if (document.indexPath !== undefined) {
    const normalized = statusIndexPath(worktree, document.indexPath);
    const exact = canonicalPath(path.join(worktree, ".codegraph", "codegraph.db"), worktree);
    if (normalized !== exact) {
      return { ok: false, code: "status-index-path", reason: "status --json 的 indexPath 不匹配当前 worktree 的精确数据库。" };
    }
  }
  if (!pendingChangesClear(document.pendingChanges)) {
    return { ok: false, code: "status-pending", reason: `status --json 仍报告 pendingChanges=${JSON.stringify(document.pendingChanges)}。` };
  }
  return { ok: true, document };
}

async function runLifecycle(action, worktree, gitHooksDir, cli) {
  const beforeLock = lockInfo(worktree);
  if (beforeLock.active) {
    return {
      ok: false,
      action,
      command: exactCommand(action, worktree),
      code: "lock-conflict",
      reason: `${beforeLock.reason}; 未执行生命周期命令，避免破坏并发索引。`,
      index: indexInfo(worktree),
      lock: beforeLock,
    };
  }
  const beforeHooks = hookSnapshot(gitHooksDir);
  if (beforeHooks === null) {
    return {
      ok: false,
      action,
      command: exactCommand(action, worktree),
      code: "git-hook-probe",
      reason: "无法读取共享 Git hooks；未执行生命周期命令，避免把未验证结果标记为成功。",
      index: indexInfo(worktree),
      lock: lockInfo(worktree),
    };
  }
  const args = action === "init" ? ["init", worktree] : ["sync", "--quiet", worktree];
  const result = await spawnBounded(cli, args, action, worktree);
  const afterHooks = hookSnapshot(gitHooksDir);
  const afterLock = lockInfo(worktree);
  const info = indexInfo(worktree);
  if (afterHooks === null) {
    return {
      ok: false,
      action,
      command: exactCommand(action, worktree),
      code: "git-hook-probe",
      reason: "生命周期后无法读取共享 Git hooks；结果未标记为成功。",
      index: info,
      lock: afterLock,
    };
  }
  if (beforeHooks !== afterHooks) {
    return {
      ok: false,
      action,
      command: exactCommand(action, worktree),
      code: "git-hook-write",
      reason: "检测到 CodeGraph 修改了 Git hooks；已拒绝把生命周期结果标记为成功。",
      index: info,
      lock: afterLock,
    };
  }
  if (afterLock.present) {
    return {
      ok: false,
      action,
      command: exactCommand(action, worktree),
      code: "lock-present",
      reason: `${afterLock.reason || "CodeGraph lock remains"}; lifecycle freshness is unverified.`,
      index: info,
      lock: afterLock,
    };
  }
  if (result.timedOut) {
    return {
      ok: false,
      action,
      command: exactCommand(action, worktree),
      code: "timeout",
      reason: `在 ${lifecycleTimeoutMs()}ms 内未完成，已终止整个生命周期进程组。`,
      index: info,
      lock: afterLock,
    };
  }
  if (result.error) {
    return {
      ok: false,
      action,
      command: exactCommand(action, worktree),
      code: "spawn-error",
      reason: `启动 CodeGraph 失败：${result.error.message || String(result.error)}`,
      index: info,
      lock: afterLock,
    };
  }
  if (result.signal || result.status !== 0) {
    return {
      ok: false,
      action,
      command: exactCommand(action, worktree),
      code: "non-zero",
      reason: compactOutput(`${result.stdout}\n${result.stderr}`) || `退出码 ${String(result.status)}`,
      index: info,
      lock: afterLock,
    };
  }
  if (info.state !== "ready") {
    return {
      ok: false,
      action,
      command: exactCommand(action, worktree),
      code: "partial-index",
      reason: `命令返回成功，但精确索引状态为 ${info.state}。${compactOutput(`${result.stdout}\n${result.stderr}`)}`.trim(),
      index: info,
      lock: afterLock,
    };
  }
  const status = await verifyStatus(worktree, cli);
  if (!status.ok) {
    return {
      ok: false,
      action,
      command: exactCommand(action, worktree),
      code: status.code,
      reason: status.reason,
      index: info,
      lock: afterLock,
    };
  }
  const finalLock = lockInfo(worktree);
  const finalInfo = indexInfo(worktree);
  if (finalLock.present) {
    return {
      ok: false,
      action,
      command: exactCommand(action, worktree),
      code: "status-lock-present",
      reason: `${finalLock.reason || "CodeGraph lock remains"}; status freshness is unverified.`,
      index: finalInfo,
      lock: finalLock,
    };
  }
  if (finalInfo.state !== "ready") {
    return {
      ok: false,
      action,
      command: exactCommand(action, worktree),
      code: "status-index-missing",
      reason: `status --json 完成后精确数据库状态为 ${finalInfo.state}。`,
      index: finalInfo,
      lock: finalLock,
    };
  }
  return { ok: true, action, command: exactCommand(action, worktree), output: compactOutput(`${result.stdout}\n${result.stderr}`), index: finalInfo, lock: finalLock };
}

function baseEvidence(cwd, identity, cli, info, lock) {
  return {
    cwd,
    worktree_root: identity.worktree_root,
    git_common_dir: identity.git_common_dir,
    git_hooks_dir: identity.git_hooks_dir,
    cli,
    index_path: info.path,
    index_state: info.state,
    status: cli && info.state === "ready" ? "cli-only" : "unavailable",
    mcp: "unknown",
    lock: lock.state,
    action: null,
    reason: null,
    takeover: null,
    needs_agent: false,
    failure_code: null,
  };
}

async function collectEvidence() {
  const cwd = resolveCwd();
  const identity = gitIdentity(cwd);
  const cli = executableOnPath("codegraph");
  const info = indexInfo(identity.worktree_root);
  const lock = lockInfo(identity.worktree_root);
  const evidence = baseEvidence(cwd, identity, cli, info, lock);
  if (!identity.worktree_root) {
    evidence.needs_agent = true;
    evidence.status = "unavailable";
    evidence.failure_code = "not-git";
    evidence.reason = "当前目录不是 Git worktree，无法定位 worktree-local CodeGraph 索引。";
    return evidence;
  }
  if (!identity.git_common_dir || !identity.git_hooks_dir) {
    evidence.needs_agent = true;
    evidence.failure_code = "git-hooks-probe";
    evidence.reason = "无法解析 Git common-dir 或实际 hooks 路径，未执行生命周期命令。";
    evidence.takeover = exactCommand("init", identity.worktree_root);
    return evidence;
  }
  if (EVENT !== "SessionStart") {
    if (!cli) {
      evidence.needs_agent = true;
      evidence.failure_code = "cli-missing";
      evidence.reason = "当前会话未发现 codegraph CLI；SubagentStart 不会自动安装。";
      evidence.takeover = `安装官方 @colbymchenry/codegraph 后执行：${exactCommand("init", identity.worktree_root)}`;
    } else if (info.state === "corrupt") {
      evidence.status = "needs-agent";
      evidence.needs_agent = true;
      evidence.failure_code = "corrupt-index";
      evidence.reason = "当前 .codegraph/codegraph.db 不是可验证的 SQLite 数据库；SubagentStart 不会覆盖它。";
      evidence.takeover = `用户确认隔离/重建后执行：codegraph uninit ${quoteDisplayArg(identity.worktree_root)} && ${exactCommand("init", identity.worktree_root)}`;
    } else if (info.state === "missing") {
      evidence.needs_agent = true;
      evidence.failure_code = "init-not-attempted";
      evidence.reason = "当前 worktree 尚无 CodeGraph 索引；父 SessionStart 应先尝试初始化。";
      evidence.takeover = exactCommand("init", identity.worktree_root);
    }
    return evidence;
  }
  if (!cli) {
    evidence.needs_agent = true;
    evidence.failure_code = "cli-missing";
    evidence.reason = "PATH 中没有 codegraph CLI；hook 不会自动安装。";
    evidence.takeover = `安装官方 @colbymchenry/codegraph 后执行：${exactCommand("init", identity.worktree_root)}`;
    return evidence;
  }
  if (info.state === "corrupt") {
    evidence.status = "needs-agent";
    evidence.needs_agent = true;
    evidence.failure_code = "corrupt-index";
    evidence.reason = "当前 .codegraph/codegraph.db 不是可验证的 SQLite 数据库；hook 不会自动覆盖。";
    evidence.takeover = `用户确认隔离/重建后执行：codegraph uninit ${quoteDisplayArg(identity.worktree_root)} && ${exactCommand("init", identity.worktree_root)}`;
    return evidence;
  }
  const action = info.state === "missing" ? "init" : "sync";
  const result = await runLifecycle(action, identity.worktree_root, identity.git_hooks_dir, cli);
  evidence.action = action;
  evidence.index_path = result.index.path;
  evidence.index_state = result.index.state;
  evidence.lock = result.lock.state;
  if (result.ok) {
    evidence.status = "ready";
    evidence.reason = result.output || `${action} 已完成。`;
    return evidence;
  }
  evidence.status = "needs-agent";
  evidence.needs_agent = true;
  evidence.failure_code = result.code;
  evidence.reason = result.reason;
  evidence.takeover = result.command;
  return evidence;
}

function contextFor(evidence) {
  const cli = evidence.cli || "missing";
  const index = evidence.index_path || "missing";
  const state = evidence.index_state || "unknown";
  const worktree = evidence.worktree_root || "unknown";
  const common = evidence.git_common_dir || "unknown";
  const hooks = evidence.git_hooks_dir || "unknown";
  const action = evidence.action || "none";
  const lock = evidence.lock || "unknown";
  const failure = evidence.failure_code || "none";
  const prefix = `CodeAtlas status=${evidence.status}; needs-agent=${evidence.needs_agent ? "true" : "false"}; cwd=${evidence.cwd}; worktree=${worktree}; git-common-dir=${common}; git-hooks-dir=${hooks}; cli=${cli}; index=${index}; index-state=${state}; action=${action}; lock=${lock}; failure=${failure}; mcp=unknown.`;
  if (EVENT === "SubagentStart") {
    const attention = evidence.needs_agent && evidence.reason
      ? ` Parent lifecycle requires attention: ${evidence.reason} takeover=${evidence.takeover || "unknown"}.`
      : "";
    return `${prefix} SubagentStart does not run init or sync; use the parent SessionStart result. Evidence rules: mark claims observed, inferred or unknown; do not fabricate graph coverage.${attention}`;
  }
  if (evidence.needs_agent) {
    return `${prefix} Hook attempt: ${evidence.reason || "unknown failure"} Agent may continue in this same session. Exact takeover: ${evidence.takeover || "unknown"}. Hook writes, if any, are limited to the current worktree .codegraph and init-required .gitignore; it never installs the CLI, configures MCP, installs Git hooks, starts a daemon or watcher, or accesses the network.`;
  }
  return `${prefix} Current worktree index is ready for graph-backed work. Evidence rules: mark claims observed, inferred or unknown; native MCP remains unknown until the host visibly negotiates tools/list.`;
}

function protocolOutput(evidence) {
  const context = contextFor(evidence);
  if (process.env.PLUGIN_DATA) {
    return JSON.stringify({ systemMessage: `CodeAtlas: ${evidence.status}`, hookSpecificOutput: { hookEventName: EVENT, additionalContext: context } });
  }
  if (EVENT === "SubagentStart") {
    return JSON.stringify({ hookSpecificOutput: { hookEventName: EVENT, additionalContext: context } });
  }
  return context;
}

function unknownEvidence() {
  return {
    cwd: "unknown",
    worktree_root: null,
    git_common_dir: null,
    git_hooks_dir: null,
    cli: null,
    index_path: null,
    index_state: "unknown",
    status: "unavailable",
    mcp: "unknown",
    lock: "unknown",
    action: null,
    reason: "CodeAtlas hook 无法读取当前环境。",
    takeover: "由 Agent 在当前会话重新检查 codegraph CLI 与当前 worktree。",
    needs_agent: true,
    failure_code: "hook-error",
  };
}

async function main() {
  try {
    process.stdout.write(`${protocolOutput(await collectEvidence())}${os.EOL}`);
  } catch (_error) {
    try { process.stdout.write(`${protocolOutput(unknownEvidence())}${os.EOL}`); } catch (_ignored) { /* advisory hook */ }
  }
}

if (require.main === module) void main();

module.exports = {
  ACTION_TIMEOUT_MS,
  STATUS_TIMEOUT_MS,
  exactCommand,
  indexInfo,
  lifecycleEnvironment,
  lockInfo,
  quoteWindowsArg,
  spawnSpec,
};
