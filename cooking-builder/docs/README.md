# cooking-builder 文档

Cooking Suggest 容器化打包/部署文档索引。

| 文档 | 说明 |
| --- | --- |
| [packaging.md](./packaging.md) | 构建与离线打包（在构建机器上执行） |
| [deployment.md](./deployment.md) | 生产部署、升级回滚、数据迁移与运维 |

相关文件：

- [../README.md](../README.md)：项目总览与快速开始
- [../.env.example](../.env.example)：环境变量模板（配置项权威来源）
- [../docker-compose.yml](../docker-compose.yml)：运行编排（仅声明 image）
- [../docker-compose.build.yml](../docker-compose.build.yml)：构建覆盖文件

## 一分钟速览

```bash
# 构建机器：构建并打包
cd cooking-builder
vi .env                 # 确认 IMAGE_TAG / TARGET_PLATFORM / 密钥
./package.sh
# 产物：dist/cooking-suggest-<IMAGE_TAG>.tar.gz

# 生产服务器：加载并启动
tar xzf cooking-suggest-<tag>.tar.gz && cd cooking-suggest-<tag>
./load.sh
cp .env.example .env && vi .env
./start.sh
```
