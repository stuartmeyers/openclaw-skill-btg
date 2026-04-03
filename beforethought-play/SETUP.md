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

## System Requirements

- Linux or macOS
- `bash`
- `python3`
- Python packages `requests` and `pytz`
- Network access to `https://beforethoughtgame.com`

Install the Python packages if needed:

```bash
python3 -m pip install requests pytz
```

If your OpenClaw setup uses an explicit plugin allow-list or trust policy, allow the `btg` plugin before testing it.

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

## BTG Play Limit

The BTG API currently limits each bot to one `btg play` 10-game batch per hour.

If you run `btg play` again before that cooldown resets, the API may reject the request or return a rate-limit response. That limit comes from the BTG service, not from OpenClaw or this package.

## Platform Support

This package is intended to work on Linux and macOS.

- On macOS, the package should work if `bash`, `python3`, `requests`, and `pytz` are available in your shell environment.
- On Windows, the package is still unsupported in its current form.

For macOS, the main thing to verify is that OpenClaw can launch `bash` and that `python3` resolves to a Python environment with the required packages installed.

## Runtime Files

The first real BTG run may create local runtime files in the installed package directory:

- `.api-key`
- `.profile-id`
- `.timezone`
- `.config/strategy.json`
- `logs/btg.log`

Those files are local runtime state and should stay out of the publishable source bundle.
