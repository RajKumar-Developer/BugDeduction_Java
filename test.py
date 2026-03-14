import os
import re
import javalang
import pandas as pd
from collections import defaultdict, Counter
import concurrent.futures
import time

def analyze_java_file(file_path):
    """
    Extract features from a Java file to identify potential bugs.
    """
    try:
        # Get file name for bug labeling
        file_name = os.path.basename(file_path)
        
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as file:
            java_code = file.read()
        
        # Parse the Java code
        tree = javalang.parse.parse(java_code)
        
        # Initialize the analysis dictionary with all required features
        analysis = {
            'file_name': file_name,
            'num_methods': 0,
            'avg_method_length': 0,
            'avg_params_per_method': 0,
            'num_return_statements': 0,
            'has_recursion': 0,
            'num_variables': 0,
            'num_global_variables': 0,
            'num_uninitialized_vars': 0,
            'num_unused_vars': 0,
            'var_shadowing_count': 0,
            'num_conditionals': 0,
            'num_loops': 0,
            'num_nested_structures': 0,
            'num_break_statements': 0,
            'num_continue_statements': 0,
            'num_try_catch': 0,
            'num_empty_catches': 0,
            'num_throws': 0,
            'max_ast_depth': 0,
            'num_method_invocations': 0,
            'num_class_attributes': 0,
            'inheritance_levels': 0,
            'num_data_dependencies': 0,
            'num_control_flow_anomalies': 0,
            'num_cyclic_dependencies': 0,
            'unsafe_api_calls': 0,
            'bug_or_not': 1 if file_name.startswith('before') else 0
        }
        
        # Collect method information
        methods = list(tree.filter(javalang.tree.MethodDeclaration))
        analysis['num_methods'] = len(methods)
        
        # Variables to track
        total_method_lines = 0
        total_params = 0
        method_names = set()
        method_calls = defaultdict(list)
        variable_declarations = {}
        variable_usages = defaultdict(int)
        variable_scopes = {}
        current_scope = []
        
        # Track method parameters
        for _, method in methods:
            method_name = method.name
            method_names.add(method_name)
            
            # Parameters per method
            params_count = len(method.parameters) if method.parameters else 0
            total_params += params_count
            
            # Estimate method length by counting tokens in body
            if method.body:
                method_tokens = len(list(javalang.tokenizer.tokenize(str(method.body))))
                total_method_lines += method_tokens // 5  # Rough estimate: 5 tokens per line
        
        # Calculate average method length and parameters
        if analysis['num_methods'] > 0:
            analysis['avg_method_length'] = total_method_lines / analysis['num_methods']
            analysis['avg_params_per_method'] = total_params / analysis['num_methods']
        
        # Count class attributes
        for _, field in tree.filter(javalang.tree.FieldDeclaration):
            analysis['num_class_attributes'] += len(field.declarators)
            
            # Track global variables
            for declarator in field.declarators:
                var_name = declarator.name
                variable_declarations[var_name] = 'global'
                analysis['num_global_variables'] += 1
                
                # Check if initialized
                if not declarator.initializer:
                    analysis['num_uninitialized_vars'] += 1
        
        # Maximum AST depth calculation
        def calculate_depth(node, current_depth=0):
            if not hasattr(node, 'children'):
                return current_depth
            
            max_child_depth = current_depth
            for child in node.children:
                if child is not None:
                    if isinstance(child, list):
                        for item in child:
                            if hasattr(item, 'children'):
                                child_depth = calculate_depth(item, current_depth + 1)
                                max_child_depth = max(max_child_depth, child_depth)
                    else:
                        child_depth = calculate_depth(child, current_depth + 1)
                        max_child_depth = max(max_child_depth, child_depth)
            
            return max_child_depth
        
        analysis['max_ast_depth'] = calculate_depth(tree)
        
        # Stack to track nested structures
        nesting_stack = []
        data_dependencies = set()
        
        # Process nodes for various metrics
        for path, node in tree:
            # Track scopes for variable shadowing detection
            if isinstance(node, (javalang.tree.MethodDeclaration, javalang.tree.ForStatement, 
                               javalang.tree.WhileStatement, javalang.tree.DoStatement, 
                               javalang.tree.IfStatement, javalang.tree.BlockStatement)):
                current_scope.append(node)
            
            # Exit scope as needed
            if hasattr(node, 'position') and node.position is not None and len(current_scope) > 0:
                if current_scope[-1].position.end < node.position.begin:
                    current_scope.pop()
            
            # Check for method invocations and recursion
            if isinstance(node, javalang.tree.MethodInvocation):
                analysis['num_method_invocations'] += 1
                
                # Check for unsafe API calls (simplified check)
                method_name = node.member
                unsafe_apis = ['exec', 'eval', 'system', 'Runtime.exec', 'ProcessBuilder', 
                              'loadLibrary', 'createTempFile', 'getConnection']
                if method_name in unsafe_apis or any(api in str(node) for api in unsafe_apis):
                    analysis['unsafe_api_calls'] += 1
                
                # Check for recursion - method calling itself
                for scope in reversed(current_scope):
                    if isinstance(scope, javalang.tree.MethodDeclaration) and scope.name == method_name:
                        analysis['has_recursion'] = 1
                        break
            
            # Return statements
            if isinstance(node, javalang.tree.ReturnStatement):
                analysis['num_return_statements'] += 1
            
            # Break statements
            if isinstance(node, javalang.tree.BreakStatement):
                analysis['num_break_statements'] += 1
            
            # Continue statements
            if isinstance(node, javalang.tree.ContinueStatement):
                analysis['num_continue_statements'] += 1
            
            # Variable declarations and initializations
            if isinstance(node, javalang.tree.LocalVariableDeclaration):
                for declarator in node.declarators:
                    var_name = declarator.name
                    scope_id = id(current_scope[-1]) if current_scope else 0
                    
                    # Check for variable shadowing
                    if var_name in variable_scopes:
                        for s_id in variable_scopes[var_name]:
                            if s_id != scope_id:
                                analysis['var_shadowing_count'] += 1
                                break
                    
                    if var_name not in variable_scopes:
                        variable_scopes[var_name] = []
                    variable_scopes[var_name].append(scope_id)
                    
                    variable_declarations[var_name] = scope_id
                    analysis['num_variables'] += 1
                    
                    # Check if uninitialized
                    if not declarator.initializer:
                        analysis['num_uninitialized_vars'] += 1
            
            # Track variable usages
            if isinstance(node, javalang.tree.MemberReference):
                var_name = node.member
                variable_usages[var_name] += 1
                
                # Track data dependencies (simplified)
                if var_name in variable_declarations:
                    data_dependencies.add(var_name)
            
            # Conditional statements
            if isinstance(node, (javalang.tree.IfStatement, javalang.tree.SwitchStatement)):
                analysis['num_conditionals'] += 1
                
                # Track nesting for conditionals
                if isinstance(node, javalang.tree.IfStatement):
                    nesting_stack.append('if')
                    
                    # Check nesting level
                    cond_count = nesting_stack.count('if')
                    loop_count = nesting_stack.count('loop')
                    
                    if cond_count > 1 or (cond_count > 0 and loop_count > 0):
                        analysis['num_nested_structures'] += 1
            
            # Loop statements
            if isinstance(node, (javalang.tree.ForStatement, javalang.tree.WhileStatement, javalang.tree.DoStatement)):
                analysis['num_loops'] += 1
                
                # Track nesting for loops
                nesting_stack.append('loop')
                
                # Check nesting level
                cond_count = nesting_stack.count('if')
                loop_count = nesting_stack.count('loop')
                
                if loop_count > 1 or (cond_count > 0 and loop_count > 0):
                    analysis['num_nested_structures'] += 1
            
            # Exit nesting stack when appropriate
            if hasattr(node, 'position') and node.position is not None and nesting_stack:
                # Check if we've exited the nesting structure
                for i in range(len(nesting_stack)-1, -1, -1):
                    if isinstance(nesting_stack[i], str):  # Skip if it's just a string marker
                        continue
                    if hasattr(nesting_stack[i], 'position'):
                        if nesting_stack[i].position.end <= node.position.begin:
                            nesting_stack.pop(i)
            
            # Try-catch blocks
            if isinstance(node, javalang.tree.TryStatement):
                analysis['num_try_catch'] += 1
                
                # Check for empty catch blocks
                if node.catches:
                    for catch in node.catches:
                        if not catch.block or not catch.block.statements:
                            analysis['num_empty_catches'] += 1
            
            # Throws statements
            if isinstance(node, javalang.tree.MethodDeclaration) and node.throws:
                analysis['num_throws'] += len(node.throws)
        
        # Calculate unused variables
        for var, count in variable_usages.items():
            if count == 0 and var in variable_declarations:
                analysis['num_unused_vars'] += 1
        
        # Set data dependencies
        analysis['num_data_dependencies'] = len(data_dependencies)
        
        # Control flow anomalies (simplified detection)
        # Looking for unreachable code patterns
        unreachable_patterns = [
            r'return\s*;.*\n\s*[^}]',  # Code after return
            r'break\s*;.*\n\s*[^}]',    # Code after break
            r'continue\s*;.*\n\s*[^}]'  # Code after continue
        ]
        for pattern in unreachable_patterns:
            matches = re.findall(pattern, java_code)
            analysis['num_control_flow_anomalies'] += len(matches)
        
        # Detect cyclic dependencies (simplified)
        # This is a basic approximation - more sophisticated analysis would require building a dependency graph
        class_imports = re.findall(r'import\s+([\w.]+);', java_code)
        self_package = re.search(r'package\s+([\w.]+);', java_code)
        if self_package:
            self_package = self_package.group(1)
            for imp in class_imports:
                if imp.startswith(self_package):
                    analysis['num_cyclic_dependencies'] += 1
        
        # Inheritance levels
        class_nodes = list(tree.filter(javalang.tree.ClassDeclaration))
        for _, cls in class_nodes:
            if cls.extends:
                analysis['inheritance_levels'] += 1
            if cls.implements:
                analysis['inheritance_levels'] += len(cls.implements)
                
        return analysis
    
    except Exception as e:
        print(f"Error analyzing {file_path}: {str(e)}")
        return None

