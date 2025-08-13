# 安全指南

本文档提供了 libvirt-mcp-server 的安全配置指南和最佳实践，确保在生产环境中安全地部署和运行服务。

## 🔒 安全原则

### 最小权限原则

- **只授予必要权限**：仅启用业务需要的 libvirt 操作
- **用户权限隔离**：使用专用的服务账户运行服务
- **网络访问控制**：限制服务的网络访问和暴露端口

### 纵深防御

- **多层安全控制**：在网络、主机、应用和数据层面实施安全措施
- **审计和监控**：记录所有操作并实时监控异常活动
- **定期安全评估**：持续评估和改进安全配置

## 🛡️ 配置安全

### 1. Libvirt 连接安全

#### 使用只读连接（推荐用于监控场景）

```yaml
libvirt:
  uri: "qemu:///system"
  readonly: true  # 启用只读模式
  timeout: 30
```

#### 远程连接安全

```yaml
libvirt:
  # 使用 SSH 隧道进行远程连接
  uri: "qemu+ssh://libvirt-user@remote-host/system"
  # 或使用 TLS 加密连接
  # uri: "qemu+tls://remote-host/system"
```

### 2. 操作权限控制

#### 最小权限配置示例

```yaml
security:
  auth_required: true
  allowed_operations:
    # 仅允许查询操作
    - "domain.list"
    - "domain.info"
    - "domain.stats"
    - "host.info"
    - "network.list"
    - "storage.list"
    
    # 注释掉危险操作
    # - "domain.start"
    # - "domain.stop"
    # - "domain.create"
    # - "domain.delete"
```

#### 生产环境权限配置

```yaml
security:
  auth_required: true
  allowed_operations:
    # 基础查询操作
    - "domain.list"
    - "domain.info"
    - "domain.stats"
    - "domain.getxml"
    
    # 安全的管理操作
    - "domain.start"
    - "domain.stop"
    - "domain.reboot"
    
    # 系统信息
    - "host.info"
    - "network.list"
    - "storage.list"
    
    # 绝对不要启用的危险操作
    # - "domain.create"   # 创建虚拟机
    # - "domain.delete"   # 删除虚拟机
    # - "domain.attach"   # 附加设备
    # - "domain.detach"   # 分离设备
  
  audit_log: true
  max_concurrent_ops: 5  # 限制并发操作数
```

### 3. 网络安全

#### 本地访问（推荐）

```yaml
mcp:
  transport: "stdio"  # 使用标准输入输出，最安全
```

#### HTTP/SSE 访问安全配置

```yaml
mcp:
  transport: "http"
  host: "127.0.0.1"  # 仅绑定本地回环地址
  port: 8000
```

#### 反向代理配置（使用 Nginx）

```nginx
server {
    listen 443 ssl http2;
    server_name libvirt-mcp.example.com;
    
    # SSL 配置
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    # 访问控制
    allow 10.0.0.0/8;    # 内网访问
    allow 192.168.0.0/16; # 局域网访问
    deny all;
    
    # 反向代理到 MCP 服务器
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 安全头
        proxy_set_header X-Content-Type-Options nosniff;
        proxy_set_header X-Frame-Options DENY;
        proxy_set_header X-XSS-Protection "1; mode=block";
    }
}
```

## 🔐 身份验证和授权

### 1. 系统用户管理

#### 创建专用服务用户

```bash
# 创建专用用户和组
sudo groupadd libvirt-mcp
sudo useradd -r -g libvirt-mcp -d /opt/libvirt-mcp-server -s /bin/bash libvirt-mcp

# 添加到 libvirt 组以访问 libvirt
sudo usermod -a -G libvirt libvirt-mcp

# 设置目录权限
sudo chown -R libvirt-mcp:libvirt-mcp /opt/libvirt-mcp-server
sudo chmod 750 /opt/libvirt-mcp-server
```

### 2. 文件权限

```bash
# 配置文件权限
sudo chown root:libvirt-mcp /etc/libvirt-mcp-server/config.yaml
sudo chmod 640 /etc/libvirt-mcp-server/config.yaml

# 日志文件权限
sudo chown libvirt-mcp:libvirt-mcp /var/log/libvirt-mcp-server/
sudo chmod 755 /var/log/libvirt-mcp-server/
```

### 3. SELinux/AppArmor 配置

#### SELinux 策略示例

```bash
# 创建 SELinux 策略文件
cat > libvirt_mcp.te << EOF
module libvirt_mcp 1.0;

require {
    type unconfined_t;
    type libvirt_t;
    class process transition;
}

# 允许 libvirt-mcp-server 访问 libvirt
allow unconfined_t libvirt_t:process transition;
EOF

# 编译和安装策略
checkmodule -M -m -o libvirt_mcp.mod libvirt_mcp.te
semodule_package -o libvirt_mcp.pp -m libvirt_mcp.mod
sudo semodule -i libvirt_mcp.pp
```

## 📊 审计和监控

### 1. 审计日志配置

```yaml
logging:
  level: "INFO"
  file: "/var/log/libvirt-mcp-server/audit.log"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  max_size: 104857600  # 100MB
  backup_count: 10

security:
  audit_log: true
```

### 2. 日志监控脚本

