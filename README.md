## 新克隆仓库必做

从 Git 拉取代码后，请按顺序执行（在项目根目录 `ModelGoAgent/` 下）：

```bash
# 1. 拉取子模块（LicenseAtlas 数据源，未 --recursive 克隆时必做）
git submodule update --init vendor/license.atlas

# 2. 安装 Python 依赖（见下方「项目依赖」）
pip install -r requirements.txt
# 或按下方列表逐项 pip install

# 3. 配置环境变量（复制并填写 API Key 等）
# cp .env.example .env

# 4. 生成本地许可全文缓存（bodies/ 不在仓库内，每台机器都要跑）
make sync-atlas
# 等价: python scripts/sync_license_atlas.py

# 5. 可选：确认 LicenseAtlas 已就绪
make check-atlas
```

**说明：**

| 步骤 | 原因 |
|------|------|
| `git submodule update --init` | `vendor/license.atlas` 为子模块，普通 `git clone` 不会带出其中文件 |
| `make sync-atlas` | 从子模块生成 `scripts/license_atlas/bodies/*.txt`（约 955 个文件）；许可建模在 `license_raw` 之后会读此处 |
| `index.json` | 已随仓库提交，无需单独下载 |
| `bodies/` | **不提交**；未执行 sync 时，未知许可的全文回退到 SPDX 远程，AI/自定义许可命中率会下降 |

推荐克隆时一次性带子模块：

```bash
git clone --recursive <仓库 URL>
```

若已克隆但未带子模块，在项目根目录执行 `git submodule update --init vendor/license.atlas` 即可。

---

## 运行方式

启动服务：

```bash
python agent/main.py
```

运行测试：

```bash
python agent/test/test_workflow.py
```

调试追踪：https://smith.langchain.com/

### LicenseAtlas（许可全文来源）

[LicenseAtlas](https://github.com/morningD/license.atlas) 提供约 956 条许可全文；`fetch_license_text` 优先级为：`license_raw` → **LicenseAtlas** → SPDX/OSI/GNU。

- 仓库内路径：`scripts/license_atlas/index.json`（已提交）、`scripts/license_atlas/bodies/`（本地生成，已 gitignore）
- 更新 Atlas 数据：升级 `vendor/license.atlas` 子模块 commit 后重新 `make sync-atlas`

## 项目依赖

安装项目依赖
```
pip install langgraph==0.2.74
pip install langchain-openai==0.3.6
pip install fastapi==0.115.8
pip install uvicorn==0.34.0
pip install gradio==5.18.0
pip install e2b-code-interpreter python-dotenv
```


使用Docker的方式运行PostgreSQL数据库

1. 进入官网 https://www.docker.com/ 下载安装Docker Desktop软件并安装，安装完成后打开软件

2. 打开命令行终端，`cd agent`，PostgreSQL的docker配置文件为docker-compose.yml。运行 `docker-compose up -d` 命令后台启动PostgreSQL数据库服务。运行成功后可在Docker Desktop软件中进行管理操作或使用命令行操作或使用指令。

3. 因为LangGraph的PostgresStore需要使用到pgvector，因此需要在容器中按照如下步骤进行操作，直接使用Docker Desktop软件中进行操作
```
apt update
apt install -y git build-essential postgresql-server-dev-15
git clone --branch v0.7.0 https://github.com/pgvector/pgvector.git
cd pgvector
make
make install
```

4. 验证安装，检查扩展文件是否安装成功
`ls -l /usr/share/postgresql/15/extension/vector*`

5. 接下来，若要在脚本中进行使用，首先在系统环境中需要安装PostgreSQL 的开发库（libpq），因为 psycopg 需要它来编译或运行,根据自己的操作系统选择进行安装

6. 最后，再安装相关依赖包
pip install langgraph-checkpoint-postgres
pip install psycopg psycopg-pool


出现OSError: exception: access violation writing 0x0000000000000000，更新psycopg 3 binarypip install --upgrade "psycopg[binary]"