def analyze_java_directory(directory_path, max_workers=None):
    """
    Analyze all Java files in the given directory and its subdirectories.
    Uses parallel processing for improved performance.
    """
    # List to store file paths
    java_files = []
    
    # Walk through directory to find all Java files
    for root, _, files in os.walk(directory_path):
        for file in files:
            if file.endswith('.java'):
                file_path = os.path.join(root, file)
                java_files.append(file_path)
    
    # List to store analysis results
    results = []
    
    # Process files in parallel
    start_time = time.time()
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {executor.submit(analyze_java_file, file_path): file_path for file_path in java_files}
        
        completed = 0
        total_files = len(java_files)
        
        for future in concurrent.futures.as_completed(future_to_file):
            file_path = future_to_file[future]
            completed += 1
            
            # Progress indicator
            if completed % 10 == 0 or completed == total_files:
                print(f"Processed {completed}/{total_files} files ({completed/total_files*100:.1f}%)")
            
            try:
                analysis = future.result()
                if analysis:
                    results.append(analysis)
            except Exception as e:
                print(f"Error processing {file_path}: {str(e)}")
    
    duration = time.time() - start_time
    print(f"Processing completed in {duration:.2f} seconds ({len(results)/duration:.1f} files/second)")
    
    # Convert results to DataFrame
    if results:
        df = pd.DataFrame(results)
        return df
    else:
        print("No valid analysis results found.")
        return pd.DataFrame()

