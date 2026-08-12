#!/usr/bin/env node
"use strict";

// Read-only lifecycle evidence. Never runs a CodeGraph subcommand, writes files,
// starts a daemon, checks the network, or waits for stdin.
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const childProcess = require("node:child_process");

const EVENT = process.argv[2] || "SessionStart";

function text(value) {
  return typeof value === "string" ? value.trim() : "";
}

function commandOutput(args, cwd) {
  try {
    const result = childProcess.spawnSync(args[0], args.slice(1), {
      cwd,
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
      timeout: 1500,
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
  if (!worktree) return { worktree_root: null, git_common_dir: null };
  const common = commandOutput(["git", "-C", worktree, "rev-parse", "--git-common-dir"], worktree);
  return {
    worktree_root: canonicalPath(worktree, cwd),
    git_common_dir: common ? canonicalPath(common, worktree) : null,
  };
}

function executableOnPath(name) {
  const pathValue = text(process.env.PATH);
  const candidates = pathValue ? pathValue.split(path.delimiter) : [];
  const names = process.platform === "win32" ? [name, `${name}.exe`, `${name}.cmd`] : [name];
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

function exactIndex(worktree) {
  if (!worktree) return null;
  const index = path.join(worktree, ".codegraph", "codegraph.db");
  try {
    return fs.lstatSync(index).isFile() ? index : null;
  } catch (_error) {
    return null;
  }
}

function collectEvidence() {
  const cwd = resolveCwd();
  const identity = gitIdentity(cwd);
  const cli = executableOnPath("codegraph");
  const indexPath = exactIndex(identity.worktree_root);
  const indexExists = Boolean(indexPath);
  const status = cli && indexExists ? "cli-only" : "unavailable";
  return {
    cwd,
    worktree_root: identity.worktree_root,
    git_common_dir: identity.git_common_dir,
    cli,
    index_path: indexPath,
    index_exists: indexExists,
    status,
    mcp: "unknown",
  };
}

function contextFor(evidence) {
  const cli = evidence.cli || "missing";
  const index = evidence.index_path || "missing";
  const worktree = evidence.worktree_root || "unknown";
  const common = evidence.git_common_dir || "unknown";
  if (EVENT === "SubagentStart") {
    return `CodeAtlas status=${evidence.status}; worktree=${worktree}; cli=${cli}; index=${index}; mcp=unknown. Evidence rules: mark claims observed, inferred or unknown; do not fabricate graph coverage; remain read-only and do not write files.`;
  }
  return [
    `CodeAtlas status=${evidence.status}; cwd=${evidence.cwd}; worktree=${worktree}; git-common-dir=${common}; cli=${cli}; index=${index}; mcp=unknown.`,
    "Limits: read-only; no CodeGraph subcommands, install, init, index, sync, serve, daemon, watcher or network; native MCP is unknown until the host visibly negotiates tools/list.",
  ].join(" ");
}

function protocolOutput(evidence) {
  const context = contextFor(evidence);
  if (process.env.PLUGIN_DATA) {
    return JSON.stringify({
      systemMessage: `CodeAtlas: ${evidence.status}`,
      hookSpecificOutput: {
        hookEventName: EVENT,
        additionalContext: context,
      },
    });
  }
  if (EVENT === "SubagentStart") {
    return JSON.stringify({
      hookSpecificOutput: {
        hookEventName: EVENT,
        additionalContext: context,
      },
    });
  }
  return context;
}

function unknownEvidence() {
  return {
    cwd: "unknown",
    worktree_root: null,
    git_common_dir: null,
    cli: null,
    index_path: null,
    index_exists: false,
    status: "unknown",
    mcp: "unknown",
  };
}

try {
  process.stdout.write(`${protocolOutput(collectEvidence())}${os.EOL}`);
} catch (_error) {
  try {
    process.stdout.write(`${protocolOutput(unknownEvidence())}${os.EOL}`);
  } catch (_ignored) {
    // Hooks are advisory; a closed stdout must never surface as a hook failure.
  }
}
