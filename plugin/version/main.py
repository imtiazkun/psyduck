"""
Version plugin for Psyduck CLI
Displays version information and build details
"""

from datetime import datetime
import sys
import platform

def get_version_info():
    """Get comprehensive version information"""
    return {
        'version': '1.0.0',
        'build_date': '2025-10-28',
        'python_version': sys.version.split()[0],
        'platform': platform.system(),
        'architecture': platform.machine()
    }

def version_command(cli_instance):
    """Version command handler"""
    from psyduck import Colors
    
    info = get_version_info()
    
    print(f"\n{Colors.BOLD}{Colors.CYAN}🦆 Psyduck CLI Version Information{Colors.END}")
    print(f"{Colors.WHITE}{'='*40}{Colors.END}")
    
    print(f"{Colors.YELLOW}Version:{Colors.END} {Colors.WHITE}{info['version']}{Colors.END}")
    print(f"{Colors.YELLOW}Build Date:{Colors.END} {Colors.WHITE}{info['build_date']}{Colors.END}")
    print(f"{Colors.YELLOW}Python:{Colors.END} {Colors.WHITE}{info['python_version']}{Colors.END}")
    print(f"{Colors.YELLOW}Platform:{Colors.END} {Colors.WHITE}{info['platform']}{Colors.END}")
    print(f"{Colors.YELLOW}Architecture:{Colors.END} {Colors.WHITE}{info['architecture']}{Colors.END}")
    
    print(f"\n{Colors.GREEN}✓ Version information displayed{Colors.END}")

def version_detailed_command(cli_instance):
    """Detailed version command with more info"""
    from psyduck import Colors
    
    info = get_version_info()
    
    print(f"\n{Colors.BOLD}{Colors.MAGENTA}🔍 Detailed Version Information{Colors.END}")
    print(f"{Colors.WHITE}{'='*50}{Colors.END}")
    
    # Basic info
    print(f"{Colors.CYAN}Application:{Colors.END}")
    print(f"  {Colors.WHITE}Name:{Colors.END} Psyduck CLI")
    print(f"  {Colors.WHITE}Version:{Colors.END} {info['version']}")
    print(f"  {Colors.WHITE}Build Date:{Colors.END} {info['build_date']}")
    
    # System info
    print(f"\n{Colors.CYAN}System:{Colors.END}")
    print(f"  {Colors.WHITE}Platform:{Colors.END} {info['platform']}")
    print(f"  {Colors.WHITE}Architecture:{Colors.END} {info['architecture']}")
    print(f"  {Colors.WHITE}Python Version:{Colors.END} {info['python_version']}")
    
    # Runtime info
    print(f"\n{Colors.CYAN}Runtime:{Colors.END}")
    print(f"  {Colors.WHITE}Current Time:{Colors.END} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  {Colors.WHITE}Python Executable:{Colors.END} {sys.executable}")
    
    print(f"\n{Colors.GREEN}✓ Detailed version information displayed{Colors.END}")

# Plugin metadata
PLUGIN_INFO = {
    'name': 'version',
    'description': 'Version information and system details',
    'version': '1.0.0',
    'commands': {
        'version': {
            'handler': version_command,
            'description': 'Show version information',
            'usage': 'version'
        }
    }
}
