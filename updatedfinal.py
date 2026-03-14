import os
import re
import pandas as pd
from collections import defaultdict, Counter
import math
import time

# First ensure you have the required dependencies
# You can install them with:
# pip install javalang pandas openpyxl

try:
    import javalang
except ImportError:
    print("Missing required dependency. Please install javalang with: pip install javalang")
    exit(1)

def read_java_file(file_path):
    """
    Read a Java file, with special handling for method-only files.
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
            content = file.read()
            
        # Check if this is a method-only file
        file_name = os.path.basename(file_path)
        if file_name.startswith('method_') and not content.strip().startswith(('class', 'interface', 'enum', 'public class', 'package')):
            # Wrap the method in a dummy class
            content = f"""
public class DummyClass {{
    {content}
}}
"""
        return content
    except Exception as e:
        print(f"Error reading file {file_path}: {str(e)}")
        return None

def analyze_java_file(file_path):
    """
    Extract features from a Java file to identify potential bugs.
    """
    try:
        # Get file name for bug labeling
        file_name = os.path.basename(file_path)
        
        # Read file content with special handling for method files
        java_code = read_java_file(file_path)
        if not java_code:
            return None
        
        # Try to parse the Java code
        try:
            tree = javalang.parse.parse(java_code)
        except Exception as parse_error:
            # If parsing fails, try more aggressive wrapping for method snippets
            if 'method_' in file_name:
                # Try wrapping with method and class structure
                java_code = f"""
