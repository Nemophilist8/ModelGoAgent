## 运行方式
启动服务 `python agent/main.py `   

运行测试 `python test/test_workflow.py`

debug https://smith.langchain.com/

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