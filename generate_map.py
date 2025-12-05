"""
Main CLI script for generating maps from occurrence data.

Usage:
    python generate_map.py --list                    # List available configurations
    python generate_map.py --config <name>            # Run specific configuration(s)
    python generate_map.py --all                      # Run all configurations
    python generate_map.py --config-file <path>       # Use custom config file
"""

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Error: PyYAML is required. Install it with: pip install pyyaml")
    sys.exit(1)

from helpers.pipeline import process_data


def load_configs(config_file="config/analyses.yaml"):
    """
    Load analysis configurations from YAML file.
    
    Args:
        config_file (str): Path to YAML configuration file
    
    Returns:
        dict: Dictionary mapping configuration names to their parameters
    """
    config_path = Path(config_file)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_file}")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if not data or 'analyses' not in data:
            raise ValueError("Configuration file must contain an 'analyses' key with a list of configurations.")
        
        # Convert list to dictionary for easy lookup
        configs = {}
        for config in data['analyses']:
            if 'name' not in config:
                raise ValueError("Each configuration must have a 'name' field.")
            
            name = config['name']
            if name in configs:
                raise ValueError(f"Duplicate configuration name: {name}")
            
            # Validate required fields
            required_fields = ['input_file', 'method', 'resolution_km']
            for field in required_fields:
                if field not in config:
                    raise ValueError(f"Configuration '{name}' missing required field: {field}")
            
            configs[name] = config
        
        return configs
    
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing YAML file: {e}")


def validate_config(config):
    """
    Validate a configuration dictionary.
    
    Args:
        config (dict): Configuration dictionary
    
    Returns:
        tuple: (is_valid, error_message)
    """
    # Check if input file exists
    input_file = Path(config['input_file'])
    if not input_file.exists():
        return False, f"Input file not found: {config['input_file']}"
    
    # Check method
    valid_methods = ['speciescount', 'chao1', 'accumulation_curve']
    if config['method'] not in valid_methods:
        return False, f"Invalid method: {config['method']}. Must be one of: {', '.join(valid_methods)}"
    
    # Check resolution
    valid_resolutions = [1, 10, 100]
    if config['resolution_km'] not in valid_resolutions:
        return False, f"Invalid resolution: {config['resolution_km']}km. Must be one of: {', '.join(map(str, valid_resolutions))}"
    
    return True, None


def list_configs(configs):
    """
    Print a list of available configurations.
    
    Args:
        configs (dict): Dictionary of configurations
    """
    if not configs:
        print("No configurations found.")
        return
    
    print(f"\nAvailable configurations ({len(configs)}):")
    print("=" * 80)
    
    for name, config in sorted(configs.items()):
        is_valid, error = validate_config(config)
        status = "✓" if is_valid else "✗"
        print(f"{status} {name}")
        print(f"    Input: {config['input_file']}")
        print(f"    Method: {config['method']}")
        print(f"    Resolution: {config['resolution_km']}km")
        if not is_valid:
            print(f"    Error: {error}")
        print()


def run_config(config_name, configs, config_file_path=None):
    """
    Run a single configuration.
    
    Args:
        config_name (str): Name of the configuration to run
        configs (dict): Dictionary of all configurations
        config_file_path (str, optional): Path to config file for error messages
    
    Returns:
        bool: True if successful, False otherwise
    """
    if config_name not in configs:
        print(f"Error: Configuration '{config_name}' not found.")
        if config_file_path:
            print(f"Check {config_file_path} for available configurations.")
        return False
    
    config = configs[config_name]
    
    # Validate configuration
    is_valid, error = validate_config(config)
    if not is_valid:
        print(f"Error: Configuration '{config_name}' is invalid: {error}")
        return False
    
    try:
        print(f"\n{'=' * 80}")
        print(f"Running configuration: {config_name}")
        print(f"{'=' * 80}")
        
        process_data(
            input_file=config['input_file'],
            method=config['method'],
            resolution_km=config['resolution_km']
        )
        
        print(f"\n✓ Successfully completed: {config_name}")
        return True
    
    except Exception as e:
        print(f"\n✗ Error running configuration '{config_name}': {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Generate maps from occurrence data using predefined configurations.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_map.py --list
  python generate_map.py --config heteroptera_chao1_100km
  python generate_map.py --config heteroptera_chao1_100km kaskaat_chao1_100km
  python generate_map.py --all
        """
    )
    
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all available configurations'
    )
    
    parser.add_argument(
        '--config',
        nargs='+',
        metavar='NAME',
        help='Run specific configuration(s) by name'
    )
    
    parser.add_argument(
        '--all',
        action='store_true',
        help='Run all configurations'
    )
    
    parser.add_argument(
        '--config-file',
        default='config/analyses.yaml',
        help='Path to configuration file (default: config/analyses.yaml)'
    )
    
    args = parser.parse_args()
    
    # Load configurations
    try:
        configs = load_configs(args.config_file)
    except Exception as e:
        print(f"Error loading configurations: {e}")
        sys.exit(1)
    
    # Handle --list option
    if args.list:
        list_configs(configs)
        return
    
    # Determine which configurations to run
    if args.all:
        config_names = list(configs.keys())
    elif args.config:
        config_names = args.config
    else:
        parser.print_help()
        print("\nError: Must specify --list, --config, or --all")
        sys.exit(1)
    
    # Run configurations
    success_count = 0
    total_count = len(config_names)
    
    for config_name in config_names:
        if run_config(config_name, configs, args.config_file):
            success_count += 1
    
    # Print summary
    print(f"\n{'=' * 80}")
    print(f"Summary: {success_count}/{total_count} configurations completed successfully")
    print(f"{'=' * 80}")
    
    if success_count < total_count:
        sys.exit(1)


if __name__ == "__main__":
    main()

