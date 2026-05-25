# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Mini LLM Gateway — 一个轻量的 LLM API 代理网关，接收 Anthropic Claude API 格式请求，转发到不同上游 Provider（MiniMax、Kimi、智谱等）。支持多模型管理、SSE 流式响应、用量统计和 Web Dashboard。

## Commands

```bash
# 开发模式运行（热重载）
python run.py

# 生产模式运行
pip install -e .
mini-llm-gateway --host 0.0.0.0 --port 8080
```

默认监听 `0.0.0.0:8080`，配置在 `config.yaml`。

## Architecture

**框架**: FastAPI + Uvicorn + httpx（异步代理）

**请求流**: Claude Code → `/anthropic/v1/messages` → proxy.py 查找模型配置 → 转发到 `{base_url}/v1/messages` → 返回响应（含 SSE 流式）

**核心单例**:
- `ModelManager`（`gateway/models/manager.py`）— 管理模型配置，持久化到 `data/models.json`，使用 FileLock 保证并发安全
- `StatsCollector`（`gateway/stats/collector.py`）— 记录请求统计，持久化到 `data/stats.json`，支持按小时聚合，历史上限 10 万条

**API 路由**:
- `gateway/api/proxy.py` — 代理转发核心，`/anthropic/v1/messages` 和 `/anthropic/v1/messages/count_tokens`
- `gateway/api/models.py` — 模型列表接口，`/anthropic/v1/models`
- `gateway/api/admin.py` — 管理 API（`/v1/admin/*`），仅限 localhost 访问
- `gateway/web/router.py` — 静态页面路由（`/config`、`/dashboard`）

**前端**: 纯 HTML + CSS + JS（`static/`），无构建步骤。使用 CSS 变量实现深色/浅色主题切换，主题偏好存 localStorage。Dashboard 使用 Chart.js 绘制趋势图。

**配置**:
- `config.yaml` — 服务配置（host/port/CORS）
- `data/models.json` — 模型配置（gitignore，含 API Key）

## Key Design Decisions

- 代理层只做请求转发，不转换请求/响应格式，上游服务需自行兼容 Anthropic API 格式
- `base_url` 配置需指向兼容 Anthropic `/v1/messages` 路径的上游服务根地址
- Admin API 通过 `check_localhost()` 限制仅本地访问
- `gateway/providers/` 目录已从 setuptools 包中排除（`pyproject.toml` exclude），Provider 机制未完成集成
