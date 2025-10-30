"""
Models plugin for Psyduck CLI
Shows available OpenAI models and their capabilities
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_openai_client():
    """Initialize OpenAI client with API key from environment"""
    api_key = os.getenv('OPENAI_KEY')
    if not api_key or api_key == 'your_openai_api_key_here':
        return None
    return OpenAI(api_key=api_key)

def list_models_command(cli_instance):
    """List all available OpenAI models"""
    from psyduck import Colors
    
    client = get_openai_client()
    if not client:
        print(f"\n{Colors.RED}❌ OpenAI API key not configured{Colors.END}")
        print(f"{Colors.YELLOW}Please set your OPENAI_KEY in the .env file{Colors.END}")
        return
    
    try:
        print(f"\n{Colors.BOLD}{Colors.CYAN}🤖 Available OpenAI Models{Colors.END}")
        print(f"{Colors.WHITE}{'='*50}{Colors.END}")
        
        # Get models from OpenAI API
        models = client.models.list()
        
        # Categorize models
        gpt_models = []
        embedding_models = []
        other_models = []
        
        for model in models.data:
            model_id = model.id
            if 'gpt' in model_id.lower():
                gpt_models.append(model_id)
            elif 'embedding' in model_id.lower() or 'text-embedding' in model_id.lower():
                embedding_models.append(model_id)
            else:
                other_models.append(model_id)
        
        # Display GPT models
        if gpt_models:
            print(f"\n{Colors.GREEN}💬 GPT Models:{Colors.END}")
            for model in sorted(gpt_models):
                print(f"  {Colors.WHITE}• {model}{Colors.END}")
        
        # Display embedding models
        if embedding_models:
            print(f"\n{Colors.BLUE}🔗 Embedding Models:{Colors.END}")
            for model in sorted(embedding_models):
                print(f"  {Colors.WHITE}• {model}{Colors.END}")
        
        # Display other models
        if other_models:
            print(f"\n{Colors.MAGENTA}🔧 Other Models:{Colors.END}")
            for model in sorted(other_models):
                print(f"  {Colors.WHITE}• {model}{Colors.END}")
        
        print(f"\n{Colors.GREEN}✓ Found {len(models.data)} total models{Colors.END}")
        
    except Exception as e:
        print(f"\n{Colors.RED}❌ Error fetching models: {str(e)}{Colors.END}")
        print(f"{Colors.YELLOW}Please check your API key and internet connection{Colors.END}")

def list_gpt_models_command(cli_instance):
    """List only GPT models"""
    from psyduck import Colors
    
    client = get_openai_client()
    if not client:
        print(f"\n{Colors.RED}❌ OpenAI API key not configured{Colors.END}")
        print(f"{Colors.YELLOW}Please set your OPENAI_KEY in the .env file{Colors.END}")
        return
    
    try:
        print(f"\n{Colors.BOLD}{Colors.GREEN}💬 GPT Models Only{Colors.END}")
        print(f"{Colors.WHITE}{'='*30}{Colors.END}")
        
        models = client.models.list()
        gpt_models = [model.id for model in models.data if 'gpt' in model.id.lower()]
        
        if gpt_models:
            for model in sorted(gpt_models):
                print(f"  {Colors.WHITE}• {model}{Colors.END}")
            print(f"\n{Colors.GREEN}✓ Found {len(gpt_models)} GPT models{Colors.END}")
        else:
            print(f"{Colors.YELLOW}No GPT models found{Colors.END}")
            
    except Exception as e:
        print(f"\n{Colors.RED}❌ Error fetching GPT models: {str(e)}{Colors.END}")

def model_info_command(cli_instance, model_name=None):
    """Get detailed information about a specific model"""
    from psyduck import Colors
    
    if not model_name:
        model_name = input(f"{Colors.CYAN}Enter model name: {Colors.END}").strip()
    
    if not model_name:
        print(f"{Colors.RED}❌ No model name provided{Colors.END}")
        return
    
    client = get_openai_client()
    if not client:
        print(f"\n{Colors.RED}❌ OpenAI API key not configured{Colors.END}")
        print(f"{Colors.YELLOW}Please set your OPENAI_KEY in the .env file{Colors.END}")
        return
    
    try:
        print(f"\n{Colors.BOLD}{Colors.CYAN}🔍 Model Information: {model_name}{Colors.END}")
        print(f"{Colors.WHITE}{'='*50}{Colors.END}")
        
        # Get model details
        model = client.models.retrieve(model_name)
        
        print(f"{Colors.YELLOW}Model ID:{Colors.END} {Colors.WHITE}{model.id}{Colors.END}")
        print(f"{Colors.YELLOW}Object Type:{Colors.END} {Colors.WHITE}{model.object}{Colors.END}")
        print(f"{Colors.YELLOW}Created:{Colors.END} {Colors.WHITE}{model.created}{Colors.END}")
        print(f"{Colors.YELLOW}Owned By:{Colors.END} {Colors.WHITE}{model.owned_by}{Colors.END}")
        
        if hasattr(model, 'permission') and model.permission:
            print(f"{Colors.YELLOW}Permissions:{Colors.END}")
            for perm in model.permission:
                print(f"  {Colors.WHITE}• {perm.id}{Colors.END}")
        
        print(f"\n{Colors.GREEN}✓ Model information retrieved{Colors.END}")
        
    except Exception as e:
        print(f"\n{Colors.RED}❌ Error fetching model info: {str(e)}{Colors.END}")
        print(f"{Colors.YELLOW}Model '{model_name}' may not exist or be accessible{Colors.END}")

def test_connection_command(cli_instance):
    """Test OpenAI API connection"""
    from psyduck import Colors
    
    client = get_openai_client()
    if not client:
        print(f"\n{Colors.RED}❌ OpenAI API key not configured{Colors.END}")
        print(f"{Colors.YELLOW}Please set your OPENAI_KEY in the .env file{Colors.END}")
        return
    
    try:
        print(f"\n{Colors.BOLD}{Colors.CYAN}🔌 Testing OpenAI Connection{Colors.END}")
        print(f"{Colors.WHITE}{'='*35}{Colors.END}")
        
        # Test with a simple API call
        models = client.models.list()
        model_count = len(models.data)
        
        print(f"{Colors.GREEN}✓ Connection successful!{Colors.END}")
        print(f"{Colors.WHITE}• API Key: Valid{Colors.END}")
        print(f"{Colors.WHITE}• Models accessible: {model_count}{Colors.END}")
        print(f"{Colors.WHITE}• Status: Ready{Colors.END}")
        
    except Exception as e:
        print(f"\n{Colors.RED}❌ Connection failed: {str(e)}{Colors.END}")
        print(f"{Colors.YELLOW}Please check your API key and internet connection{Colors.END}")

# Plugin metadata
PLUGIN_INFO = {
    'name': 'models',
    'description': 'OpenAI models management and information',
    'version': '1.0.0',
    'commands': {
        'models': {
            'handler': list_models_command,
            'description': 'List all available OpenAI models',
            'usage': 'models'
        }
    }
}
