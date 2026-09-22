import os

base_dir = r"C:\Users\meaks\.gemini\antigravity\scratch\ajrasakha-feedback-system\backend"
app_dir = os.path.join(base_dir, "app")
models_dir = os.path.join(app_dir, "models")
services_dir = os.path.join(app_dir, "services")
routers_dir = os.path.join(app_dir, "routers")

for d in [base_dir, app_dir, models_dir, services_dir, routers_dir]:
    os.makedirs(d, exist_ok=True)

# 1. __init__.py
for d in [app_dir, models_dir, services_dir, routers_dir]:
    with open(os.path.join(d, "__init__.py"), "w", encoding="utf-8") as f:
        f.write("# Init\n")

print("Created directories and init files.")
