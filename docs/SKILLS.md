# Skill Compatibility

`cronctl` now ships its skill template in the conservative subset that overlaps well across current Agent Skills consumers.

Official references:

- Anthropic custom skills: <https://support.claude.com/en/articles/11804320-how-to-create-custom-skills>
- Anthropic skills repo: <https://github.com/anthropics/skills>
- OpenCode skills: <https://opencode.ai/docs/agents/skills>
- OpenClaw skills: <https://openclaw.ai/docs/core-concepts/skills>

## What the ecosystem expects

- **Anthropic custom skills / official Anthropic skills repo**
  - A skill is a folder with a `SKILL.md` file.
  - `SKILL.md` starts with YAML frontmatter and must include `name` and `description`.
  - Anthropic's custom-skill guide keeps descriptions short and shows folder-based packaging.
- **OpenCode**
  - Scans common skill roots such as `.opencode/skills`, `.claude/skills`, `.agents/skills`, and global skill directories.
  - Expects a `SKILL.md` file inside a folder whose name matches the skill name.
  - Recognizes `name`, `description`, `license`, `compatibility`, and `metadata`, and ignores unknown fields.
- **OpenClaw**
  - Reads skills from a workspace `skills/` directory or `~/.openclaw/skills`.
  - Uses `SKILL.md` plus YAML frontmatter, but adds OpenClaw-specific optional keys and metadata rules.
  - Its `metadata.openclaw` contract is more specialized than the common Agent Skills subset.

## Design choices in cronctl

To stay portable across Claude-oriented skills, OpenCode, and OpenClaw, cronctl now uses the stricter common subset:

- Skill folder name: `cronctl`
- Skill file name: `SKILL.md`
- Frontmatter fields: `name`, `description`, `license`
- Description: short enough to stay compatible with Anthropic's guidance
- No nested `metadata` or OpenClaw-only frontmatter in the shipped template

This avoids portability problems where one client accepts nested metadata or custom keys and another client rejects or ignores them differently.

## Installed layout

`cronctl init --skill-path <skills-root>` now writes:

```text
<skills-root>/
└── cronctl/
    └── SKILL.md
```

Examples:

- Claude-style project skills: `.claude/skills/cronctl/SKILL.md`
- OpenCode project skills: `.opencode/skills/cronctl/SKILL.md` or `.agents/skills/cronctl/SKILL.md`
- OpenClaw workspace skills: `skills/cronctl/SKILL.md`

## Recommended commands

```bash
# Claude-style project skill
uv run python -m cronctl init --non-interactive --skill-path .claude/skills

# OpenCode project skill
uv run python -m cronctl init --non-interactive --skill-path .opencode/skills

# OpenClaw workspace skill
uv run python -m cronctl init --non-interactive --skill-path skills
```

For the public installer:

```bash
CRONCTL_INSTALL_SKILL_PATH=.claude/skills \
  bash <(curl -fsSL https://raw.githubusercontent.com/jhleee/cronctl/main/install.sh)
```

## Why not use OpenClaw-only metadata?

OpenClaw supports extra frontmatter such as `homepage`, `user-invocable`, `disable-model-invocation`, and specialized `metadata.openclaw` requirements. Those are useful, but they are not the safest common denominator across the broader skills ecosystem.

cronctl therefore ships a portable default template first. If you need OpenClaw-only gating or slash-command behavior, layer it on in your local copy after `cronctl` installs the base `cronctl/SKILL.md`.
