import os

# Base directory
base_dir = "/Users/vr/Claude/Conversations/mtr-normalization-system"

# Directory structure
directories = [
    "data/input",
    "data/output", 
    "data/processed",
    "data/embeddings",
    "src/processors",
    "src/agents",
    "src/utils",
    "src/models",
    "src/schemas",
    "config",
    "logs",
    "tests",
    "notebooks"
]

# Create directories
for dir_path in directories:
    full_path = os.path.join(base_dir, dir_path)
    os.makedirs(full_path, exist_ok=True)
    print(f"✅ Created: {dir_path}")

print("\n🏗️ Project structure created successfully!")
