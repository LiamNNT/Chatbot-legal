# Centralized Configuration System for Orchestrator Service

## Overview

This document describes the new centralized configuration system that implements the architectural improvements suggested for the Chatbot-UIT orchestrator service. The system now separates configuration from business logic, uses dependency injection, and implements the Factory pattern for agent creation.

## Architecture Improvements Implemented

### 1. Centralized Configuration (agents_config.yaml)

All agent configurations, model settings, and hyperparameters are now stored in a single YAML file located at:
```
services/orchestrator/config/agents_config.yaml
```

**Benefits:**
- ✅ Single source of truth for all configurations
- ✅ Easy to modify models and parameters without code changes
- ✅ Environment-specific configurations without rebuilding
- ✅ Version control for configuration changes

### 2. Dependency Injection with Factory Pattern

**New Components:**
- `ConfigurationManager`: Loads and manages YAML configurations
- `AgentFactory`: Creates agents based on configuration
- Enhanced `ServiceContainer`: Injects configured dependencies

**Benefits:**
- ✅ Loose coupling between components
- ✅ Easy to swap models (e.g., GPT-3.5 → Claude-3)
- ✅ Configuration-driven agent creation
- ✅ Testable with mock configurations

### 3. Separation of Logic from Configuration

**Before:** Agents had hardcoded configurations in `create_default_config()` methods
**After:** Agents receive configuration through constructor parameters

**Benefits:**
- ✅ Agents focus purely on business logic
- ✅ No need to modify agent code to change models
- ✅ Runtime configuration overrides possible
- ✅ Agent parameters are customizable per deployment

## File Structure

```
services/orchestrator/
├── config/
│   └── agents_config.yaml          # Centralized configuration file
├── app/
│   ├── core/
│   │   ├── config_manager.py       # Configuration management
│   │   ├── agent_factory.py        # Agent factory implementation
│   │   └── container.py            # Enhanced DI container
│   └── agents/
│       ├── base.py                 # Updated base agent with parameters
│       ├── planner_agent.py        # Refactored to use config
│       ├── answer_agent.py         # Refactored to use config
│       └── ...                     # Other agents
└── scripts/
    └── manage_config.py            # Configuration management utility
```

## Configuration File Structure

```yaml
system:
  default_timeout: 30
  default_max_retries: 3
  enable_verification: true
  enable_planning: true

models:
  planner_model:
    name: "mistralai/mistral-7b-instruct:free"
    temperature: 0.3
    max_tokens: 1000
    timeout: null

agents:
  planner:
    agent_type: "planner"
    model_config: "planner_model"
    system_prompt: |
      Your system prompt here...
    parameters:
      complexity_thresholds:
        simple_max_length: 50
        complex_min_length: 100
```

## Usage Examples

### 1. Changing Models

To switch from Mistral to Claude for the planner agent:

```yaml
models:
  planner_model:
    name: "anthropic/claude-3.5-haiku:beta"  # Changed model
    temperature: 0.3
    max_tokens: 1000
    timeout: null
```

No code changes required!

### 2. Adjusting Hyperparameters

To make the answer agent more creative:

```yaml
models:
  answer_model:
    temperature: 0.7  # Increased from 0.2
    max_tokens: 2000  # Increased from 1500
```

### 3. Customizing Agent Behavior

To modify planner complexity thresholds:

```yaml
agents:
  planner:
    parameters:
      complexity_thresholds:
        simple_max_length: 30    # Reduced from 50
        complex_min_length: 150  # Increased from 100
```

### 4. Environment-Specific Configurations

Create different config files for different environments:
- `config/agents_config.dev.yaml` (Development)
- `config/agents_config.prod.yaml` (Production)
- `config/agents_config.test.yaml` (Testing)

## Configuration Management Utility

Use the included management script for common tasks:

```bash
# List all configurations
python scripts/manage_config.py list

# Validate configuration file
python scripts/manage_config.py validate

# Test agent creation
python scripts/manage_config.py test

# Update model settings interactively
python scripts/manage_config.py update-model planner_model
```

## Programming Interface

### Using the Configuration Manager

```python
from core.config_manager import get_config_manager

# Load configuration
config_manager = get_config_manager("config/agents_config.yaml")

# Get agent configuration
agent_config = config_manager.get_agent_full_config("planner")
print(f"Model: {agent_config['model']}")
print(f"Temperature: {agent_config['temperature']}")
```

