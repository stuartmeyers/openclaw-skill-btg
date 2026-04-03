# BTG Setup

This BTG package includes both the executable plugin tool and the skill instructions that use it.

## Install From A Local Folder

```bash
openclaw plugins install /absolute/path/to/beforethought-play
```

## Install From ClawHub

```bash
openclaw plugins install clawhub:<package-id>
```

Replace `<package-id>` with the package id you publish.

## After Install

Start a new OpenClaw session or restart the gateway so the bundled skill is loaded.

## Verify

Check that the plugin is present:

```bash
openclaw plugins list
```

Then run a BTG command in chat:

```bash
/btg help
```

If the install is working, OpenClaw should execute the bundled `btg_runner` tool and return real BTG output.

## Runtime Files

The first real BTG run may create local runtime files in the installed package directory:

- `.api-key`
- `.profile-id`
- `.timezone`
- `.config/strategy.json`
- `logs/btg.log`

Those files are local runtime state and should stay out of the publishable source bundle.
