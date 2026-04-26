import { runPluginCommandWithTimeout } from "openclaw/plugin-sdk/run-command";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { homedir } from "node:os";

import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";

const baseDir = dirname(fileURLToPath(import.meta.url));
const wrapperPath = resolve(baseDir, "run_btg.sh");
const supportedPlatforms = new Set(["linux", "darwin"]);

type LocalIdentityConfig = {
  displayName?: string;
  stateDir?: string;
};

function sanitizeSegment(input: string): string {
  const sanitized = input.trim().replace(/[^A-Za-z0-9._-]+/g, "-");
  return sanitized || "default";
}

function deriveStateDir(agentId?: string): string {
  const suffix = sanitizeSegment(agentId || "default");
  return resolve(homedir(), ".openclaw", `btg-state-${suffix}`);
}

function resolveLocalIdentityConfig(pluginConfig: Record<string, any> | undefined, agentId?: string): LocalIdentityConfig | null {
  if (!pluginConfig || !agentId) {
    return null;
  }

  const identities = pluginConfig.localIdentities;
  const identity = identities?.[agentId];

  if (!identity || typeof identity !== "object") {
    return null;
  }

  const displayName =
    typeof identity.displayName === "string" && identity.displayName.trim()
      ? identity.displayName.trim()
      : undefined;

  const stateDir =
    typeof identity.stateDir === "string" && identity.stateDir.trim()
      ? identity.stateDir.trim()
      : deriveStateDir(agentId);

  return {
    displayName,
    stateDir
  };
}

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
    api.registerTool((ctx) => {
      const localIdentity = resolveLocalIdentityConfig(api.pluginConfig as Record<string, any> | undefined, ctx.agentId);

      return {
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
          if (!supportedPlatforms.has(process.platform)) {
            throw new Error("btg_runner currently supports Linux and macOS only.");
          }

          const raw = params.command.trim();
          if (!raw) {
            throw new Error("Provide a BTG command.");
          }

          const commandText = raw.replace(/^\/btg(?=\s|$)/i, "btg");

          const normalized =
            commandText.toLowerCase().startsWith("btg ") || commandText.toLowerCase() === "btg"
              ? commandText
              : `btg ${commandText}`;

          const argv = splitShellWords(normalized);
          const childEnv: NodeJS.ProcessEnv = { ...process.env };

          if (localIdentity?.stateDir) {
            childEnv.BTG_STATE_DIR = localIdentity.stateDir;
          }
          if (localIdentity?.displayName) {
            childEnv.BTG_DISPLAY_NAME = localIdentity.displayName;
          }

          const result = await runPluginCommandWithTimeout({
            argv: ["bash", wrapperPath, ...argv],
            cwd: baseDir,
            env: childEnv,
            timeoutMs: 120000
          });

          const text = renderOutput(result.stdout, result.stderr);

          if (result.code !== 0 && !text.trim()) {
            throw new Error(`BTG command failed with exit code ${result.code}.`);
          }

          return {
            content: [{ type: "text", text }]
          };
        }
      };
    });
  }
});
