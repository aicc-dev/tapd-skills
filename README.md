# tapd-skills

TAPD 相关 Codex skills 集合，用于沉淀 TAPD OAuth、用户态 API、TAPD 需求、TestX 用例与需求关联等自动化流程。

## Skills

- `aicc-tapd:base`（目录 `tapd-base`）：TAPD 用户态 OAuth、token 缓存、配置加载和通用用户态 API 调用。
- `aicc-tapd:story`（目录 `tapd-story`）：TAPD 需求读取、更新，以及通过 TestX design 接口读取需求。
- `aicc-tapd:testx`（目录 `tapd-testx`）：TestX repo/folder/case 操作，以及需求关联 TestX 用例。

## 串联使用

- 只做授权或通用 TAPD API：`aicc-tapd:base`
- 操作需求：`aicc-tapd:base` -> `aicc-tapd:story`
- 操作 TestX：`aicc-tapd:base` -> `aicc-tapd:testx`
- 从需求生成或关联 TestX 用例：`aicc-tapd:base` -> `aicc-tapd:story` -> `aicc-tapd:testx`

## Codex 安装

把需要使用的 skill 目录复制或软链到 `~/.codex/skills`，然后重启 Codex。

```bash
mkdir -p ~/.codex/skills
ln -s "$(pwd)/tapd-base" ~/.codex/skills/tapd-base
ln -s "$(pwd)/tapd-story" ~/.codex/skills/tapd-story
ln -s "$(pwd)/tapd-testx" ~/.codex/skills/tapd-testx
```

## Claude Code 安装

Claude Code 使用 `~/.claude/skills` 作为个人 skills 目录，也支持项目内 `.claude/skills`。

个人安装：

```bash
mkdir -p ~/.claude/skills
ln -s "$(pwd)/tapd-base" ~/.claude/skills/tapd-base
ln -s "$(pwd)/tapd-story" ~/.claude/skills/tapd-story
ln -s "$(pwd)/tapd-testx" ~/.claude/skills/tapd-testx
```

项目安装：

```bash
mkdir -p .claude/skills
ln -s "$(pwd)/tapd-base" .claude/skills/tapd-base
ln -s "$(pwd)/tapd-story" .claude/skills/tapd-story
ln -s "$(pwd)/tapd-testx" .claude/skills/tapd-testx
```

Claude Code 会根据 `SKILL.md` 的 `description` 自动加载，也可以用 `/aicc-tapd:base`、`/aicc-tapd:story` 或 `/aicc-tapd:testx` 显式触发。

正式发布到 GitLab/GitHub 后，也可以先 clone 仓库，再按同样方式安装子目录。

## 配置

Codex 推荐配置文件：

```bash
mkdir -p ~/.codex/config
cp tapd-base/env.example ~/.codex/config/tapd-base.env
```

Claude Code 推荐配置文件：

```bash
mkdir -p ~/.claude/config
cp tapd-base/env.example ~/.claude/config/tapd-base.env
```

至少需要填写 `TAPD_CLIENT_ID` 和 `TAPD_CLIENT_SECRET`。脚本会优先使用 `TAPD_ENV_FILE`；未显式指定时，会依次查找 `~/.codex/config/tapd-base.env`、`~/.claude/config/tapd-base.env`、当前工作目录 `.env` 和 `tapd-base/.env`。

## 发布注意

- 不提交真实 `.env`、token cache 或凭据。
- 不提交 `__pycache__`、`.DS_Store` 等本地生成文件。
- 每个 skill 目录必须包含 `SKILL.md`。
- 修改脚本后运行对应测试。
