---
name: aicc-tapd:base
description: TAPD 命名空间基础技能，包含 OAuth 授权、token 缓存、配置加载和通用 TAPD 用户态 API 调用。需要获取或复用 TAPD 用户态 token，或其它 aicc-tapd:* 技能要求先授权时使用。
---

# TAPD 基础用户态能力

使用这个 skill 处理 TAPD 用户态 OAuth、配置检查、token 缓存和通用 API 调用。它是 `aicc-tapd:*` 命名空间的基础技能，`aicc-tapd:story` 和 `aicc-tapd:testx` 都依赖本目录下的 `scripts`。

## 串联方式

- 只做授权或通用 API：使用 `aicc-tapd:base`
- 操作需求：先使用 `aicc-tapd:base` 确认 token，再使用 `aicc-tapd:story`
- 操作 TestX：先使用 `aicc-tapd:base` 确认 token，再使用 `aicc-tapd:testx`
- 从需求生成或关联 TestX 用例：按 `aicc-tapd:base` -> `aicc-tapd:story` -> `aicc-tapd:testx` 串联

## 强制配置检查

执行 OAuth 或 TAPD API 前，先检查 `TAPD_CLIENT_ID` 和 `TAPD_CLIENT_SECRET`：

```bash
python3 tapd-base/scripts/tapd_user_oauth_demo.py check-config
```

如果任一为空、缺失或仍是占位值，停止后续 TAPD 操作，并提醒用户先配置凭据。

## 配置

推荐把真实配置放在 skill 目录外。

Codex：

```bash
mkdir -p ~/.codex/config
cp tapd-base/env.example ~/.codex/config/tapd-base.env
```

Claude Code：

```bash
mkdir -p ~/.claude/config
cp tapd-base/env.example ~/.claude/config/tapd-base.env
```

至少填写：

```bash
TAPD_CLIENT_ID=your_client_id
TAPD_CLIENT_SECRET=your_client_secret
```

脚本默认按这个顺序找配置：

1. `TAPD_ENV_FILE`
2. `~/.codex/config/tapd-base.env`
3. `~/.claude/config/tapd-base.env`
4. 当前工作目录 `.env`
5. `tapd-base/.env`

默认 scope 是：

```bash
TAPD_SCOPES=user story#read story#write
```

默认 token cache：

```bash
~/.codex/memories/tapd-base/session.json
```

如果只存在 Claude Code 配置文件、没有 Codex 配置文件，默认使用：

```bash
~/.claude/tapd-base/session.json
```

## OAuth 流程

启动本地回调授权：

```bash
python3 tapd-base/scripts/tapd_user_oauth_demo.py authorize
```

直接打开默认浏览器：

```bash
python3 tapd-base/scripts/tapd_user_oauth_demo.py authorize --open
```

只打印授权 URL：

```bash
python3 tapd-base/scripts/tapd_user_oauth_demo.py show-url
```

已有 TAPD 回跳 code 时直接换 token：

```bash
python3 tapd-base/scripts/tapd_user_oauth_demo.py exchange-code \
  --code your_callback_code \
  --workspace-id 32131908
```

## 通用 API 调用

用缓存 token 调用户态 API：

```bash
python3 tapd-base/scripts/tapd_user_api.py /users/info
```

调用任意 TAPD 用户态 API：

```bash
python3 tapd-base/scripts/tapd_user_api.py \
  /api/testx/case/v1/namespaces/32131908/repos \
  --query Offset=0 \
  --query Limit=20
```

## 维护注意事项

- TAPD 回调里会带 `code`、`state`、`resource`
- TAPD 文档说明 `code` 有效期 5 分钟
- 当前缓存的 token 只用于用户态 TAPD API
- 不提交真实 `.env`、token cache 或凭据
