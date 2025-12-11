import os

# src/config/paths.py

# SRC_DIR = .../src/config  → src  → project root
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))      # .../src/config
SRC_DIR = os.path.dirname(CONFIG_DIR)                        # .../src
PROJECT_ROOT = os.path.dirname(SRC_DIR)                      # .../Shopkeeper Product Substitution Assistant

DATA_DIR = os.path.join(PROJECT_ROOT, "data")

PRODUCTS_PATH = os.path.join(DATA_DIR, "products.json")
CATEGORIES_PATH = os.path.join(DATA_DIR, "categories.json")
ATTRIBUTES_PATH = os.path.join(DATA_DIR, "attributes.json")
