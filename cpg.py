import subprocess

def java_to_cpg(java_file_path):
    """Converts a Java file to CPG using cpggen."""
    
    try:
        # Use cpggen to generate the CPG
        subprocess.run(["cpggen", "-o", "output_cpg", java_file_path], check=True)
        print("CPG generation successful!")

    except subprocess.CalledProcessError as e:
        print(f"Error generating CPG: {e}")

if __name__ == "__main__":
    # Provide the path to your Java file
    java_file_path = "C:/Users/rajk8/OneDrive/Desktop/finalyearProjectCode/Example.java"
    java_to_cpg(java_file_path)
