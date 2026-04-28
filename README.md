# tapd-skills

TAPD 相关 Agent Skills 集合，用于沉淀 TAPD OAuth、用户态 API、TAPD 需求、TestX 用例与需求关联等自动化流程。仓库采用通用 `skills/<skill-name>/SKILL.md` 结构，可被 `npx skills` 发现并安装到 Codex、Claude Code 等 agent。

## Skills

- `tapd-base`（目录 `skills/tapd-base`）：TAPD 用户态 OAuth、token 缓存、配置加载和通用用户态 API 调用。
- `tapd-story`（目录 `skills/tapd-story`）：TAPD 需求读取、更新，以及通过 TestX design 接口读取需求。
- `tapd-testx`（目录 `skills/tapd-testx`）：TestX repo/folder/case 操作，以及需求关联 TestX 用例。

## 串联使用

- 只做授权或通用 TAPD API：`tapd-base`
- 操作需求：`tapd-base` -> `tapd-story`
- 操作 TestX：`tapd-base` -> `tapd-testx`
- 从需求生成或关联 TestX 用例：`tapd-base` -> `tapd-story` -> `tapd-testx`

## npx skills 安装

推荐用通用 Skills CLI 安装。它会交互式选择 skill、agent、安装范围和安装方式。

```bash
npx skills add https://github.com/aicc-dev/tapd-skills
```

列出仓库里的 skills：

```bash
npx skills add https://github.com/aicc-dev/tapd-skills --list
```

安装全部 skills，并交互选择 agent：

```bash
npx skills add https://github.com/aicc-dev/tapd-skills --skill '*'
```

安装到 Codex 全局目录：

```bash
npx skills add https://github.com/aicc-dev/tapd-skills --skill '*' -a codex -g
```

安装到 Claude Code 全局目录：

```bash
npx skills add https://github.com/aicc-dev/tapd-skills --skill '*' -a claude-code -g
```

CI 或非交互安装：

```bash
npx skills add https://github.com/aicc-dev/tapd-skills --skill '*' -a codex -g -y
```

`tapd-story` 和 `tapd-testx` 依赖 `tapd-base`，推荐安装全部三个 skills。

## 手动安装

Codex 使用 `~/.codex/skills` 作为个人 skills 目录：

```bash
mkdir -p ~/.codex/skills
ln -s "$(pwd)/skills/tapd-base" ~/.codex/skills/tapd-base
ln -s "$(pwd)/skills/tapd-story" ~/.codex/skills/tapd-story
ln -s "$(pwd)/skills/tapd-testx" ~/.codex/skills/tapd-testx
```

Claude Code 使用 `~/.claude/skills` 作为个人 skills 目录：

```bash
mkdir -p ~/.claude/skills
ln -s "$(pwd)/skills/tapd-base" ~/.claude/skills/tapd-base
ln -s "$(pwd)/skills/tapd-story" ~/.claude/skills/tapd-story
ln -s "$(pwd)/skills/tapd-testx" ~/.claude/skills/tapd-testx
```

Claude Code 项目安装：

```bash
mkdir -p .claude/skills
ln -s "$(pwd)/skills/tapd-base" .claude/skills/tapd-base
ln -s "$(pwd)/skills/tapd-story" .claude/skills/tapd-story
ln -s "$(pwd)/skills/tapd-testx" .claude/skills/tapd-testx
```

安装后重启对应 agent。agent 会根据 `SKILL.md` 的 `name` 和 `description` 自动加载，也可以按名称显式触发。

## 配置

Codex 推荐配置文件：

```bash
mkdir -p ~/.codex/config
cp ~/.codex/skills/tapd-base/env.example ~/.codex/config/tapd-base.env
```

Claude Code 推荐配置文件：

```bash
mkdir -p ~/.claude/config
cp ~/.claude/skills/tapd-base/env.example ~/.claude/config/tapd-base.env
```

如果是在当前仓库内手动配置，也可以从 `skills/tapd-base/env.example` 复制。

至少需要填写 `TAPD_CLIENT_ID` 和 `TAPD_CLIENT_SECRET`。脚本会优先使用 `TAPD_ENV_FILE`；未显式指定时，会依次查找 `~/.codex/config/tapd-base.env`、`~/.claude/config/tapd-base.env`、当前工作目录 `.env` 和 `tapd-base/.env`。

## 发布注意

- 不提交真实 `.env`、token cache 或凭据。
- 不提交 `__pycache__`、`.DS_Store` 等本地生成文件。
- 每个 skill 目录必须包含 `SKILL.md`。
- 修改脚本后运行对应测试。
