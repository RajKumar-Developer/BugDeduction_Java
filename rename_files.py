import os

# Set the root directory
root_dir = r"C:\Users\rajk8\OneDrive\Desktop\final-year-project\dataset\java"

# Traverse through all folders and subfolders
for folder_path, subfolders, filenames in os.walk(root_dir):
    for filename in filenames:
        if filename.endswith(".txt"):  # Check if file is a .txt file
            old_file = os.path.join(folder_path, filename)
            new_file = os.path.join(folder_path, filename.replace(".txt", ".java"))
            os.rename(old_file, new_file)  # Rename file
            print(f"Renamed: {old_file} → {new_file}")

print("✅ All .txt files renamed to .java successfully!")
