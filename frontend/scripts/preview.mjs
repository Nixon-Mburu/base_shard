// Local production-build preview. Deployment uses the Nginx gateway.
import { createServer } from "node:http";
import { readFile, stat } from "node:fs/promises";
import { resolve, extname, sep } from "node:path";
const root = resolve(import.meta.dirname, "..");
const mime = {
  ".html": "text/html",
  ".js": "text/javascript",
  ".css": "text/css",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
  ".png": "image/png",
  ".svg": "image/svg+xml",
};
createServer(async (req, res) => {
  try {
    const pathname = decodeURIComponent(
      new URL(req.url, "http://localhost").pathname,
    );
    const match = pathname.match(/^\/mfe\/(signup|orders|checkout)\/(.*)$/);
    const base = resolve(root, "apps", match ? match[1] : "shell", "dist");
    let file = resolve(base, "." + (match ? "/" + match[2] : pathname));
    if (file !== base && !file.startsWith(base + sep)) {
      res.writeHead(403);
      res.end();
      return;
    }
    try {
      if ((await stat(file)).isDirectory()) file = resolve(file, "index.html");
    } catch {
      if (extname(file)) {
        res.writeHead(404);
        res.end();
        return;
      }
      file = resolve(base, "index.html");
    }
    const data = await readFile(file);
    res.writeHead(200, {
      "Content-Type": mime[extname(file)] || "application/octet-stream",
      "Cache-Control": "no-cache",
    });
    res.end(data);
  } catch {
    res.writeHead(500);
    res.end("Build the apps with npm run build first.");
  }
}).listen(4173, "127.0.0.1", () =>
  console.log("Production build preview: http://localhost:4173"),
);
