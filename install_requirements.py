import subprocess
import sys
import os
from typing import List, Tuple

def print_colored(text: str, color: str) -> None:
    """Print text in specified color"""
    colors = {
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'end': '\033[0m'
    }
    print(f"{colors.get(color, '')}{text}{colors['end']}")

def check_python_version() -> bool:
    """Check if Python version is compatible"""
    required_version = (3, 8)
    max_version = (3, 12)  # Maximum supported version
    current_version = sys.version_info[:2]
    
    if current_version < required_version:
        print_colored(f"Error: Python {required_version[0]}.{required_version[1]} or higher is required.", 'red')
        print_colored(f"Current version: {current_version[0]}.{current_version[1]}", 'red')
        return False
    elif current_version > max_version:
        print_colored(f"Error: Python {max_version[0]}.{max_version[1]} or lower is required.", 'red')
        print_colored(f"Current version: {current_version[0]}.{current_version[1]}", 'red')
        return False
    return True

def upgrade_pip() -> bool:
    """Upgrade pip to the latest version"""
    print_colored("Upgrading pip...", 'blue')
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
        print_colored("✓ Pip upgraded successfully", 'green')
        return True
    except subprocess.CalledProcessError as e:
        print_colored(f"✗ Failed to upgrade pip: {str(e)}", 'red')
        return False

def install_requirements() -> bool:
    """Install all required packages"""
    print_colored("Installing required packages...", 'blue')
    
    # List of required packages with their versions
    requirements = [
        'flask==2.3.3',
        'flask-cors==4.0.0',
        'flask-sqlalchemy==3.0.5',
        'flask-migrate==4.0.4',
        'flask-mail==0.9.1',
        'apscheduler==3.10.1',
        'razorpay==1.4.2',
        'stripe==6.5.0',
        'sqlalchemy==1.4.41',
        'python-dotenv==1.0.0',
        'flask-mysqldb==2.0.0',
        'pymysql==1.1.0',
        'werkzeug==2.3.7',
        'jinja2==3.1.2',
        'itsdangerous==2.0.1',
        'click==8.1.7',
        'blinker==1.6.2',
        'alembic==1.11.1',
        'mako==1.2.4',
        'markupsafe==2.1.3',
        'typing-extensions==4.7.1',
        'greenlet==2.0.2',
        'tzdata==2023.3',
        'tzlocal==5.0.1',
        'requests==2.31.0',
        'urllib3==2.0.4',
        'certifi==2023.7.22',
        'charset-normalizer==3.2.0',
        'idna==3.4',
        'numpy==1.24.3'
    ]

    try:
        # Install each package individually for better error tracking
        for package in requirements:
            print_colored(f"Installing {package}...", 'yellow')
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                print_colored(f"✓ Successfully installed {package}", 'green')
            except subprocess.CalledProcessError as e:
                print_colored(f"✗ Failed to install {package}: {str(e)}", 'red')
                if package == 'flask-mysqldb':
                    print_colored("Note: Skipping flask-mysqldb as it's not critical for SQLite", 'yellow')
                    continue
                return False

        print_colored("\nAll packages installed successfully!", 'green')
        return True
    except subprocess.CalledProcessError as e:
        print_colored(f"\n✗ Failed to install packages: {str(e)}", 'red')
        return False

def verify_installation() -> bool:
    """Verify that all required packages are installed correctly"""
    print_colored("\nVerifying installation...", 'blue')
    
    try:
        # Import all required packages to verify installation
        import flask
        import flask_cors
        import flask_sqlalchemy
        import flask_migrate
        import flask_mail
        import apscheduler
        import razorpay
        import stripe
        import sqlalchemy
        import dotenv
        
        print_colored("✓ All packages verified successfully!", 'green')
        return True
    except ImportError as e:
        print_colored(f"✗ Verification failed: {str(e)}", 'red')
        return False

def main():
    """Main installation function"""
    print_colored("\n=== Career Navigator - Package Installation ===\n", 'blue')
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Upgrade pip
    if not upgrade_pip():
        sys.exit(1)
    
    # Install requirements
    if not install_requirements():
        sys.exit(1)
    
    # Verify installation
    if not verify_installation():
        sys.exit(1)
    
    print_colored("\n=== Installation Complete! ===", 'green')
    print_colored("\nYou can now run the application using:", 'blue')
    print_colored("python app.py", 'yellow')

if __name__ == "__main__":
    main() 