import { lstat, realpath, rm } from "node:fs/promises";
import path from "node:path";

const root = await realpath(process.cwd());
const buildDir = path.resolve(root, ".next-brandlens-build");
const relative = path.relative(root, buildDir);
if (relative !== ".next-brandlens-build" || path.isAbsolute(relative)) {
  throw new Error(`Refusing to clean an unexpected Next.js build path: ${buildDir}`);
}

try {
  const info = await lstat(buildDir);
  if (!info.isDirectory()) throw new Error(`Expected a generated build directory at ${buildDir}`);
  await rm(buildDir, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 });
} catch (error) {
  if (error?.code !== "ENOENT") throw error;
}
