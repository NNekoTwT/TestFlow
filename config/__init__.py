# 该文件用于在 Django 启动时注册 MySQL 驱动。
# 实际安装动作放在 settings.py 中（根据 DB_ENGINE 决定），
# 避免测试使用 SQLite 时产生无谓的 MySQL 驱动依赖。
