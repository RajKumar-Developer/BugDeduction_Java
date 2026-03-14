import javalang
import networkx as nx
import matplotlib.pyplot as plt

# Function to parse Java code into an AST
def java_to_ast(java_code):
    tokens = javalang.tokenizer.tokenize(java_code)
    parser = javalang.parser.Parser(tokens)
    tree = parser.parse()
    return tree

# Recursive function to construct AST as a graph
def construct_ast(node, graph, parent=None):
    if isinstance(node, javalang.tree.Node):
        # Create a unique node identifier with the type of node and its id
        node_name = f"{type(node).__name__}_{id(node)}"
        
        graph.add_node(node_name, label=type(node).__name__)

        if parent:
            graph.add_edge(parent, node_name)

        # Check if the node has children and iterate through them
        if hasattr(node, 'children') and callable(node.children):
            for child in node.children():
                # Ensure child is either a list or a Node
                if isinstance(child, list):
                    for subchild in child:
                        if isinstance(subchild, javalang.tree.Node):  # Check for valid node
                            construct_ast(subchild, graph, node_name)
                elif isinstance(child, javalang.tree.Node):
                    construct_ast(child, graph, node_name)

# Function to draw the graph using Matplotlib and NetworkX
def draw_graph(graph, title):
    labels = nx.get_node_attributes(graph, 'label')
    pos = nx.spring_layout(graph, seed=42)  # Layout algorithm for positioning nodes
    plt.figure(figsize=(12, 8))
    nx.draw(graph, pos, labels=labels, with_labels=True, node_size=2000, node_color='lightblue', font_size=10, font_weight='bold', arrows=True)
    plt.title(title)
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

    # Create a directed graph for the AST
    ast_graph = nx.DiGraph()

    # Construct the AST
    construct_ast(ast, ast_graph)

    # Draw the AST
    draw_graph(ast_graph, "Abstract Syntax Tree (AST)")

if __name__ == "__main__":
    main()