public class DummyClass {{
    public void dummyMethod() {{
        {java_code}
    }}
}}
"""
                try:
                    tree = javalang.parse.parse(java_code)
                except Exception as inner_error:
                    print(f"Failed to parse {file_path} even with wrapping: {str(inner_error)}")
                    return None
            else:
                print(f"Parse error in {file_path}: {str(parse_error)}")
                return None
        
        # Extract topic and subfolder information from path
        path_parts = file_path.split(os.sep)
        # Get topic (usually the folder name that contains numbered subfolders)
        topic_index = max(0, len(path_parts) - 3)  # two levels up from the file
        topic = path_parts[topic_index] if topic_index < len(path_parts) else "unknown"
        
        # Get subfolder (usually a number)
        subfolder_index = max(0, len(path_parts) - 2)  # one level up from the file
        subfolder = path_parts[subfolder_index] if subfolder_index < len(path_parts) else "unknown"
        
        # Initialize the analysis dictionary with all required features
        analysis = {
            'file_name': file_name,
            'file_path': file_path,
            'topic': topic,
            'subfolder': subfolder,
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
            
            # NEW FEATURES
            'cyclomatic_complexity': 0,
            'max_method_complexity': 0,
            'avg_method_complexity': 0,
            'halstead_volume': 0,
            'halstead_difficulty': 0,
            'comment_ratio': 0,
            'num_null_checks': 0,
            'num_eq_null_checks': 0,
            'num_resource_leaks': 0,
            'cognitive_complexity': 0,
            'num_todo_comments': 0,
            'num_fixme_comments': 0,
            'direct_nesting_depth': 0,
            'max_nesting_depth': 0,
            'max_method_params': 0,
            'exception_diversity': 0,
            'num_overridden_methods': 0,
            'num_static_methods': 0,
            'method_complexity_ratio': 0,  # Ratio of complexity to method size
            'comment_pattern_score': 0,    # Score based on comment patterns
            'assignment_in_if': 0,         # Potentially error-prone pattern
            'num_early_returns': 0,        # Early return pattern
            'num_while_true': 0,           # Infinite loop risk
            'index_offset_patterns': 0,    # Off-by-one error patterns
            
            'bug_or_not': 1 if 'before' in file_name.lower() else 0  # Check for 'before' anywhere in filename
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
        
        # For cyclomatic complexity
        total_complexity = 0
        max_complexity = 0
        method_complexities = []
        
        # For Halstead metrics
        operators = Counter()
        operands = Counter()
        
        # For cognitive complexity
        cognitive_complexity_total = 0
        
        # Track method parameters
        max_params = 0
        for _, method in methods:
            method_name = method.name
            method_names.add(method_name)
            
            # Parameters per method
            params_count = len(method.parameters) if method.parameters else 0
            total_params += params_count
            max_params = max(max_params, params_count)
            
            # Check for overridden methods
            if hasattr(method, 'annotations') and method.annotations:
                for annotation in method.annotations:
                    if annotation.name == 'Override':
                        analysis['num_overridden_methods'] += 1
                        break
            
            # Check for static methods
            if hasattr(method, 'modifiers') and 'static' in method.modifiers:
                analysis['num_static_methods'] += 1
            
            # Estimate method length by counting tokens in body
            if method.body:
                # Convert method body to string safely
                method_body_str = str(method.body)
                try:
                    method_tokens = len(list(javalang.tokenizer.tokenize(method_body_str)))
                    method_lines = method_tokens // 5  # Rough estimate: 5 tokens per line
                    total_method_lines += method_lines
                    
                    # Calculate complexity for this method
                    method_complexity = 1  # Base complexity
                    
                    # Add complexity for decision points in method body
                    if_count = method_body_str.count('if')
                    for_count = method_body_str.count('for')
                    while_count = method_body_str.count('while')
                    catch_count = method_body_str.count('catch')
                    case_count = method_body_str.count('case')
                    and_count = method_body_str.count('&&')
                    or_count = method_body_str.count('||')
                    
                    # Check for potentially problematic patterns
                    if 'while(true)' in method_body_str.replace(" ", "") or 'while (true)' in method_body_str:
                        analysis['num_while_true'] += 1
                        
                    # Check for early returns
                    if len(re.findall(r'if\s*\([^)]+\)\s*\{\s*return', method_body_str)) > 0:
                        analysis['num_early_returns'] += 1
                    
                    # Check for assignment in if condition
                    if len(re.findall(r'if\s*\(.*=.*\)', method_body_str)) > 0:
                        analysis['assignment_in_if'] += 1
                    
                    # Check for array index patterns that might indicate off-by-one errors
                    if len(re.findall(r'array\s*\[\s*i\s*-\s*1\s*\]', method_body_str)) > 0 or \
                       len(re.findall(r'array\s*\[\s*i\s*\+\s*1\s*\]', method_body_str)) > 0:
                        analysis['index_offset_patterns'] += 1
                    
                    # Cyclomatic complexity calculation
                    method_complexity += if_count + for_count + while_count + catch_count + case_count + and_count + or_count
                    total_complexity += method_complexity
                    method_complexities.append(method_complexity)
                    max_complexity = max(max_complexity, method_complexity)
                    
                    # Cognitive complexity - more weight to deeply nested structures
                    max_nesting = 0
                    nesting_level = 0
                    for line in method_body_str.split('\n'):
                        # Increment nesting level for control structures
                        if re.search(r'\s*(if|for|while|switch)', line) and '{' in line:
                            nesting_level += 1
                        # Decrement nesting level when closing blocks
                        elif '}' in line and nesting_level > 0:
                            nesting_level -= 1
                        
                        max_nesting = max(max_nesting, nesting_level)
                    
                    # Update direct_nesting_depth feature
                    analysis['direct_nesting_depth'] = max(analysis['direct_nesting_depth'], max_nesting)
                    
                    # Cognitive complexity calculation with nesting weights
                    cognitive_complexity = method_complexity + (max_nesting * 2)
                    cognitive_complexity_total += cognitive_complexity
                    
                    # Store complexity to method size ratio
                    if method_lines > 0:
                        method_complexity_ratio = method_complexity / method_lines
                        analysis['method_complexity_ratio'] += method_complexity_ratio / len(methods) if len(methods) > 0 else 0
                        
                except Exception as token_error:
                    # If tokenizing fails, use a simple line count estimate
                    method_lines = method_body_str.count('\n') + 1
                    total_method_lines += method_lines
        
        # Set max method params
        analysis['max_method_params'] = max_params
        
        # Calculate average method length and parameters
        if analysis['num_methods'] > 0:
            analysis['avg_method_length'] = total_method_lines / analysis['num_methods']
            analysis['avg_params_per_method'] = total_params / analysis['num_methods']
            analysis['cyclomatic_complexity'] = total_complexity
            analysis['max_method_complexity'] = max_complexity
            analysis['avg_method_complexity'] = total_complexity / analysis['num_methods']
            analysis['cognitive_complexity'] = cognitive_complexity_total
        
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
        
        # Maximum AST depth calculation - simplified to avoid recursion errors
        def calculate_depth(node, current_depth=0, max_depth=100):
            if current_depth >= max_depth or not hasattr(node, 'children'):
                return current_depth
            
            max_child_depth = current_depth
            for child in node.children:
                if child is not None:
                    if isinstance(child, list):
                        for item in child:
                            if item is not None and hasattr(item, 'children'):
                                child_depth = calculate_depth(item, current_depth + 1, max_depth)
                                max_child_depth = max(max_child_depth, child_depth)
                    else:
                        child_depth = calculate_depth(child, current_depth + 1, max_depth)
                        max_child_depth = max(max_child_depth, child_depth)
            
            return max_child_depth
        
        # Limit max depth calculation to avoid stack overflows
        try:
            analysis['max_ast_depth'] = calculate_depth(tree, max_depth=50)
        except RecursionError:
            analysis['max_ast_depth'] = 50  # Set a default if recursion limit is hit
        
        # Stack to track nested structures
        nesting_stack = []
        data_dependencies = set()
        
        # Comment analysis
        comments_length = 0
        code_length = len(java_code)
        # Extract comments
        try:
            comment_patterns = [
                r'/\*\*.*?\*/',  # JavaDoc comment
                r'/\*.*?\*/',    # Multi-line comment
                r'//.*?$'        # Single-line comment
            ]
            
            all_comments = []
            for pattern in comment_patterns:
                if pattern.endswith('$'):
                    # Line-based pattern
                    for line in java_code.split('\n'):
                        matches = re.findall(pattern, line, re.DOTALL)
                        all_comments.extend(matches)
                else:
                    # Multi-line pattern
                    matches = re.findall(pattern, java_code, re.DOTALL)
                    all_comments.extend(matches)
            
            # Calculate total comment length
            for comment in all_comments:
                comments_length += len(comment)
                
                # Check for TODO/FIXME comments
                if 'TODO' in comment.upper():
                    analysis['num_todo_comments'] += 1
                if 'FIXME' in comment.upper():
                    analysis['num_fixme_comments'] += 1
            
            # Calculate comment to code ratio
            if code_length > 0:
                analysis['comment_ratio'] = comments_length / code_length
                
            # Comment pattern analysis
            pattern_score = 0
            
            # Score method header comments
            for method in methods:
                method_name = method[1].name
                method_pattern = f"(?:/\\*\\*.*?\\*/|//.*?\\n)\\s*.*?{method_name}\\s*\\("
                if re.search(method_pattern, java_code, re.DOTALL):
                    pattern_score += 1
            
            # Normalize pattern score
            if len(methods) > 0:
                analysis['comment_pattern_score'] = pattern_score / len(methods)
            
        except Exception as e:
            print(f"Error in comment analysis: {str(e)}")
        
        # Maximum nesting depth - track across all methods
        max_nesting_depth = 0
        current_nesting = 0
        
        # Process nodes for various metrics - using a safer approach
        try:
            for path, node in tree:
                # Track scopes for variable shadowing detection
                if isinstance(node, (javalang.tree.MethodDeclaration, javalang.tree.ForStatement, 
                                  javalang.tree.WhileStatement, javalang.tree.DoStatement, 
                                  javalang.tree.IfStatement, javalang.tree.BlockStatement)):
                    current_scope.append(node)
                    
                    # Track nesting depth
                    if isinstance(node, (javalang.tree.ForStatement, javalang.tree.WhileStatement, 
                                      javalang.tree.DoStatement, javalang.tree.IfStatement)):
                        current_nesting += 1
                        max_nesting_depth = max(max_nesting_depth, current_nesting)
                
                # Safe scope exit (simplified)
                if len(current_scope) > 0 and isinstance(path, list) and len(path) > 0:
                    # Simple check - if we're at a different node than the current scope's last node, pop
                    if path[-1] != current_scope[-1]:
                        current_scope.pop()
                        
                        # Adjust nesting depth when exiting control structures
                        if isinstance(path[-1], (javalang.tree.ForStatement, javalang.tree.WhileStatement, 
                                             javalang.tree.DoStatement, javalang.tree.IfStatement)) and current_nesting > 0:
                            current_nesting -= 1
                
                # Track Halstead metrics
                if isinstance(node, javalang.tree.BinaryOperation):
                    operators[node.operator] += 1
                    # Count operands
                    if hasattr(node, 'operandl') and node.operandl:
                        if isinstance(node.operandl, javalang.tree.Literal):
                            operands[str(node.operandl.value)] += 1
                        elif hasattr(node.operandl, 'member'):
                            operands[node.operandl.member] += 1
                    if hasattr(node, 'operandr') and node.operandr:
                        if isinstance(node.operandr, javalang.tree.Literal):
                            operands[str(node.operandr.value)] += 1
                        elif hasattr(node.operandr, 'member'):
                            operands[node.operandr.member] += 1
                
                # Check for method invocations and recursion
                if isinstance(node, javalang.tree.MethodInvocation):
                    analysis['num_method_invocations'] += 1
                    
                    # Check for unsafe API calls (simplified check)
                    method_name = node.member
                    unsafe_apis = ['exec', 'eval', 'system', 'Runtime.exec', 'ProcessBuilder', 
                                  'loadLibrary', 'createTempFile', 'getConnection']
                    if method_name in unsafe_apis or any(api in str(node) for api in unsafe_apis):
                        analysis['unsafe_api_calls'] += 1
                    
                    # Check for null checks
                    if method_name == 'equals' and hasattr(node, 'arguments') and node.arguments:
                        for arg in node.arguments:
                            if isinstance(arg, javalang.tree.Literal) and arg.value == 'null':
                                analysis['num_eq_null_checks'] += 1
                    
                    # Check for potential resource leaks
                    resource_mgmt_methods = ['close', 'dispose', 'release']
                    if method_name in resource_mgmt_methods:
                        analysis['num_resource_leaks'] -= 1  # Decrement as this indicates proper resource management
                    
                    # Check for resource acquisition (that might need management)
                    resource_acq_patterns = ['new FileInputStream', 'new Socket', 'getConnection']
                    if any(pattern in str(node) for pattern in resource_acq_patterns):
                        analysis['num_resource_leaks'] += 1  # Increment as a potential leak
                    
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
                    try:
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
                    except (AttributeError, IndexError, TypeError) as e:
                        # More detailed error reporting
                        print(f"Error processing variable declaration: {e}")
                        pass
                
                # Track variable usages
                if isinstance(node, javalang.tree.MemberReference):
                    var_name = node.member
                    variable_usages[var_name] += 1
                    
                    # Track data dependencies (simplified)
                    if var_name in variable_declarations:
                        data_dependencies.add(var_name)
                
                # Check for null checks
                if isinstance(node, javalang.tree.BinaryOperation) and node.operator == '==':
                    if (isinstance(node.operandl, javalang.tree.Literal) and str(node.operandl.value) == 'null') or \
                       (isinstance(node.operandr, javalang.tree.Literal) and str(node.operandr.value) == 'null'):
                        analysis['num_null_checks'] += 1
                
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
                
                # Exit nesting stack when appropriate (simplified)
                if nesting_stack and isinstance(nesting_stack[-1], str):
                    if isinstance(node, javalang.tree.BlockStatement):
                        # Simple pop on block exit
                        nesting_stack.pop() if nesting_stack else None
                
                # Try-catch blocks
                if isinstance(node, javalang.tree.TryStatement):
                    analysis['num_try_catch'] += 1
                    
                    # Check for empty catch blocks - safely handle missing attributes
                    if hasattr(node, 'catches') and node.catches:
                        for catch in node.catches:
                            try:
                                if not catch.block or not catch.block.statements:
                                    analysis['num_empty_catches'] += 1
                            except (AttributeError, TypeError):
                                # Skip if catch block has issues
                                pass
                        
                        # Calculate exception diversity
                        exception_types = set()
                        for catch in node.catches:
                            if hasattr(catch, 'parameter') and hasattr(catch.parameter, 'type'):
                                exception_types.add(str(catch.parameter.type))
                        
                        analysis['exception_diversity'] += len(exception_types)
                
                # Throws statements
                if isinstance(node, javalang.tree.MethodDeclaration) and hasattr(node, 'throws') and node.throws:
                    analysis['num_throws'] += len(node.throws)
        except Exception as e:
            print(f"Error while traversing AST for {file_path}: {str(e)}")
            # Continue with partial analysis instead of returning None
        
        # Calculate unused variables
        for var, count in variable_usages.items():
            if count == 0 and var in variable_declarations:
                analysis['num_unused_vars'] += 1
        
        # Set data dependencies
        analysis['num_data_dependencies'] = len(data_dependencies)
        
        # Set maximum nesting depth
        analysis['max_nesting_depth'] = max_nesting_depth
        
        # Calculate Halstead complexity metrics
        n1 = len(operators)  # Unique operators
        n2 = len(operands)   # Unique operands
        N1 = sum(operators.values())  # Total operators
        N2 = sum(operands.values())   # Total operands
        
        if n1 > 0 and n2 > 0:
            # Calculate Halstead volume
            n = n1 + n2
            N = N1 + N2
            if n > 0:
                analysis['halstead_volume'] = N * (math.log2(n) if n > 1 else 1)
            
            # Calculate Halstead difficulty
            if n2 > 0:
                analysis['halstead_difficulty'] = (n1 / 2) * (N2 / n2)
        
        # Control flow anomalies (simplified detection)
        # Looking for unreachable code patterns
        try:
            unreachable_patterns = [
                r'return\s*;.*\n\s*[^}]',  # Code after return
                r'break\s*;.*\n\s*[^}]',    # Code after break
                r'continue\s*;.*\n\s*[^}]'  # Code after continue
            ]
            for pattern in unreachable_patterns:
                matches = re.findall(pattern, java_code)
                analysis['num_control_flow_anomalies'] += len(matches)
        except Exception as e:
            print(f"Error in control flow analysis: {str(e)}")
        
        # Detect cyclic dependencies (simplified)
        try:
            class_imports = re.findall(r'import\s+([\w.]+);', java_code)
            self_package = re.search(r'package\s+([\w.]+);', java_code)
            if self_package:
                self_package = self_package.group(1)
                for imp in class_imports:
                    if imp.startswith(self_package):
                        analysis['num_cyclic_dependencies'] += 1
        except Exception as e:
            print(f"Error in cyclic dependency analysis: {str(e)}")
        
        # Inheritance levels
        try:
            class_nodes = list(tree.filter(javalang.tree.ClassDeclaration))
            for _, cls in class_nodes:
                if hasattr(cls, 'extends') and cls.extends:
                    analysis['inheritance_levels'] += 1
                if hasattr(cls, 'implements') and cls.implements:
                    analysis['inheritance_levels'] += len(cls.implements)
        except Exception as e:
            print(f"Error in inheritance analysis: {str(e)}")
                
        return analysis
    
    except Exception as e:
        print(f"Error analyzing {file_path}: {str(e)}")
        return None

def analyze_java_directory(directory_path, max_files=None):
    """
    Analyze all Java files in the given directory and its subdirectories.
    
    Args:
        directory_path: Path to the root directory containing Java files
        max_files: Optional maximum number of files to process (for testing/debugging)
    """
    # List to store file paths
    java_files = []
    
    # Dictionary to track folder structure and counts
    folder_structure = {}
    
    # Walk through directory to find all Java files
    print(f"Searching for Java files in {directory_path}...")
    
    # Check if directory exists
    if not os.path.exists(directory_path):
        print(f"Error: Directory '{directory_path}' does not exist.")
        return pd.DataFrame()
    
    try:
        for root, dirs, files in os.walk(directory_path):
            java_count = 0
            for file in files:
                if file.endswith('.java'):
                    java_count += 1
                    file_path = os.path.join(root, file)
                    java_files.append(file_path)
            
            if java_count > 0:
                relative_path = os.path.relpath(root, directory_path)
                folder_structure[relative_path] = java_count
    except Exception as e:
        print(f"Error scanning directory: {str(e)}")
        return pd.DataFrame()
    
    # Print folder structure summary
    print("\nFolder Structure Summary:")
    total_files = 0
    for folder, count in sorted(folder_structure.items()):
        print(f"  {folder}: {count} Java files")
        total_files += count
    
    print(f"\nTotal Java files found: {total_files}")
    
    if total_files == 0:
        print("No Java files found to analyze.")
        return pd.DataFrame()
    
    if max_files and max_files < len(java_files):
        print(f"Limiting analysis to first {max_files} files for testing")
        java_files = java_files[:max_files]
    
    # List to store analysis results
    results = []
    
    # Process files sequentially
    start_time = time.time()
    error_count = 0
    success_count = 0
    
    total_files = len(java_files)
    print(f"\nStarting analysis of {total_files} Java files...")
    
    for idx, file_path in enumerate(java_files):
        # Progress indicator (more frequent for large datasets)
        if (idx + 1) % 20 == 0 or idx + 1 == total_files:
            elapsed_time = time.time() - start_time
            files_per_second = (idx + 1) / elapsed_time if elapsed_time > 0 else 0
            eta = (total_files - (idx + 1)) / files_per_second if files_per_second > 0 else "unknown"
            eta_str = f"{eta:.1f} seconds" if isinstance(eta, float) else eta
            
            print(f"Processed {idx+1}/{total_files} files ({(idx+1)/total_files*100:.1f}%) - "
                  f"Success: {success_count}, Errors: {error_count} - "
                  f"Speed: {files_per_second:.1f} files/sec - ETA: {eta_str}")
        
        try:
            analysis = analyze_java_file(file_path)
            if analysis:
                results.append(analysis)
                success_count += 1
            else:
                error_count += 1
        except Exception as e:
            error_count += 1
            print(f"Unexpected error processing {file_path}: {str(e)}")
    
    duration = time.time() - start_time
    print(f"\nProcessing completed in {duration:.2f} seconds ({success_count/duration:.1f} files/second)")
    print(f"Successfully analyzed: {success_count}/{total_files} files ({success_count/total_files*100:.1f}%)")
    print(f"Failed to analyze: {error_count}/{total_files} files ({error_count/total_files*100:.1f}%)")
    
    # Convert results to DataFrame
    if results:
        df = pd.DataFrame(results)
        return df
    else:
        print("No valid analysis results found.")
        return pd.DataFrame()

def analyze_dataset(dataset_path, output_file=None, max_files=None):
    """
    Main function to run the analysis on the hierarchical dataset structure.
    
    Args:
        dataset_path: Path to the dataset root directory
        output_file: Optional path for the output file
        max_files: Optional maximum number of files to process (for testing)
    """
    if not output_file:
        output_file = os.path.join(dataset_path, 'java_feature_extraction.xlsx')
    
    print(f"Starting analysis of Java files in dataset: {dataset_path}")
    
    # Analyze all nested directories
    results_df = analyze_java_directory(dataset_path, max_files)
    
    if not results_df.empty:
        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # Save to CSV first (more reliable for large datasets)
        csv_output = output_file.replace('.xlsx', '.csv')
        results_df.to_csv(csv_output, index=False)
        print(f"Results saved as CSV to {csv_output}")
        
        try:
            # Try to save as Excel (might fail for very large datasets)
            results_df.to_excel(output_file, index=False, engine='openpyxl')
            print(f"Results also saved as Excel to {output_file}")
        except Exception as e:
            print(f"Warning: Could not save to Excel format due to: {str(e)}")
            print("The CSV file contains all data and can be opened in Excel.")
        
        # Summary statistics
        print("\nSummary statistics:")
        print(f"Total files analyzed: {len(results_df)}")
        
        if 'bug_or_not' in results_df.columns:
            print(f"Files with bugs: {results_df['bug_or_not'].sum()} "
                  f"({results_df['bug_or_not'].sum()/len(results_df)*100:.1f}%)")
            print(f"Files without bugs: {len(results_df) - results_df['bug_or_not'].sum()} "
                  f"({(1-results_df['bug_or_not'].sum()/len(results_df))*100:.1f}%)")
        
        # Topic statistics
        if 'topic' in results_df.columns:
            print("\nFiles by topic:")
            topic_counts = results_df['topic'].value_counts()
            for topic, count in topic_counts.items():
                print(f"  {topic}: {count} files")
        
        # Feature statistics
        print("\nFeature averages:")
        for col in results_df.columns:
            if col not in ['file_name', 'file_path', 'topic', 'subfolder', 'bug_or_not'] and results_df[col].dtype in ['int64', 'float64']:
                print(f"  Average {col}: {results_df[col].mean():.2f}")
        
        return results_df
    else:
        print("No results to save.")
        return None

def test_file_parsing(directory_path, num_files=5):
    """
    Test the file parsing on a small subset of files.
    Useful for debugging parsing issues.
    """
    print(f"Testing file parsing in {directory_path}...")
    
    # Check if directory exists
    if not os.path.exists(directory_path):
        print(f"Error: Directory '{directory_path}' does not exist.")
        return
    
    # Find some method files to test
    method_files = []
    for root, _, files in os.walk(directory_path):
        for file in files:
            if file.startswith('method_') and file.endswith('.java'):
                method_files.append(os.path.join(root, file))
                if len(method_files) >= num_files:
                    break
        if len(method_files) >= num_files:
            break
    
    if not method_files:
        print("No method files found for testing. Testing regular Java files instead.")
        # Try to find any Java files
        for root, _, files in os.walk(directory_path):
            for file in files:
                if file.endswith('.java'):
                    method_files.append(os.path.join(root, file))
                    if len(method_files) >= num_files:
                        break
            if len(method_files) >= num_files:
                break
    
    if not method_files:
        print("No Java files found for testing.")
        return
    
    # Test each file
    for file_path in method_files:
        print(f"\nTesting: {file_path}")
        
        try:
            # Read the original content
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                original_content = f.read()
            
            print("Original content:")
            print(original_content[:200] + "..." if len(original_content) > 200 else original_content)
            
            # Try parsing with our wrapper
            java_code = read_java_file(file_path)
            print("\nWrapped content:")
            print(java_code[:200] + "..." if len(java_code) > 200 else java_code)
            
            # Test parsing
            try:
                tree = javalang.parse.parse(java_code)
                print("\nParsing successful!")
                print(f"Methods found: {len(list(tree.filter(javalang.tree.MethodDeclaration)))}")
            except Exception as e:
                print(f"\nParsing failed: {str(e)}")
                
                # Try with more aggressive wrapping
                try:
                    aggressive_wrapper = f"""
