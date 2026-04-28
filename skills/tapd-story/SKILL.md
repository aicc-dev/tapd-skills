---
name: tapd-story
description: TAPD 需求技能，用于读取、更新 TAPD 需求，读取/新增/修改需求评论，以及通过 TestX design 接口读取需求；读取需求时只处理 API 返回的文本字段。依赖 tapd-base 提供 OAuth 和用户态 API token；需要把需求关联到 TestX 时可继续使用 tapd-testx。
---

# TAPD Story 操作

使用这个 skill 处理 TAPD 需求读取、更新、需求评论读取/新增/修改，以及 TestX design 侧的需求读取。执行前必须先确认相邻目录存在 `tapd-base`，并按 `tapd-base` 完成配置和 token 检查。

## 串联方式

- 需求读取/更新/评论：`tapd-base` -> `tapd-story`
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

- 默认 `TAPD_SCOPES=user story#read story#write comment#read comment#write` 覆盖需求读取、更新和评论场景
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

## 需求读取边界

- 读取需求描述时，只使用 `story-get` 或 `design-story-get` 返回的文本字段，例如 `name`、`description`、`status`、`owner`、`developer`、`created`、`modified`。
- `description` 可能是 HTML。可以基于其中的文字内容做摘要；遇到 `<img>`、附件、截图、相对图片路径或富文本媒体标签时，只说明“描述中包含图片/附件，未解析图片内容”。
- 不要为了补全截图里的信息调用浏览器、chrome-devtools、图片下载、OCR、视觉模型或其它图像读取流程，除非用户在当前请求中明确要求解析图片。
- 当用户只是要求“看下需求描述”时，输出文本内容和必要的元信息即可；不要主动打开 TAPD 页面或截图资源。

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

## 读取 TAPD 需求评论

按 TAPD 官方“获取评论”接口封装，使用 `GET /comments`。读取某条需求的评论时传 `--story-id`，脚本会默认使用 `entry_type=stories` 和 `entry_id=<story_id>`。也可以传 `--comment-id` 读取指定评论，或传 `--description`、`--limit`、`--page`、`--order`、`--fields` 控制查询、分页、排序和字段。

注意：TAPD 的 `description` 参数不等同于稳定的“包含文本”搜索。需要按页面文本查找评论时，优先使用 `comment-find`，它会读取评论后在本地剥离 HTML 并做关键词包含匹配。

```bash
python3 "$TAPD_SKILLS_ROOT/tapd-story/scripts/tapd_story.py" \
  comment-list \
  --workspace-id 32131908 \
  --story-id 1132131908001006860 \
  --limit 50 \
  --order "created desc"
```

## 按文本查找 TAPD 需求评论

```bash
python3 "$TAPD_SKILLS_ROOT/tapd-story/scripts/tapd_story.py" \
  comment-find \
  --workspace-id 32131908 \
  --story-id 1132131908001006860 \
  --keyword "hello from browser"
```

## 读取 TAPD 需求变更历史

需求评论也会出现在 `story_changes` 的 `comment` 或 `field_changes` 字段中。需要对照页面动态时可以使用：

```bash
python3 "$TAPD_SKILLS_ROOT/tapd-story/scripts/tapd_story.py" \
  story-change-list \
  --workspace-id 32131908 \
  --story-id 1132131908001006860 \
  --limit 100 \
  --order "created desc"
```

## 新增 TAPD 需求评论

按 TAPD 官方“添加评论接口”封装，使用 `POST /comments`。需求评论默认 `entry_type=stories`，必填 `workspace_id`、`story_id`、`description` 和 `author`；回复评论时可选传 `--root-id` 或 `--reply-id`。

```bash
python3 "$TAPD_SKILLS_ROOT/tapd-story/scripts/tapd_story.py" \
  comment-add \
  --workspace-id 32131908 \
  --story-id 1132131908001006860 \
  --description "这个需求需要补充验收标准" \
  --author tester
```

## 修改 TAPD 评论

按 TAPD 官方“更新评论接口”封装，使用 `POST /comments`。必填 `workspace_id`、`comment_id` 和 `description`；需要记录变更人时可选传 `--change-creator`。

```bash
python3 "$TAPD_SKILLS_ROOT/tapd-story/scripts/tapd_story.py" \
  comment-update \
  --workspace-id 32131908 \
  --comment-id 1020355782058781915 \
  --description "更新后的评论内容" \
  --change-creator tester
```
