#!/usr/bin/env python3
"""
Script để kiểm tra model nào đang được sử dụng bởi các agents
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'services', 'orchestrator'))

from app.core.config_manager import get_config_manager

def check_models():
    """Kiểm tra configuration của các models"""
    
    print("=" * 80)
    print("KIỂM TRA AGENT MODELS CONFIGURATION")
    print("=" * 80)
    
    config_manager = get_config_manager()
    
    # List all agents
    agents = config_manager.list_available_agents()
    print(f"\nĐã tìm thấy {len(agents)} agents:")
    for agent in agents:
        print(f"  - {agent}")
    
    print("\n" + "-" * 80)
    
    # Check each agent's model
    for agent_id in agents:
        print(f"\n🤖 Agent: {agent_id}")
        print("-" * 80)
        
        try:
            full_config = config_manager.get_agent_full_config(agent_id)
            
            print(f"  Model: {full_config.get('model')}")
            print(f"  Temperature: {full_config.get('temperature')}")
            print(f"  Max tokens: {full_config.get('max_tokens')}")
            print(f"  Timeout: {full_config.get('timeout')}")
            
            # Get raw agent config to see model_config reference
            agent_config = config_manager.get_agent_config(agent_id)
            print(f"  Model config ref: {agent_config.model_config}")
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    # Check environment variable
    print("\n" + "=" * 80)
    print("ENVIRONMENT VARIABLES")
    print("=" * 80)
    
    env_model = os.getenv('OPENROUTER_DEFAULT_MODEL', 'Not set')
    print(f"OPENROUTER_DEFAULT_MODEL: {env_model}")
    
    # Check model configurations
    print("\n" + "=" * 80)
    print("MODEL CONFIGURATIONS")
    print("=" * 80)
    
    models = config_manager.list_available_models()
    print(f"\nĐã tìm thấy {len(models)} model configs:")
    
    for model_id in models:
        try:
            model_config = config_manager.get_model_config(model_id)
            print(f"\n📋 {model_id}:")
            print(f"  Name: {model_config.name}")
            print(f"  Temperature: {model_config.temperature}")
            print(f"  Max tokens: {model_config.max_tokens}")
        except Exception as e:
            print(f"\n📋 {model_id}: ❌ Error: {e}")

if __name__ == "__main__":
    check_models()
