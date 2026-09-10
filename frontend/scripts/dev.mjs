import { spawn } from "node:child_process";
const children = ["signup", "orders", "checkout", "shell"].map((app) =>
  spawn("npm", ["run", "dev", "--workspace=@base-grid/" + app], {
    stdio: "inherit",
  }),
);
let stopping = false;
function stop(code = 0) {
  if (stopping) return;
  stopping = true;
  children.forEach((p) => p.kill("SIGTERM"));
  process.exitCode = code;
}
process.on("SIGINT", () => stop());
process.on("SIGTERM", () => stop());
children.forEach((p) =>
  p.on("exit", (code) => {
    if (!stopping) stop(code || 1);
  }),
);
