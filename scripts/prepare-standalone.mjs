import { cp, mkdir } from "node:fs/promises";
import path from "node:path";

const root = process.cwd();
const buildDir = path.join(root, ".next-brandlens-build");
const standaloneDir = path.join(buildDir, "standalone");

// The standalone server changes its working directory to its own folder.
// Put static assets where that server expects them for local `npm start` and
// container builds using the same output.
await mkdir(path.join(standaloneDir, ".next-brandlens-build"), { recursive: true });
await cp(path.join(buildDir, "static"), path.join(standaloneDir, ".next-brandlens-build", "static"), { recursive: true });
await cp(path.join(root, "public"), path.join(standaloneDir, "public"), { recursive: true });

console.log(`Prepared standalone runtime at ${path.relative(root, standaloneDir)}`);
