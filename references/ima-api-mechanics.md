# IMA API 归档机制速查（实测，Step 0.7 参考）

## 可用
- `import_urls`：导入网页/微信文章；按 URL 去重；`folder_id` 必填（根目录=kb_id）。
  - 工具：`scripts/import_urls_to_ima.sh <url文件|单个URL> [--folder <folder_id>]`
- `add_knowledge`：`media_type=11` + `note_info.content_id` 归类笔记。
- `get_knowledge_list`：浏览；`folder_id` 省略=根目录；`media_type=99`=文件夹。
- `search_knowledge`：返回 `parent_folder_id`，可验证归属。
- `get_media_info`：取 `url_info.url`（微信文章/网页/文件的原始 URL）。

## 无效 / 不存在
- `move_knowledge`：**静默 no-op 桩**（36 组合全试）。字段 `src_knowledge_base_id`/`dst_knowledge_base_id` 存在，但 `media_ids` 传值后无任何效果。
- `wiki/v1/delete_knowledge`、`remove_knowledge`、`delete_media`、`update_knowledge`：端点不存在（空响应）。
- `note/v1/move_note`、`delete_note`：不存在。
- 文件类（media_type=1，PDF/Word/PPT）：无法迁移。

## 迁移可行路径
1. web/微信（media_type=2/6）：记录原 URL → 用 `import_urls_to_ima.sh <url> --folder <目标>` 重导入 = 迁移。
2. 笔记（media_type=11）：`add_knowledge(mt=11, note_info.content_id=<note_id>)` = 归入目标 folder。
3. 文件类：无解；新建时指定 folder，已入库的无法移动。

## 常见坑
- 根目录 `get_knowledge_list` 含"最近添加"全局条目，**不代表归属根目录**；验收看目标文件夹。
- `update_note` 的 updates 是 **内容块** 枚举（`BlockUpdateAction`），与移动归属无关；且需顶层 `note_id`+`user_request_id`。
- 站点适配器风控：`Navigation rejected` / `响应不是有效 JSON`，重试或换源。

## WorkBuddy 版实测补充（2026-11-01，v1.1.0）

### 正确的 API 端点与凭证（踩坑修正）
- **Base**：`https://ima.qq.com/openapi/wiki/v1/`（⚠️ 不是 `openapi.ima.qq.com`——该域名全网 NXDOMAIN）
- **凭证头**：`ima-openapi-clientid` / `ima-openapi-apikey`（⚠️ 不是 `client_id`/`api_key`）
- **绕过系统代理**：本机代理对部分腾讯域 502，所有 IMA/COS 请求需 `ProxyHandler({})` 直连
- **COS PUT 签名**：标准 `q-sign-algorithm=sha1`，**FormatString 必须含 host header**（`q-header-list=host`），否则 SignatureDoesNotMatch 403。完整链路：`create_media` → COS PUT → `add_knowledge`（见 scripts/sync_to_ima_wb.py 的 cos_put）

### search_knowledge 不稳定降级链路（实战验证）
- search_knowledge 时常 502/空返回（曾跨 30 分钟不可用）。**降级路径**：
  1. `get_knowledge_list`（limit≤50，**limit=100 会返回空**）分页拉全量建索引（cursor 翻页）
  2. 本地标题包含匹配定位素材
  3. `get_media_info` 取 `url_info.url` 下载原文（TXT/MD 直接读）
- folder 子列表：**直调 API 传 folder_id 常返回空**，用 ima-mcp 工具传 folder_id 才可靠（folder 结构 folder_7509xxxx 一类）；按路径逐级下钻（如 拆书课→拆AI工作坊-杨辉→20261101）

### get_knowledge_list 返回结构
- 条目在 `data.knowledge_list`（不是顶层）；`media_type: 99`=文件夹 / 9=图片 / 6=微信文章 / 7=Markdown / 11=笔记 / 1=PDF / 15=音频
- 图片下载：`get_media_info` → `url_info.url` 直接 GET
