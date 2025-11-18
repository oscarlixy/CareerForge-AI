#!/bin/bash

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

clear

echo -e "${CYAN}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════════╗
║                                                                 ║
║       🚀 CareerForge AI - 一键部署到 Hugging Face                ║
║                                                                 ║
║              让 AI 助力你的职业发展！                              ║
║                                                                 ║
╚═══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"
echo ""

# 检查当前目录
if [ ! -f "app.py" ] || [ ! -f "Dockerfile" ]; then
    echo -e "${RED}❌ 错误：请在 CareerForge-完整代码包 文件夹中运行此脚本${NC}"
    echo ""
    echo "当前目录：$(pwd)"
    echo "请确保包含以下文件："
    echo "  • app.py"
    echo "  • requirements.txt"
    echo "  • Dockerfile"
    echo "  • README.md"
    echo "  • static/index.html"
    echo ""
    exit 1
fi

echo -e "${GREEN}✅ 检测到所有必需文件${NC}"
echo ""

# 显示文件列表
echo -e "${BLUE}📁 即将部署以下文件：${NC}"
echo "  ✓ app.py              - 后端服务器"
echo "  ✓ requirements.txt    - Python 依赖"
echo "  ✓ Dockerfile          - Docker 配置"
echo "  ✓ README.md           - Space 说明"
echo "  ✓ static/index.html   - 前端应用"
echo ""

# 步骤 1：获取用户信息
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}📝 步骤 1/5: 配置部署信息${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

read -p "请输入你的 Hugging Face 用户名: " HF_USERNAME
if [ -z "$HF_USERNAME" ]; then
    echo -e "${RED}❌ 用户名不能为空${NC}"
    exit 1
fi

read -p "请输入 Space 名称 [默认: careerforge-ai]: " SPACE_NAME
SPACE_NAME=${SPACE_NAME:-careerforge-ai}

echo ""
echo -e "${GREEN}✅ 用户名: ${CYAN}$HF_USERNAME${NC}"
echo -e "${GREEN}✅ Space 名称: ${CYAN}$SPACE_NAME${NC}"
echo -e "${GREEN}✅ Space 地址: ${BLUE}https://huggingface.co/spaces/$HF_USERNAME/$SPACE_NAME${NC}"
echo ""

read -p "信息正确吗？(y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}⚠️  已取消${NC}"
    exit 1
fi

echo ""

# 步骤 2：检查 Git
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}🔍 步骤 2/5: 检查 Git 环境${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if ! command -v git &> /dev/null; then
    echo -e "${RED}❌ Git 未安装${NC}"
    echo ""
    echo "请先安装 Git："
    echo "  Mac:     brew install git"
    echo "  Windows: https://git-scm.com/download/win"
    echo ""
    exit 1
fi

echo -e "${GREEN}✅ Git 已安装: $(git --version)${NC}"
echo ""

# 配置 Git 用户信息（如果未配置）
if [ -z "$(git config user.name)" ]; then
    read -p "请输入 Git 用户名: " GIT_NAME
    git config user.name "$GIT_NAME"
    echo -e "${GREEN}✅ 已设置 Git 用户名${NC}"
fi

if [ -z "$(git config user.email)" ]; then
    read -p "请输入 Git 邮箱: " GIT_EMAIL
    git config user.email "$GIT_EMAIL"
    echo -e "${GREEN}✅ 已设置 Git 邮箱${NC}"
fi

echo ""

# 步骤 3：初始化 Git 仓库
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}📦 步骤 3/5: 初始化 Git 仓库${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ -d ".git" ]; then
    echo -e "${YELLOW}⚠️  Git 仓库已存在，跳过初始化${NC}"
else
    echo "正在初始化 Git 仓库..."
    git init
    echo -e "${GREEN}✅ Git 仓库初始化完成${NC}"
fi

echo ""