```bash
#!/bin/bash
# /opt/libvirt-mcp-server/scripts/monitor_security.sh

LOG_FILE="/var/log/libvirt-mcp-server/audit.log"
ALERT_EMAIL="security@example.com"

# 监控可疑活动
tail -f "$LOG_FILE" | while read line; do
    # 检测失败的操作
    if echo "$line" | grep -q "operation_denied\|rate_limit_exceeded\|unauthorized"; then
        echo "SECURITY ALERT: $line" | mail -s "libvirt-mcp Security Alert" "$ALERT_EMAIL"
    fi
    
    # 检测异常大量操作
    if echo "$line" | grep -q "max_concurrent_ops"; then
        echo "PERFORMANCE ALERT: $line" | mail -s "libvirt-mcp Performance Alert" "$ALERT_EMAIL"
    fi
done
```

### 3. 系统监控集成

#### Prometheus 指标导出

```python
# 在 security.py 中添加 Prometheus 指标
from prometheus_client import Counter, Histogram

OPERATION_COUNTER = Counter('libvirt_mcp_operations_total', 'Total operations', ['operation', 'success'])
OPERATION_DURATION = Histogram('libvirt_mcp_operation_duration_seconds', 'Operation duration')

# 在操作完成时更新指标
OPERATION_COUNTER.labels(operation=operation, success=str(success).lower()).inc()
OPERATION_DURATION.observe(execution_time)
```

## 🔧 安全加固

### 1. 系统级加固

#### Systemd 服务安全配置

```ini
[Service]
# 安全选项
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/libvirt-mcp-server /var/run/libvirt-mcp-server

# 能力限制
CapabilityBoundingSet=
AmbientCapabilities=

# 系统调用过滤
SystemCallFilter=@system-service
SystemCallErrorNumber=EPERM

# 资源限制
LimitNOFILE=1024
LimitNPROC=512
```

### 2. 网络安全

#### 防火墙配置

```bash
# UFW 配置
sudo ufw allow from 192.168.1.0/24 to any port 8000
sudo ufw deny 8000

# iptables 配置
sudo iptables -A INPUT -s 192.168.1.0/24 -p tcp --dport 8000 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 8000 -j DROP
```

#### fail2ban 配置

```ini
# /etc/fail2ban/jail.local
[libvirt-mcp]
enabled = true
port = 8000
filter = libvirt-mcp
logpath = /var/log/libvirt-mcp-server/audit.log
maxretry = 3
bantime = 3600
```

```bash
# /etc/fail2ban/filter.d/libvirt-mcp.conf
[Definition]
failregex = .*operation_denied.*client_info.*ip.*<HOST>
            .*unauthorized.*<HOST>
            .*rate_limit_exceeded.*<HOST>
ignoreregex =
```

### 3. 容器安全（Docker）

#### 安全 Dockerfile 配置

```dockerfile
# 使用非 root 用户
RUN groupadd -r libvirt && useradd -r -g libvirt libvirt
USER libvirt

# 安全选项
LABEL security.no-new-privileges=true
```

#### Docker Compose 安全配置

```yaml
services:
  libvirt-mcp-server:
    security_opt:
      - no-new-privileges:true
      - apparmor:unconfined
    cap_drop:
      - ALL
    cap_add:
      - CHOWN
      - SETGID
      - SETUID
    read_only: true
    tmpfs:
      - /tmp:noexec,nosuid,size=100m
```

## 🚨 事件响应

### 1. 安全事件类型

- **未授权访问**：尝试执行未允许的操作
- **权限提升**：尝试获取更高权限
- **异常活动**：超出正常使用模式的行为
- **资源滥用**：过度使用系统资源

### 2. 响应流程

1. **立即响应**
   - 自动阻止可疑连接
   - 记录详细日志信息
   - 发送实时警报

2. **调查分析**
   - 分析审计日志
   - 确定攻击向量
   - 评估影响范围

3. **修复和恢复**
   - 修复安全漏洞
   - 恢复服务
   - 加强安全控制

### 3. 应急联系人

```yaml
# 在配置中定义应急联系信息
security:
  emergency_contacts:
    - name: "安全团队"
      email: "security@example.com"
      phone: "+86-xxx-xxxx-xxxx"
    - name: "系统管理员"
      email: "sysadmin@example.com"
      phone: "+86-xxx-xxxx-xxxx"
```

## 📝 安全检查清单

### 部署前检查

- [ ] 配置了最小权限操作列表
- [ ] 启用了审计日志
- [ ] 设置了适当的网络访问控制
- [ ] 配置了专用服务用户
- [ ] 设置了正确的文件权限
- [ ] 配置了防火墙规则
- [ ] 设置了监控和告警

### 定期安全检查

- [ ] 审查审计日志
- [ ] 检查用户权限
- [ ] 更新安全策略
- [ ] 测试备份和恢复
- [ ] 验证监控系统
- [ ] 更新软件包

### 事件后检查

- [ ] 分析事件原因
- [ ] 更新安全策略
- [ ] 加强监控规则
- [ ] 培训相关人员
- [ ] 文档化经验教训

## 📞 报告安全问题

如果您发现安全漏洞或有安全相关的问题，请通过以下方式联系我们：

- **邮箱**: security@example.com
- **加密**: 请使用我们的 GPG 公钥加密敏感信息
- **响应时间**: 我们承诺在 24 小时内响应安全报告

请不要公开披露安全问题，直到我们有机会修复它们。
