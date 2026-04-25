import os

with open('files.txt', 'r') as f:
    files = f.read().splitlines()

missing = []
present = []

for file in files:
    if file.strip():
        if os.path.exists(file):
            present.append(file)
        else:
            missing.append(file)

with open('missing_files.txt', 'w') as f:
    for file in missing:
        f.write(file + '\n')

with open('present_files.txt', 'w') as f:
    for file in present:
        f.write(file + '\n')

print(f"Total: {len(files)}, Present: {len(present)}, Missing: {len(missing)}")