public class DummyClass {{
    public void dummyMethod() {{
        {original_content}
    }}
}}
"""
                    tree = javalang.parse.parse(aggressive_wrapper)
                    print("\nParsing with aggressive wrapping successful!")
                    print(f"Methods found: {len(list(tree.filter(javalang.tree.MethodDeclaration)))}")
                except Exception as e2:
                    print(f"\nAggressive wrapping also failed: {str(e2)}")
        except Exception as e:
            print(f"Error testing file: {str(e)}")

if __name__ == "__main__":
    # Set a default path or ask the user for the path
    default_dataset_path = "./dataset"  # Change to a default location
    
    # Ask user for path with the default as a suggestion
    dataset_path = input(f"Enter the path to your Java dataset [default: {default_dataset_path}]: ").strip()
    
    # Use default if nothing was entered
    if not dataset_path:
        dataset_path = default_dataset_path
        print(f"Using default path: {dataset_path}")
    
    # Create output path based on dataset location
    output_file = os.path.join(dataset_path, "java_features_analysis.xlsx")
    
    # Check if the directory exists
    if not os.path.exists(dataset_path):
        print(f"Warning: The directory '{dataset_path}' does not exist.")
        create_dir = input("Would you like to create this directory? (y/n): ").lower().strip()
        if create_dir == 'y':
            try:
                os.makedirs(dataset_path)
                print(f"Directory '{dataset_path}' created successfully.")
            except Exception as e:
                print(f"Failed to create directory: {str(e)}")
                exit(1)
        else:
            print("Exiting program.")
            exit(1)
    
    # Ask if user wants to run a test first
    run_test = input("Would you like to test parsing on a few files first? (y/n): ").lower().strip()
    if run_test == 'y':
        num_test_files = 5
        try:
            num_test_files = int(input(f"How many files to test? [default: {num_test_files}]: ").strip() or num_test_files)
        except ValueError:
            print(f"Using default of {num_test_files} files.")
        
        test_file_parsing(dataset_path, num_files=num_test_files)
        
        continue_analysis = input("\nContinue with full analysis? (y/n): ").lower().strip()
        if continue_analysis != 'y':
            print("Exiting program.")
            exit(0)
    
    # Ask if user wants to limit the number of files
    limit_files = input("Would you like to limit the number of files for analysis? (y/n): ").lower().strip()
    max_files = None
    if limit_files == 'y':
        try:
            max_files = int(input("Maximum number of files to analyze: ").strip())
            print(f"Limiting analysis to {max_files} files.")
        except ValueError:
            print("Invalid input. Analyzing all files.")
    
    # Run the analysis
    df = analyze_dataset(dataset_path, output_file, max_files=max_files)
    
    if df is not None and not df.empty:
        print("\nAnalysis completed successfully!")
    else:
        print("\nAnalysis completed with no results or errors occurred.")