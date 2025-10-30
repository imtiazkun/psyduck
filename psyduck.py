#!/usr/bin/env python3
"""
Psyduck - A stylized CLI application with loading animations and visual elements
"""

import argparse
import sys
import time
import random
import os
import importlib.util
from typing import List, Optional, Dict, Any
import threading
from datetime import datetime

class Colors:
    """ANSI color codes for terminal styling"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

class PsyduckCLI:
    def __init__(self):
        self.running = False
        self.plugins = {}
        self.load_plugins()
        
    def print_banner(self):
        """Display the Psyduck banner"""
        banner = f"""
{Colors.YELLOW}
⠀⠀⠀⠀⠀⠀⠀⠀⣤⡀⠀⣶⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠙⣿⣆⣿⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠸⣷⣮⣿⣿⣄⣀⣀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⢀⡠⠒⠉⠀⠀⠀⠀⠀⠀⠈⠁⠲⢖⠒⡀⠀⠀
⠀⠀⠀⡠⠴⣏⠀⢀⡀⠀⢀⡀⠀⠀⠀⡀⠀⠀⡀⠱⡈⢄⠀
⠀⠀⢠⠁⠀⢸⠐⠁⠀⠄⠀⢸⠀⠀⢎⠀⠂⠀⠈⡄⢡⠀⢣
⠀⢀⠂⠀⠀⢸⠈⠢⠤⠤⠐⢁⠄⠒⠢⢁⣂⡐⠊⠀⡄⠀⠸
⠀⡘⠀⠀⠀⢸⠀⢠⠐⠒⠈⠀⠀⠀⠀⠀⠀⠈⢆⠜⠀⠀⢸
⠀⡇⠀⠀⠀⠀⡗⢺⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠑⡄⢀⠎
⠀⢃⠀⠀⠀⢀⠃⢠⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⠷⡃⠀
⠀⠈⠢⣤⠀⠈⠀⠀⠑⠠⠤⣀⣀⣀⣀⣀⡀⠤⠒⠁⠀⢡⠀
⡀⣀⠀⡆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢘⠀
⠑⢄⠉⢳⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡸⠀
⠀⠀⠑⠢⢱⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⡴⠁⠀
⠀⠀⠀⠀⢀⠠⠓⠢⠤⣀⣀⡀⠀⠀⣀⣀⡀⠤⠒⠑⢄⠀⠀
⠀⠀⠀⠰⠥⠤⢄⢀⡠⠄⡈⡀⠀⠀⣇⣀⠠⢄⠀⠒⠤⠣⠀
⠀⠀⠀⠀⠀⠀⠀⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠀⠀⠀⠀

{Colors.BOLD}🦆 PSYDUCK CLI v1.0.0 🦆{Colors.END}
{Colors.WHITE}AI OSINT Tool for sentiment Analysis{Colors.END}
        """
        print(banner)
    
    def loading_spinner(self, message: str = "Loading", duration: float = 3.0):
        """Display a loading spinner with message"""
        spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        end_time = time.time() + duration
        
        print(f"\n{Colors.YELLOW}{message}...{Colors.END}", end='', flush=True)
        
        while time.time() < end_time:
            for char in spinner_chars:
                if time.time() >= end_time:
                    break
                print(f"\r{Colors.YELLOW}{message}... {char}{Colors.END}", end='', flush=True)
                time.sleep(0.1)
        
        print(f"\r{Colors.GREEN}{message}... ✓{Colors.END}")
    
    def progress_bar(self, message: str = "Processing", duration: float = 3.0, width: int = 40):
        """Display a progress bar with percentage"""
        print(f"\n{Colors.BLUE}{message}:{Colors.END}")
        
        for i in range(width + 1):
            percentage = int((i / width) * 100)
            filled = '█' * i
            empty = '░' * (width - i)
            
            print(f"\r{Colors.CYAN}[{filled}{empty}] {percentage:3d}%{Colors.END}", end='', flush=True)
            time.sleep(duration / width)
        
        print(f"\n{Colors.GREEN}✓ {message} completed!{Colors.END}")
    
    def typewriter_effect(self, text: str, delay: float = 0.05):
        """Display text with typewriter effect"""
        for char in text:
            print(char, end='', flush=True)
            time.sleep(delay)
        print()
    
    def rainbow_text(self, text: str):
        """Display text in rainbow colors"""
        colors = [Colors.RED, Colors.YELLOW, Colors.GREEN, Colors.CYAN, Colors.BLUE, Colors.MAGENTA]
        result = ""
        
        for i, char in enumerate(text):
            if char == ' ':
                result += ' '
            else:
                color = colors[i % len(colors)]
                result += f"{color}{char}{Colors.END}"
        
        return result
    
    def show_menu(self):
        """Display the main menu"""
        commands = self.get_available_commands()
        
        menu_text = f"""
{Colors.BOLD}{Colors.CYAN}╔══════════════════════════════════════╗
║              MAIN MENU              ║
╚══════════════════════════════════════╝{Colors.END}

