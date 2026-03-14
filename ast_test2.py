import javalang
import networkx as nx
import matplotlib.pyplot as plt

# Function to parse Java code into an AST
def java_to_ast(java_code):
    tokens = javalang.tokenizer.tokenize(java_code)
    parser = javalang.parser.Parser(tokens)
    tree = parser.parse()
    return tree

# Function to recursively traverse the AST and add nodes/edges to the graph
def visualize_ast(node, graph, parent=None):
    # Every node gets a unique identifier
    node_id = str(id(node))
    label = type(node).__name__  # Get the class name of the node

    # Add the current node to the graph with the label
    graph.add_node(node_id, label=label)

    # If a parent exists, create an edge from the parent to the current node
    if parent:
        graph.add_edge(parent, node_id)

    # Check the node's children recursively
    if isinstance(node, javalang.tree.Node):
        for child in node.children:
            if isinstance(child, javalang.tree.Node):
                visualize_ast(child, graph, node_id)  # Recurse into the child node
            elif isinstance(child, list):
                for list_item in child:
                    if isinstance(list_item, javalang.tree.Node):
                        visualize_ast(list_item, graph, node_id)  # Handle lists of child nodes

# Function to draw the graph using Matplotlib and NetworkX
def draw_graph(graph):
    labels = nx.get_node_attributes(graph, 'label')  # Extract labels for nodes
    pos = nx.spring_layout(graph)  # Layout algorithm for positioning nodes
    nx.draw(graph, pos, labels=labels, with_labels=True, node_size=2000, node_color='lightblue', font_size=10, font_color='black', font_weight='bold')
    plt.show()  # Display the graph using Matplotlib

def main():
    # Example Java code
    java_code = """
    public class Calculator {

        private int result;

        public Calculator() {
            this.result = 0;
        }

        public int add(int a, int b) {
            result = a + b;
            return result;
        }

        public int subtract(int a, int b) {
            result = a - b;
            return result;
        }

        public int multiply(int a, int b) {
            result = a * b;
            return result;
        }

        public int divide(int a, int b) {
            if (b == 0) {
                throw new IllegalArgumentException("Division by zero is not allowed.");
            }
            result = a / b;
            return result;
        }

        public static void main(String[] args) {
            Calculator calc = new Calculator();
            int sum = calc.add(10, 20);
            int diff = calc.subtract(30, 10);
            int product = calc.multiply(5, 4);
            int quotient = calc.divide(20, 4);

            System.out.println("Sum: " + sum);
            System.out.println("Difference: " + diff);
            System.out.println("Product: " + product);
            System.out.println("Quotient: " + quotient);
        }
    }

    """

    # Parse the Java code into an AST
    ast = java_to_ast(java_code)

    # Create a directed graph to represent the AST
    graph = nx.DiGraph()

    # Visualize the AST by recursively adding nodes and edges
    visualize_ast(ast, graph)

    # Draw the graph using Matplotlib
    draw_graph(graph)

if __name__ == "__main__":
    main()
