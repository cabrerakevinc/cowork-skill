# cowork-skill

Marketplace repo for the `cowork` plugin: Cowork OS as a plugin. One entrypoint, lean memory, workstations added by convention, a doctor that keeps the structure honest. The plugin itself, with its own README, lives in [`cowork/`](cowork/).

## Install

**Cowork desktop app:** download `cowork.plugin` from the [latest release](https://github.com/cabrerakevinc/cowork-skill/releases/latest) and open it in the Claude desktop app.

**Claude Code:**

```
/plugin marketplace add cabrerakevinc/cowork-skill
/plugin install cowork@cowork-skill
```

Update later with `/plugin marketplace update cowork-skill` and reinstall.

## Commands

`/cowork:bootstrap`, `/cowork:extend`, `/cowork:doctor`, `/cowork:end-session`. Details in [`cowork/README.md`](cowork/README.md). Version history in [`CHANGELOG.md`](CHANGELOG.md).

## Releasing (maintainers)

1. Bump `version` in `cowork/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` to the same number, and add a `## [x.y.z] - date` section to `CHANGELOG.md`.
2. Commit, then tag and push the tag:
   ```
   git tag v0.2.0
   git push origin main --tags
   ```
3. The Release workflow checks the three versions match, validates the plugin, builds `cowork.plugin`, and publishes a GitHub Release with that changelog section and the file attached. Nothing to zip by hand.

MIT licensed.