def main(directory_path, output_file=None, max_workers=None):
    """
    Main function to run the analysis and save results.
    
    Args:
        directory_path: Path to directory containing Java files
        output_file: Optional path for the output file (default: java_feature_extraction.csv)
        max_workers: Optional number of worker processes (default: system-dependent)
    """
    if not output_file:
        output_file = os.path.join(directory_path, 'java_feature_extraction.csv')
    
    print(f"Starting analysis of Java files in: {directory_path}")
    
    # Analyze directory
    results_df = analyze_java_directory(directory_path, max_workers=max_workers)
    
    if not results_df.empty:
        # Save to CSV
        results_df.to_csv(output_file, index=False)
        print(f"Analysis complete. Results saved to {output_file}")
        
        # Summary statistics
        print("\nSummary statistics:")
        print(f"Total files analyzed: {len(results_df)}")
        print(f"Files with bugs: {results_df['bug_or_not'].sum()} ({results_df['bug_or_not'].sum()/len(results_df)*100:.1f}%)")
        print(f"Files without bugs: {len(results_df) - results_df['bug_or_not'].sum()} ({(1-results_df['bug_or_not'].sum()/len(results_df))*100:.1f}%)")
        
        # Feature statistics
        for col in results_df.columns:
            if col not in ['file_name', 'bug_or_not']:
                print(f"Average {col}: {results_df[col].mean():.2f}")
        
        return results_df
    else:
        print("No results to save.")
        return None

# For Jupyter notebook usage - direct execution without command line args
# Change these variables to match your environment
default_dir = r"C:\eval1"
output_file = "java_feature_extraction.csv"  # Will be saved in the directory_path
max_workers = 4  # Set to the number of CPU cores you want to use

# Call the main function directly - uncomment to run
df = main(default_dir, output_file=output_file, max_workers=max_workers)
print(df)