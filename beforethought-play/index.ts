import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";

const baseDir = dirname(fileURLToPath(import.meta.url));
const wrapperPath = resolve(baseDir, "run_btg.sh");

function splitShellWords(input: string): string[] {
  const out: string[] = [];
  let current = "";
  let quote: "'" | '"' | null = null;
  let escaping = false;

  for (let i = 0; i < input.length; i += 1) {
    const ch = input[i];

    if (escaping) {
      current += ch;
      escaping = false;
      continue;
    }

    if (ch === "\\") {
      escaping = true;
      continue;
    }

    if (quote) {
      if (ch === quote) {
        quote = null;
      } else {
        current += ch;
      }
      continue;
    }

    if (ch === "'" || ch === '"') {
      quote = ch;
      continue;
    }

    if (/\s/.test(ch)) {
      if (current.length > 0) {
        out.push(current);
        current = "";
      }
      continue;
    }

    current += ch;
  }

  if (escaping) {
    current += "\\";
  }
  if (quote) {
    throw new Error("Unterminated quote in BTG command.");
  }
  if (current.length > 0) {
    out.push(current);
  }

  return out;
}

function renderOutput(stdout: string, stderr: string): string {
  const out = stdout.trim();
  const err = stderr.trim();

  if (out && err) {
    return `${out}\n\n[stderr]\n${err}`;
  }
  if (out) {
    return out;
  }
  if (err) {
    return `[stderr]\n${err}`;
  }
  return "No output.";
}

export default definePluginEntry({
  id: "btg",
  name: "BTG",
  description: "Runs BTG commands through run_btg.sh",
  register(api) {
    api.registerTool({
      name: "btg_runner",
      description:
        "Run a raw BTG command through bash run_btg.sh and return stdout/stderr.",
      parameters: {
        type: "object",
        additionalProperties: false,
        required: ["command"],
        properties: {
          command: {
            type: "string",
            minLength: 1
          },
          commandName: {
            type: "string"
          },
          skillName: {
            type: "string"
          }
        }
      },
      async execute(_toolCallId, params) {
        if (process.platform !== "linux") {
          throw new Error("btg_runner is Linux-only.");
        }

	const raw = params.command.trim();
	if (!raw) {
	  throw new Error("Provide a BTG command.");
	}

	const normalized = raw.toLowerCase().startsWith("btg ") || raw.toLowerCase() === "btg"
	  ? raw
	  : `btg ${raw}`;

	const argv = splitShellWords(normalized);

        const result = await new Promise<{ code: number; stdout: string; stderr: string }>(
          (resolvePromise, rejectPromise) => {
            const child = spawn("bash", [wrapperPath, ...argv], {
              cwd: baseDir,
              env: process.env
            });

            let stdout = "";
            let stderr = "";

            child.stdout.on("data", (chunk) => {
              stdout += String(chunk);
            });

            child.stderr.on("data", (chunk) => {
              stderr += String(chunk);
            });

            child.on("error", rejectPromise);

            child.on("close", (code) => {
              resolvePromise({
                code: code ?? 1,
                stdout,
                stderr
              });
            });
          }
        );

        const text = renderOutput(result.stdout, result.stderr);

        if (result.code !== 0) {
          throw new Error(text);
        }

        return {
          content: [{ type: "text", text }]
        };
      }
    });
  }
});