# 步骤 4：添加远程仓库
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}🔗 步骤 4/5: 配置远程仓库${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

REMOTE_URL="https://huggingface.co/spaces/$HF_USERNAME/$SPACE_NAME"

# 检查是否已有 origin
if git remote | grep -q "origin"; then
    echo "移除旧的 origin..."
    git remote remove origin
fi

echo "添加远程仓库: $REMOTE_URL"
git remote add origin $REMOTE_URL
echo -e "${GREEN}✅ 远程仓库配置完成${NC}"
echo ""

# 步骤 5：提交并推送
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}🚀 步骤 5/5: 提交并推送代码${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo "添加所有文件..."
git add .

echo "提交更改..."
git commit -m "Initial commit: Deploy CareerForge AI to Hugging Face Space"

echo ""
echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                                 ║${NC}"
echo -e "${BLUE}║                  ⚠️  准备推送到 Hugging Face                    ║${NC}"
echo -e "${BLUE}║                                                                 ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}接下来会要求你输入：${NC}"
echo ""
echo -e "  ${CYAN}Username:${NC} $HF_USERNAME"
echo -e "  ${CYAN}Password:${NC} 使用你的 Hugging Face Access Token"
echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}🔑 如何获取 Access Token：${NC}"
echo ""
echo "  1️⃣  访问: ${BLUE}https://huggingface.co/settings/tokens${NC}"
echo "  2️⃣  点击 'New token' 按钮"
echo "  3️⃣  选择 'write' 权限 ⚠️"
echo "  4️⃣  点击 'Generate'"
echo "  5️⃣  复制生成的 token（以 hf_ 开头）"
echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

read -p "准备好 Token 了吗？按回车继续推送..." 

echo ""
echo "正在推送到 Hugging Face..."
echo ""

if git push origin main 2>&1; then
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                                 ║${NC}"
    echo -e "${GREEN}║                  🎉🎉🎉 推送成功！🎉🎉🎉                          ║${NC}"
    echo -e "${GREEN}║                                                                 ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${GREEN}✅ CareerForge AI 已成功上传到 Hugging Face！${NC}"
    echo ""
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${RED}⚠️  重要：还需要完成最后一步！${NC}"
    echo ""
    echo -e "${CYAN}📍 请访问你的 Space 设置页面：${NC}"
    echo -e "   ${BLUE}$REMOTE_URL/settings${NC}"
    echo ""
    echo -e "${CYAN}🔐 添加 DeepSeek API Key：${NC}"
    echo ""
    echo "  1️⃣  点击 'Settings' 标签"
    echo "  2️⃣  找到 'Repository secrets' 部分"
    echo "  3️⃣  点击 'New secret' 按钮"
    echo "  4️⃣  填写："
    echo -e "      Name:  ${GREEN}DEEPSEEK_API_KEY${NC}"
    echo -e "      Value: ${GREEN}sk-你的DeepSeek API密钥${NC}"
    echo "  5️⃣  点击 'Add' 按钮"
    echo ""
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${CYAN}💡 获取 DeepSeek API Key：${NC}"
    echo ""
    echo "  1. 访问: ${BLUE}https://platform.deepseek.com${NC}"
    echo "  2. 注册并登录"
    echo "  3. 点击左侧 'API Keys'"
    echo "  4. 创建新密钥"
    echo "  5. 充值 ¥10-20"
    echo ""
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${CYAN}⏳ 配置完成后：${NC}"
    echo ""
    echo "  • 等待 3-5 分钟让 Space 构建"
    echo "  • 访问 App 标签测试功能"
    echo "  • 生成一份简历试试！"
    echo ""
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${CYAN}🌐 你的应用地址：${NC}"
    echo -e "   ${BLUE}$REMOTE_URL${NC}"
    echo ""
    echo -e "${CYAN}📊 查看构建日志：${NC}"
    echo -e "   ${BLUE}$REMOTE_URL?logs=build${NC}"
    echo ""
    echo -e "${GREEN}祝你使用愉快！🚀✨${NC}"
    echo ""
else
    echo ""
    echo -e "${RED}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║                                                                 ║${NC}"
    echo -e "${RED}║                  ❌ 推送失败                                      ║${NC}"
    echo -e "${RED}║                                                                 ║${NC}"
    echo -e "${RED}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}可能的原因：${NC}"
    echo ""
    echo "  1. Access Token 不正确或权限不足"
    echo "  2. Space 尚未在 Hugging Face 创建"
    echo "  3. 网络连接问题"
    echo "  4. Token 已过期"
    echo ""
    echo -e "${YELLOW}解决方法：${NC}"
    echo ""
    echo "  1. 确保先在 HF 网站创建 Space："
    echo -e "     ${BLUE}https://huggingface.co/new-space${NC}"
    echo "  2. 确保 SDK 选择了 'Docker'"
    echo "  3. 获取新的 Access Token（需要 write 权限）："
    echo -e "     ${BLUE}https://huggingface.co/settings/tokens${NC}"
    echo "  4. 检查网络连接"
    echo ""
    echo "  然后重新运行此脚本。"
    echo ""
fi

