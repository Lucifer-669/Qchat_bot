#!/bin/bash
echo "正在部署聊天机器人到Oracle Cloud..."

# 安装必要依赖
echo "安装系统依赖..."
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv git

# 创建项目目录
echo "创建项目目录..."
mkdir -p ~/chatbot
cd ~/chatbot

# 克隆项目代码
echo "克隆代码库..."
git clone https://github.com/your-repo/chatbot.git .

# 设置虚拟环境
echo "设置Python虚拟环境..."
python3 -m venv venv
source venv/bin/activate

# 安装Python依赖
echo "安装Python依赖..."
pip install -r requirements.txt

# 初始化配置文件
if [ ! -f ".env" ]; then
    echo "初始化.env配置文件..."
    cp .env.template .env
    echo "请编辑.env文件配置您的API密钥和其他设置"
fi

# 创建数据目录结构
echo "创建数据目录结构..."
mkdir -p data/logs
mkdir -p data/chat_history
mkdir -p data/cache
mkdir -p data/config

echo "部署完成！"
echo "请编辑.env文件后，使用以下命令启动机器人:"
echo "QQ机器人: python bot.py qq"
echo "或配置为系统服务(参见README)"