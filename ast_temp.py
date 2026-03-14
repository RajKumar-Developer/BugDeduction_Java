import javalang
import networkx as nx
import matplotlib.pyplot as plt

# Function to parse Java code into an AST
def java_to_ast(java_code):
    tokens = javalang.tokenizer.tokenize(java_code)
    parser = javalang.parser.Parser(tokens)
    tree = parser.parse()
    return tree

# Function to extract detailed node labels
def get_node_label(node):
    if isinstance(node, javalang.tree.VariableDeclarator):
        return f"Variable: {node.name}, Init: {node.initializer}"
    elif isinstance(node, javalang.tree.MethodDeclaration):
        return f"Method: {node.name}, Return Type: {node.return_type}"
    elif isinstance(node, javalang.tree.ClassDeclaration):
        return f"Class: {node.name}"
    elif isinstance(node, javalang.tree.FormalParameter):
        return f"Parameter: {node.name}, Type: {node.type}"
    elif isinstance(node, javalang.tree.Literal):
        return f"Literal: {node.value}"
    elif isinstance(node, javalang.tree.BinaryOperation):
        return f"Operation: {node.operator}"
    else:
        return type(node).__name__

# Function to recursively traverse the AST and add nodes/edges to the graph
def visualize_ast(node, graph, parent=None):
    node_id = str(id(node))
    label = get_node_label(node)
    graph.add_node(node_id, label=label)

    if parent:
        graph.add_edge(parent, node_id)

    if isinstance(node, javalang.tree.Node):
        for child in node.children:
            if isinstance(child, javalang.tree.Node):
                visualize_ast(child, graph, node_id)
            elif isinstance(child, list):
                for list_item in child:
                    if isinstance(list_item, javalang.tree.Node):
                        visualize_ast(list_item, graph, node_id)

# Function to draw the graph using Matplotlib and NetworkX
def draw_graph(graph):
    pos = nx.nx_agraph.graphviz_layout(graph, prog='dot')  # Top-to-bottom hierarchical layout
    labels = nx.get_node_attributes(graph, 'label')
    nx.draw(graph, pos, labels=labels, with_labels=True, node_size=2000, node_color='lightblue', 
            font_size=10, font_color='black', font_weight='bold', arrows=False)
    plt.show()

def main():
    java_code = """
    public class Calculator {
        public static void main(String[] args) {
           int sum = 10 + 20;
           System.out.println("Sum: " + sum);
        }
    }
    """
    
    ast = java_to_ast(java_code)
    graph = nx.DiGraph()
    visualize_ast(ast, graph)
    draw_graph(graph)

if __name__ == "__main__":
    main()