### Using the Agent Factory

```python
from core.agent_factory import get_agent_factory

# Create configured agents
factory = get_agent_factory()
planner = factory.create_agent("planner", agent_port)

# Override configuration at runtime
planner = factory.create_agent_with_parameters(
    "planner", 
    agent_port,
    temperature=0.5,  # Override temperature
    model="openai/gpt-4"  # Override model
)
```

### Using the Enhanced Container

```python
from core.container import get_container

# Get services with configuration support
container = get_container("config/agents_config.yaml")
orchestrator = container.get_multi_agent_orchestrator()
```

## Migration Guide

### For Existing Deployments

1. **Backup existing configuration** (if any hardcoded values need preservation)

2. **Update environment setup:**
   ```bash
   # No additional dependencies required
   # YAML parsing uses built-in Python libraries
   ```

3. **Copy configuration file:**
   ```bash
   cp config/agents_config.yaml.example config/agents_config.yaml
   ```

4. **Customize configuration** based on your requirements

5. **Update startup scripts** to use new container initialization:
   ```python
   # Old way
   container = get_container()
   
   # New way
   container = get_container("config/agents_config.yaml")
   ```

### For Development

1. **Create development configuration:**
   ```bash
   cp config/agents_config.yaml config/agents_config.dev.yaml
   ```

2. **Use faster/cheaper models for development:**
   ```yaml
   models:
     planner_model:
       name: "mistralai/mistral-7b-instruct:free"
   ```

3. **Disable expensive features:**
   ```yaml
   system:
     enable_verification: false  # Skip verification in dev
   ```

## Best Practices

### 1. Configuration Management
- **Version control configuration files** alongside code
- **Use different configs for different environments**
- **Document configuration changes** in commit messages
- **Test configuration changes** before deploying

### 2. Model Selection
- **Use free models for development/testing**
- **Use premium models for production**
- **Monitor costs** when changing to premium models
- **Set appropriate timeouts** for different model speeds

### 3. Parameter Tuning
- **Start with default values** then optimize
- **A/B test different configurations**
- **Monitor quality metrics** when changing parameters
- **Keep temperature low for factual tasks**

### 4. Security
- **Keep API keys in environment variables**, not config files
- **Protect configuration files** from unauthorized access
- **Audit configuration changes** in production

## Troubleshooting

### Common Issues

1. **Configuration file not found:**
   ```
   FileNotFoundError: Configuration file not found: config/agents_config.yaml
   ```
   **Solution:** Ensure the config file exists and path is correct

2. **Invalid YAML syntax:**
   ```
   yaml.YAMLError: Invalid YAML configuration
   ```
   **Solution:** Validate YAML syntax using `python scripts/manage_config.py validate`

3. **Unknown model configuration:**
   ```
   KeyError: Model configuration 'unknown_model' not found
   ```
   **Solution:** Check that all agents reference valid model configurations

4. **Agent creation failure:**
   ```
   ValueError: No agent class found for type: unknown_type
   ```
   **Solution:** Ensure agent types match available agent classes

### Debugging

Enable debug logging to see configuration loading:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Now configuration loading will show detailed information
```

## Future Enhancements

### Planned Features

1. **Configuration hot-reloading** without service restart
2. **Configuration validation schemas** (JSON Schema)
3. **Web UI for configuration management**
4. **Configuration versioning and rollback**
5. **Configuration templates** for common use cases
6. **Metrics and monitoring integration**

### Extension Points

1. **Custom agent types** via plugin system
2. **External configuration sources** (database, remote API)
3. **Configuration encryption** for sensitive parameters
4. **Multi-tenant configurations**

## Contributing

When adding new agents or configuration options:

1. **Update the YAML schema** in `agents_config.yaml`
2. **Add validation logic** in `ConfigurationManager`
3. **Register new agent types** in `AgentFactory`
4. **Update documentation** and examples
5. **Add tests** for new configuration options

## Performance Considerations

- **Configuration loading is cached** until service restart
- **Agent creation is lazy** (created when first accessed)  
- **Memory usage is optimized** (shared configuration objects)
- **Startup time impact is minimal** (YAML parsing is fast)

## Security Considerations

- **API keys never stored in config files**
- **Configuration files should be protected** from unauthorized access
- **Use environment variable overrides** for sensitive values
- **Audit configuration changes** in production environments