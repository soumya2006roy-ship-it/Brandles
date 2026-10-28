import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { spawnSync } from "node:child_process";

const root = process.cwd();
const windowsPython = resolve(root, "api", ".venv", "Scripts", "python.exe");
const unixPython = resolve(root, "api", ".venv", "bin", "python");
const python = existsSync(windowsPython) ? windowsPython : existsSync(unixPython) ? unixPython : (process.platform === "win32" ? "py" : "python3");
const args = python === "py" ? ["-3", "scripts/simulate_health.py"] : ["scripts/simulate_health.py"];
const result = spawnSync(python, args, { cwd: resolve(root, "api"), stdio: "inherit" });
if (result.error) throw result.error;
process.exit(result.status ?? 1);
