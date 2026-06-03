# Contributing to Navigator

## Skill versioning convention

Each skill carries its own `version:` in the `SKILL.md` frontmatter, bumped with
[semver](https://semver.org/) **per skill** on any material change to that
skill's behavior, steps, functions, or templates:

- **patch** (x.y.**z**) — typo/wording fixes, no behavioral change
- **minor** (x.**y**.0) — new steps, functions, templates, or options (backward compatible)
- **major** (**x**.0.0) — removed/renamed functions or templates, or reworked workflow

The skill `version:` is independent of the plugin version in
`.claude-plugin/plugin.json` / `marketplace.json` (those track the release as a
whole). Do **not** retro-version every skill on a plugin bump — only bump a
skill when its own `SKILL.md` materially changes.

> When in doubt, bump the skill minor on a feature add and major when you delete
> or rename a referenced function/template (a consumer following the old SKILL.md
> would break).