{Colors.WHITE}Available Commands:{Colors.END}"""
        
        # System commands
        system_commands = ['help', 'exit']
        for cmd in system_commands:
            if cmd in commands:
                menu_text += f"\n  {Colors.GREEN}{cmd:<12}{Colors.END} - {commands[cmd]}"
        
        # Plugin commands
        plugin_commands = [cmd for cmd in commands.keys() if cmd not in system_commands]
        if plugin_commands:
            menu_text += f"\n\n{Colors.MAGENTA}Plugin Commands:{Colors.END}"
            for cmd in sorted(plugin_commands):
                menu_text += f"\n  {Colors.CYAN}{cmd:<12}{Colors.END} - {commands[cmd]}"
        
        menu_text += f"\n\n{Colors.YELLOW}Usage: psyduck <command> [options]{Colors.END}"
        print(menu_text)
    
    def show_time(self):
        """Display current time with styling"""
        now = datetime.now()
        time_str = now.strftime("%Y-%m-%d %H:%M:%S")
        
        print(f"\n{Colors.BOLD}{Colors.CYAN}🕐 Current Time:{Colors.END}")
        print(f"{Colors.WHITE}{time_str}{Colors.END}")
    
    def random_fact(self):
        """Display a random Psyduck fact"""
        facts = [
            "Psyduck is a Water-type Pokémon known for its constant headaches.",
            "When Psyduck's headache peaks, it unleashes tremendous psychic power.",
            "Psyduck's vacant expression is actually a sign of intense concentration.",
            "In the anime, Misty's Psyduck often appears at the most inconvenient times.",
            "Psyduck evolves into Golduck when exposed to a Water Stone.",
            "Despite its confused appearance, Psyduck is actually quite intelligent.",
            "Psyduck's psychic powers are strongest when it has a headache.",
            "The yellow duck Pokémon is often misunderstood due to its expression."
        ]
        
        fact = random.choice(facts)
        print(f"\n{Colors.BOLD}{Colors.YELLOW}🦆 Random Psyduck Fact:{Colors.END}")
        print(f"{Colors.WHITE}{fact}{Colors.END}")
    
    def demo(self):
        """Run a comprehensive demo of all features"""
        print(f"\n{Colors.BOLD}{Colors.MAGENTA}🎬 Running Psyduck Demo...{Colors.END}")
        
        # Typewriter effect
        self.typewriter_effect(f"{Colors.CYAN}Welcome to the Psyduck CLI demo!{Colors.END}")
        time.sleep(1)
        
        # Loading spinner
        self.loading_spinner("Initializing Psyduck", 2.0)
        
        # Progress bar
        self.progress_bar("Loading features", 3.0)
        
        # Rainbow text
        rainbow_text = self.rainbow_text("PSYDUCK CLI IS AWESOME!")
        print(f"\n{rainbow_text}")
        
        # Random fact
        self.random_fact()
        
        # Time display
        self.show_time()
        
        print(f"\n{Colors.GREEN}✓ Demo completed!{Colors.END}")
    
    def load_plugins(self):
        """Load all plugins from the plugin directory"""
        plugin_dir = os.path.join(os.path.dirname(__file__), 'plugin')
        
        if not os.path.exists(plugin_dir):
            return
        
        for item in os.listdir(plugin_dir):
            plugin_path = os.path.join(plugin_dir, item)
            if os.path.isdir(plugin_path) and not item.startswith('__'):
                main_file = os.path.join(plugin_path, 'main.py')
                if os.path.exists(main_file):
                    try:
                        spec = importlib.util.spec_from_file_location(f"plugin.{item}", main_file)
                        plugin_module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(plugin_module)
                        
                        if hasattr(plugin_module, 'PLUGIN_INFO'):
                            plugin_info = plugin_module.PLUGIN_INFO
                            self.plugins[plugin_info['name']] = plugin_info
                            # Only show loading message in interactive mode
                            if hasattr(self, '_show_loading_messages'):
                                print(f"{Colors.GREEN}✓ Loaded plugin: {plugin_info['name']}{Colors.END}")
                        else:
                            if hasattr(self, '_show_loading_messages'):
                                print(f"{Colors.YELLOW}⚠ Plugin {item} missing PLUGIN_INFO{Colors.END}")
                    except Exception as e:
                        if hasattr(self, '_show_loading_messages'):
                            print(f"{Colors.RED}✗ Failed to load plugin {item}: {e}{Colors.END}")
    
    def get_available_commands(self):
        """Get all available commands including plugin commands"""
        commands = {
            'help': 'Show this menu',
            'exit': 'Exit the application'
        }
        
        # Add plugin commands
        for plugin_name, plugin_info in self.plugins.items():
            if 'commands' in plugin_info:
                for cmd_name, cmd_info in plugin_info['commands'].items():
                    commands[cmd_name] = cmd_info['description']
        
        return commands
    
    def execute_command(self, command: str, args: List[str] = None):
        """Execute a command, checking plugins first"""
        if args is None:
            args = []
            
        # Check if command exists in plugins
        for plugin_name, plugin_info in self.plugins.items():
            if 'commands' in plugin_info and command in plugin_info['commands']:
                cmd_info = plugin_info['commands'][command]
                if 'handler' in cmd_info:
                    try:
                        # Pass arguments to handler if it accepts them
                        import inspect
                        sig = inspect.signature(cmd_info['handler'])
                        if len(sig.parameters) > 1:  # More than just cli_instance
                            cmd_info['handler'](self, *args)
                        else:
                            cmd_info['handler'](self)
                        return True
                    except Exception as e:
                        print(f"{Colors.RED}Error executing plugin command {command}: {e}{Colors.END}")
                        return False
        
        # Handle system commands
        if command == 'help' or command == '':
            self.show_menu()
        else:
            return False
        
        return True
    
    def run_interactive(self):
        """Run the CLI in interactive mode"""
        self._show_loading_messages = True
        self.print_banner()
        self.show_menu()
        
        while True:
            try:
                user_input = input(f"\n{Colors.CYAN}psyduck> {Colors.END}").strip()
                
                if not user_input:
                    self.show_menu()
                    continue
                
                parts = user_input.split()
                command = parts[0].lower()
                args = parts[1:] if len(parts) > 1 else []
                
                if command == 'exit' or command == 'quit':
                    print(f"\n{Colors.YELLOW}Goodbye! Thanks for using Psyduck CLI! 🦆{Colors.END}")
                    break
                elif not self.execute_command(command, args):
                    print(f"{Colors.RED}Unknown command: {command}{Colors.END}")
                    print(f"{Colors.YELLOW}Type 'help' to see available commands{Colors.END}")
                    
            except KeyboardInterrupt:
                print(f"\n\n{Colors.YELLOW}Goodbye! Thanks for using Psyduck CLI! 🦆{Colors.END}")
                break
            except EOFError:
                print(f"\n\n{Colors.YELLOW}Goodbye! Thanks for using Psyduck CLI! 🦆{Colors.END}")
                break

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Psyduck - A stylized CLI application with visual elements",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  psyduck                    # Run in interactive mode
  psyduck demo              # Run demo animations
  psyduck spinner           # Show loading spinner
  psyduck progress          # Show progress bar
  psyduck time              # Show current time
  psyduck random            # Show random Psyduck fact
        """
    )
    
    parser.add_argument('command', nargs='?', default='interactive',
                       help='Command to run (default: interactive mode)')
    
    args = parser.parse_args()
    cli = PsyduckCLI()
    
    if args.command == 'interactive':
        cli.run_interactive()
    else:
        # Try to execute the command
        if not cli.execute_command(args.command):
            print(f"{Colors.RED}Unknown command: {args.command}{Colors.END}")
            print(f"{Colors.YELLOW}Run 'psyduck --help' for usage information{Colors.END}")
            sys.exit(1)

if __name__ == "__main__":
    main()
