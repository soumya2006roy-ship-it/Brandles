import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const mode = process.argv[2] === "prod" ? "prod" : "dev";
const windows = process.platform === "win32";
const command = windows ? "cmd.exe" : "bash";
const args = windows ? ["/d", "/c", "start.bat", mode] : [path.join(root, "start.sh"), mode];
const child = spawn(command, args, { cwd: root, stdio: "inherit" });
const shutdown = () => child.kill("SIGINT");
process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);
child.on("error", (error) => { console.error(`Could not start BrandLens: ${error.message}`); process.exitCode = 1; });
child.on("exit", (code, signal) => { process.exitCode = code ?? (signal ? 1 : 0); });
