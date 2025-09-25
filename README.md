
## Setup

### First time setup

```bash
# Create virtual environment
python3.10 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Daily Usage

### Start working
```bash
source venv/bin/activate
python app.py
```

Access the app at http://localhost:5000

### Stop working
```bash
deactivate
```

## Package Management

### Install new packages
```bash
pip install package_name
pip freeze > requirements.txt
```

### Install from requirements
```bash
pip install -r requirements.txt
```