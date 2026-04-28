---
name: tapd-story
description: TAPD 需求技能，用于读取、更新 TAPD 需求，以及通过 TestX design 接口读取需求。依赖 tapd-base 提供 OAuth 和用户态 API token；需要把需求关联到 TestX 时可继续使用 tapd-testx。
---

# TAPD Story 操作

使用这个 skill 处理 TAPD 需求读取、更新，以及 TestX design 侧的需求读取。执行前必须先确认相邻目录存在 `tapd-base`，并按 `tapd-base` 完成配置和 token 检查。

## 串联方式

- 需求读取/更新：`tapd-base` -> `tapd-story`
- 读取需求后创建或关联 TestX 用例：`tapd-base` -> `tapd-story` -> `tapd-testx`

## 前置检查

命令示例默认已设置 skills 根目录。Codex 全局安装通常是 `~/.codex/skills`，Claude Code 全局安装通常是 `~/.claude/skills`：

```bash
export TAPD_SKILLS_ROOT="${TAPD_SKILLS_ROOT:-$HOME/.codex/skills}"
```

先检查 TAPD 用户态配置：

```bash
python3 "$TAPD_SKILLS_ROOT/tapd-base/scripts/tapd_user_oauth_demo.py" check-config
```

如果没有可用 token，先通过 `tapd-base` 完成授权：

```bash
python3 "$TAPD_SKILLS_ROOT/tapd-base/scripts/tapd_user_oauth_demo.py" authorize
```

## 已验证规则

- 默认 `TAPD_SCOPES=user story#read story#write` 覆盖需求读取和更新场景
- TestX design 读取需求时，路径里两个 workspace 都必须填真实 `workspace_id`

正确：

```text
/api/testx/design/v2/namespaces/{workspace_id}/workspaces/{workspace_id}/stories
```

错误：

```text
/api/testx/design/v2/namespaces/{workspace_id}/workspaces/0/stories
```

错误写法会触发：

```text
项目关联的workspace不正确
```

## 读取 TAPD 需求

```bash
python3 "$TAPD_SKILLS_ROOT/tapd-story/scripts/tapd_story.py" \
  story-get \
  --workspace-id 32131908 \
  --story-id 1132131908001006860
```

## 更新 TAPD 需求

按 TAPD 官方“更新需求”接口封装，使用 `POST /stories`，必填 `id` 和 `workspace_id`。`payload-file` 可以直接放需求字段对象，也可以放带 `Story` 键的对象。命令行里的 `--workspace-id` 和 `--story-id` 会覆盖 payload 中的同名字段，避免误更新其它需求。

```bash
python3 "$TAPD_SKILLS_ROOT/tapd-story/scripts/tapd_story.py" \
  story-update \
  --workspace-id 32131908 \
  --story-id 1132131908001006860 \
  --payload-file /absolute/path/to/story.json
```

payload 示例：

```json
{
  "Story": {
    "name": "更新后的需求标题",
    "priority_label": "高",
    "owner": "tester;"
  }
}
```

## 通过 TestX design 接口读取需求

```bash
python3 "$TAPD_SKILLS_ROOT/tapd-story/scripts/tapd_story.py" \
  design-story-get \
  --workspace-id 32131908 \
  --story-id 1132131908001006860
```
