import javalang
import networkx as nx
import matplotlib.pyplot as plt

# Function to parse Java code into an AST
def java_to_ast(java_code):
    tokens = javalang.tokenizer.tokenize(java_code)
    parser = javalang.parser.Parser(tokens)
    tree = parser.parse()
    return tree

# Function to construct a Directed Acyclic Graph (DAG)
def construct_dag(tree, graph):
    # Iterate through class declarations
    for class_decl in tree.filter(javalang.tree.ClassDeclaration):
        class_node = class_decl.name
        graph.add_node(class_node, label=f"Class: {class_node}")

        # Add edges for class dependencies
        for base_class in class_decl.extends:
            graph.add_edge(class_node, base_class)
        
        # Iterate through methods
        for method in class_decl.methods:
            method_node = f"{class_node}.{method.name}"
            graph.add_node(method_node, label=f"Method: {method.name}")
            graph.add_edge(class_node, method_node)  # Edge from class to method
            
            # Add edges for method calls within the method
            for statement in method.body:
                if isinstance(statement, javalang.tree.MethodInvocation):
                    callee = statement.method.name
                    callee_node = f"{class_node}.{callee}"
                    graph.add_edge(method_node, callee_node)
    
    return graph

# Function to draw the graph using Matplotlib and NetworkX
def draw_dag(graph):
    labels = nx.get_node_attributes(graph, 'label')
    pos = nx.spring_layout(graph, seed=42)  # Layout algorithm for positioning nodes
    nx.draw(graph, pos, labels=labels, with_labels=True, node_size=2000, node_color='lightblue', font_size=10, font_color='black', font_weight='bold', arrows=True)
    plt.show()  # Display the graph using Matplotlib

def main():
    java_code = """
    public class Example {
        
        private Helper helper;

        public Example() {
            this.helper = new Helper();
        }

        public void doWork() {
            helper.performTask();
        }
    }
    
    public class Helper {
        
        public void performTask() {
            System.out.println("Task performed.");
        }
    }
    """

    # Parse the Java code into an AST
    ast = java_to_ast(java_code)

    # Create a directed graph to represent the DAG
    graph = nx.DiGraph()

    # Construct the DAG from the AST
    graph = construct_dag(ast, graph)

    # Draw the DAG using Matplotlib
    draw_dag(graph)

if __name__ == "__main__":
    main()
