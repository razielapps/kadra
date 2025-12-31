
# 🔐 KADRA - Credential Bruteforce Automation Tool

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-educational-purple)
![Platform](https://img.shields.io/badge/platform-Kali%20Linux-red)
![Status](https://img.shields.io/badge/status-production-green)
![Tools](https://img.shields.io/badge/tools-Hydra%20%2B%20CeWL-orange)

Author: Conscience Ekhomwandolor 

**KADRA** is an intelligent credential brute force automation tool designed for authorized penetration testing. It specializes in targeted attacks against authentication services (SSH, RDP, FTP, Telnet, SMTP) using a strategic two-phase approach: common passwords followed by target-specific wordlists.

## 📋 Table of Contents
- [🎯 Features](#-features)
- [🚀 Quick Start](#-quick-start)
- [📦 Installation](#-installation)
- [⚙️ Configuration](#️-configuration)
- [📖 Usage](#-usage)
- [🔧 How It Works](#-how-it-works)
- [📊 Output & Results](#-output--results)
- [⚖️ Legal & Ethical Use](#️-legal--ethical-use)
- [🔍 Troubleshooting](#-troubleshooting)
- [🎓 Academic Context](#-academic-context)

## 🎯 Features

### **🎯 Targeted Service Enumeration**
- **Focused Scanning**: Only scans for SSH (22), RDP (3389), FTP (21), Telnet (23), SMTP (25)
- **Fast Detection**: Quick port scanning to identify open services
- **Service-specific**: Uses appropriate usernames for each service type

### **🔑 Intelligent Brute Force Strategy**
- **Two-Phase Approach**:
  1. **Phase 1**: Common/default passwords (`passlist.txt`)
  2. **Phase 2**: Target-specific wordlists (generated from URLs)
- **Smart Escalation**: Only progresses to Phase 2 if Phase 1 fails
- **Service Context**: Different username lists for SSH, RDP, FTP, Telnet, SMTP

### **🔧 Professional Tool Integration**
- **Hydra Engine**: Industry-standard brute force tool
- **CeWL Integration**: Generates targeted wordlists from web content
- **Parallel Execution**: Multi-threaded attacks for efficiency
- **Rate Limiting**: Configurable attempt rates to avoid detection

### **📊 Comprehensive Reporting**
- **JSON Output**: Structured data for automation
- **Human-Readable Summaries**: Quick overview of findings
- **Detailed Logs**: Complete audit trail of all attempts
- **Credential Tracking**: Source attribution for found credentials

## 🚀 Quick Start

### **5-Minute Setup**
```bash
# 1. Download/Clone the tool
git clone https://github.com/razielapps/kadra.git
cd kadra

# 2. Make executable
chmod +x kadra.py

# 3. Create setup script and run
python3 -c "import kadra; kadra.create_setup_script()"
sudo bash setup_kadra.sh

# 4. Configure targets
nano targets.txt

# 5. Run KADRA
sudo python3 kadra.py
```

### **First Run Example**
```bash
# Test with a single target
sudo python3 kadra.py --target 192.168.1.105

# Or use default targets.txt
sudo python3 kadra.py
```

## 📦 Installation

### **System Requirements**
- **Operating System**: Kali Linux 2023.x+ (or any Linux with Hydra/CeWL)
- **Python**: 3.8 or higher
- **Required Tools**: 
  - `hydra` (THC-Hydra)
  - `cewl` (Custom Word List generator)
- **Permissions**: Root/sudo for raw socket operations

### **Automatic Installation**
```bash
# Run the built-in setup
python3 -c "import kadra; kadra.create_setup_script()"
sudo bash setup_kadra.sh
```

### **Manual Installation**
```bash
# 1. Install required packages
sudo apt update
sudo apt install -y hydra cewl python3 python3-pip

# 2. Create necessary directories
mkdir -p wordlists results

# 3. Create configuration files
touch targets.txt passlist.txt

# 4. Add default passwords to passlist.txt
cat > passlist.txt << 'EOF'
admin
password
123456
password123
administrator
root
toor
admin123
test
guest
qwerty
letmein
EOF
```

### **Verification**
```bash
# Check installation
python3 kadra.py --help

# Verify tools are available
which hydra
which cewl
```

## ⚙️ Configuration

### **File Structure**
```
kadra/
├── kadra.py                 # Main script
├── targets.txt             # Target list (required)
├── passlist.txt           # Common passwords (required)
├── setup_kadra.sh         # Installation script
├── kadra.log              # Log file (auto-generated)
├── wordlists/             # Generated wordlists (auto)
│   ├── https_example_com.txt
│   └── target_specific.txt
└── results/               # Scan results (auto)
    ├── target1_summary.txt
    └── target1_credentials.json
```

### **1. `targets.txt` - Target Specification**
```txt
# Add targets (IPs, domains, or URLs)
# One per line, comments with #

192.168.1.105              # Internal server
example.com                # Domain (will be resolved)
https://webapp.example.com # URL (wordlist will be generated)
ftp.server.com            # FTP server
smtp.corporate.com        # SMTP server
```

**Supported Formats:**
- IP addresses: `192.168.1.1`
- Domains: `example.com` (will be DNS resolved)
- URLs: `https://example.com` (triggers wordlist generation)

### **2. `passlist.txt` - Common Passwords**
```txt
# Most common/default passwords
# One per line

admin
password
123456
password123
administrator
root
toor
admin123
test
guest
qwerty
letmein
welcome
12345
12345678
123456789
```

**Tip**: Start with 15-20 most common passwords. Add service-specific defaults if known.

### **3. Configuration (In-Code)**
Key settings in `kadra.py`:
```python
class Config:
    # Service definitions
    SERVICES = {
        'ssh': {'port': 22, 'hydra_module': 'ssh', 'timeout': 30},
        'rdp': {'port': 3389, 'hydra_module': 'rdp', 'timeout': 45},
        'ftp': {'port': 21, 'hydra_module': 'ftp', 'timeout': 25},
        'telnet': {'port': 23, 'hydra_module': 'telnet', 'timeout': 20},
        'smtp': {'port': 25, 'hydra_module': 'smtp', 'timeout': 30}
    }
    
    # Performance
    MAX_THREADS = 3           # Concurrent attacks
    HYDRA_TASKS = 16         # Hydra parallel tasks
    BRUTE_TIMEOUT = 300      # Max seconds per attack
    
    # CeWL settings
    CEWL_DEPTH = 2           # Spidering depth
    CEWL_MIN_WORD_LEN = 3    # Minimum word length
```

## 📖 Usage

### **Command Line Interface**

```bash
# Show help with all options
python3 kadra.py --help
```

#### **Basic Operations**
```bash
# Run with default targets.txt and passlist.txt
sudo python3 kadra.py

# Single target (skip targets.txt)
sudo python3 kadra.py --target 192.168.1.105

# Custom targets file
sudo python3 kadra.py --targets my_targets.txt

# Custom password list
sudo python3 kadra.py --passlist custom_passwords.txt
```

#### **Performance Tuning**
```bash
# Adjust thread count
sudo python3 kadra.py --threads 5

# Skip wordlist generation (faster)
sudo python3 kadra.py --no-wordlists

# Verbose output for debugging
sudo python3 kadra.py --verbose
```

#### **Advanced Examples**
```bash
# Comprehensive attack with wordlists
sudo python3 kadra.py --targets production_servers.txt --threads 4

# Quick test without wordlist generation
sudo python3 kadra.py --target test-server.local --no-wordlists

# Debug mode with maximum output
sudo python3 kadra.py --target 192.168.1.100 --verbose 2>&1 | tee debug.log
```

### **Interactive Workflow**
When you run KADRA, it follows this workflow:

1. **Load Configuration**
   - Reads `targets.txt` and `passlist.txt`
   - Validates all targets

2. **Wordlist Generation** (if enabled)
   - For each URL target, runs CeWL to generate context-aware wordlists
   - Saves to `wordlists/` directory

3. **Service Discovery**
   - Scans each target for open service ports
   - Only proceeds with open services

4. **Phase 1: Common Passwords**
   - Attempts common passwords from `passlist.txt`
   - Tries service-specific usernames
   - Stops if credentials found

5. **Phase 2: Target Wordlists** (if Phase 1 fails)
   - Uses generated wordlists for targeted attacks
   - More sophisticated but slower approach

6. **Results & Reporting**
   - Saves credentials to `results/` directory
   - Generates human-readable summaries
   - Logs all activity to `kadra.log`

## 🔧 How It Works

### **Architecture Overview**
```
┌─────────────────┐
│   targets.txt   │
└────────┬────────┘
         │
┌────────▼────────┐
│  Target Loader  │
│  • Validation   │
│  • DNS Resolve  │
└────────┬────────┘
         │
┌────────▼────────┐    ┌─────────────────┐
│  Wordlist Gen   │◄───┤     CeWL        │
│  • URL parsing  │    │  (for URLs)     │
│  • File save    │    └─────────────────┘
└────────┬────────┘
         │
┌────────▼────────┐
│  Port Scanner   │
│  • SSH (22)     │
│  • RDP (3389)   │
│  • FTP (21)     │
│  • Telnet (23)  │
│  • SMTP (25)    │
└────────┬────────┘
         │
┌────────▼────────┐    ┌─────────────────┐
│  Phase 1:       │    │  passlist.txt   │
│  Common Passwords├───►                 │
│                 │    │  admin          │
│                 │    │  password       │
│                 │    │  123456         │
└────────┬────────┘    └─────────────────┘
         │
    ┌────┴─────┐
    │ Success? │───Yes──►[Save Credentials]
    └────┬─────┘
         │No
         │
┌────────▼────────┐    ┌─────────────────┐
│  Phase 2:       │    │  wordlists/     │
│  Target Lists   ├───►│  target1.txt    │
│                 │    │  target2.txt    │
│                 │    └─────────────────┘
└────────┬────────┘
         │
    ┌────┴─────┐
    │ Success? │───Yes──►[Save Credentials]
    └────┬─────┘
         │No
         ▼
   [Next Service/Target]
```

### **Service-Specific Details**

#### **SSH (Port 22)**
- **Common Usernames**: `root`, `ubuntu`, `admin`, `ec2-user`
- **Strategy**: High-rate attempts with common defaults
- **Success Rate**: Typically high for misconfigured servers

#### **RDP (Port 3389)**
- **Common Usernames**: `administrator`, `admin`, `user`
- **Strategy**: Slower attempts (Windows account lockout)
- **Note**: Uses Hydra's RDP module with visual feedback

#### **FTP (Port 21)**
- **Common Usernames**: `anonymous`, `ftp`, `admin`
- **Strategy**: Quick anonymous check first
- **Success Rate**: High for anonymous FTP servers

#### **Telnet (Port 23)**
- **Common Usernames**: `root`, `admin`, `cisco`
- **Strategy**: Fast attempts (usually no lockouts)
- **Warning**: Credentials transmitted in clear text

#### **SMTP (Port 25)**
- **Common Usernames**: `admin`, `postmaster`, `mail`
- **Strategy**: VRFY/EXPN testing before brute force
- **Use Case**: Email server enumeration

### **Wordlist Generation Strategy**
```bash
# CeWL command used internally
cewl https://target.com \
  -d 2 \          # Depth of spidering
  -m 3 \          # Minimum word length
  --with-numbers \ # Include numbers
  --lowercase \   # Convert to lowercase
  -w target.txt   # Output file
```

**Generated wordlists include:**
- Page titles and headings
- Body text content
- Metadata keywords
- URLs and paths
- Email-like patterns
- Number variations

## 📊 Output & Results

### **Results Directory Structure**
```
results/
├── 192_168_1_105_20240115_143022.json
├── 192_168_1_105_summary.txt
├── example_com_20240115_143512.json
└── example_com_summary.txt
```

### **JSON Output Example**
```json
{
  "target": "192.168.1.105",
  "ip": "192.168.1.105",
  "open_services": {
    "ssh": true,
    "rdp": false,
    "ftp": true,
    "telnet": false,
    "smtp": true
  },
  "credentials_found": [
    {
      "service": "ssh",
      "username": "root",
      "password": "password123",
      "host": "192.168.1.105",
      "port": 22,
      "password_source": "common"
    }
  ],
  "timestamp": "2024-01-15T14:30:22"
}
```

### **Summary File Example**
```
============================================================
KADRA - Credential Bruteforce Summary
============================================================

Target: 192.168.1.105
IP Address: 192.168.1.105
Scan Time: 2024-01-15T14:30:22

Open Services:
  SSH        : OPEN
  RDP        : closed
  FTP        : OPEN
  TELNET     : closed
  SMTP       : OPEN

Credentials Found:
  1. Service: SSH
     Username: root
     Password: password123
     Source: common
     Host: 192.168.1.105:22

============================================================
```

### **Log File**
`kadra.log` contains:
- Timestamped operations
- Scan progress
- Attack attempts
- Success/failure notifications
- Error messages and debugging info

## ⚖️ Legal & Ethical Use

### **Authorized Use Cases**
- ✅ **Penetration Testing**: With written authorization from system owner
- ✅ **Security Research**: In controlled lab environments
- ✅ **Educational Purposes**: Classroom learning (like this project)
- ✅ **Self-Assessment**: Testing your own systems/networks
- ✅ **Bug Bounty Programs**: Within explicitly defined scope

### **Strictly Prohibited**
- ❌ **Unauthorized Testing**: Any system without explicit permission
- ❌ **Production Systems**: Without formal approval and scheduling
- ❌ **Third-Party Services**: Cloud providers, ISPs, etc.
- ❌ **Malicious Activities**: Data theft, disruption, or damage
- ❌ **Illegal Access**: Violating computer fraud laws

### **Legal Compliance**
Users must ensure compliance with:
- **Computer Fraud and Abuse Act (CFAA)**
- **General Data Protection Regulation (GDPR)**
- **Local cybersecurity laws**
- **Terms of Service agreements**
- **Organizational security policies**

### **Responsible Disclosure**
If vulnerabilities are found:
1. **Document** findings thoroughly
2. **Notify** system owner immediately
3. **Provide** remediation recommendations
4. **Delete** any captured data after reporting
5. **Maintain** confidentiality until fixed

## 🔍 Troubleshooting

### **Common Issues & Solutions**

#### **Issue: "Hydra not found"**
```bash
# Solution: Install Hydra
sudo apt update
sudo apt install hydra

# Verify installation
which hydra
```

#### **Issue: "CeWL not found"**
```bash
# Solution: Install CeWL
sudo apt update
sudo apt install cewl

# Verify installation
which cewl
```

#### **Issue: Permission Denied**
```bash
# Solution: Run with sudo
sudo python3 kadra.py

# Alternative: Set capabilities (advanced)
sudo setcap cap_net_raw+ep $(which python3)
```

#### **Issue: Timeout Errors**
```python
# Adjust in Config class:
Config.BRUTE_TIMEOUT = 600  # Increase timeout
Config.HYDRA_TASKS = 8      # Reduce parallel tasks
```

#### **Issue: No Credentials Found**
1. **Check `passlist.txt`** - Add more common passwords
2. **Verify services** - Ensure ports are actually open
3. **Check network** - Firewall may be blocking
4. **Review logs** - `kadra.log` for detailed info

### **Debug Mode**
```bash
# Enable verbose logging
sudo python3 kadra.py --verbose 2>&1 | tee debug.log

# Check log file
tail -f kadra.log
```

### **Performance Optimization**

| Setting | Fast Scan | Thorough Scan |
|---------|-----------|---------------|
| Threads | 5 | 2 |
| Wordlists | Disabled | Enabled |
| Timeout | 120s | 300s |
| CeWL Depth | 1 | 3 |


### **Extension Ideas**
For advanced projects, consider adding:

1. **Hash Cracking**: Integrate John the Ripper or Hashcat
2. **API Support**: Cloud service credential testing
3. **Reporting Dashboard**: Web interface for results
4. **Machine Learning**: Predict password patterns
5. **Distributed Attacks**: Multi-system coordination

## 📚 Resources

### **Further Learning**
- [THC-Hydra Manual](https://github.com/vanhauser-thc/thc-hydra)
- [CeWL Documentation](https://github.com/digininja/CeWL)
- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [Pentester's Lab](https://pentesterlab.com/)

### **Similar Tools**
- **Medusa**: Alternative to Hydra
- **Patator**: Multi-protocol brute forcer
- **Ncrack**: From Nmap developers
- **BruteSpray**: Post-Nmap brute forcing

### **Security Standards**
- **NIST SP 800-63**: Digital Identity Guidelines
- **ISO/IEC 27001**: Information Security Management
- **PCI DSS**: Payment Card Industry Security
- **CIS Benchmarks**: Security configuration guidelines

---

## ⚠️ Final Warning

**This tool is for educational and authorized security testing only.**

**Never use KADRA on systems you don't own or have explicit written permission to test.**

**By using this tool, you accept full responsibility for your actions.**

---

**KADRA** - Because sometimes, the key is just trying the most obvious things first.

*Built for educational purposes. Use responsibly.*
