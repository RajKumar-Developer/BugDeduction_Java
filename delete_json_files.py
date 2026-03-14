import os

# Set the root directory
root_dir = r"C:\Users\rajk8\OneDrive\Desktop\final-year-project\dataset\java"

# Traverse through all folders and subfolders
for folder_path, subfolders, filenames in os.walk(root_dir):
    for filename in filenames:
        if filename in ["commit_info.json", "bug.json"]:  # Targeted JSON files
            file_path = os.path.join(folder_path, filename)
            os.remove(file_path)  # Delete file
            print(f"Deleted: {file_path}")

print("✅ commit_info.json and bug.json files deleted successfully!")
