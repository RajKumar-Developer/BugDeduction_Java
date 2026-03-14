import javalang
from graphviz import Digraph

def java_to_ast(java_code):
    tokens = javalang.tokenizer.tokenize(java_code)
    parser = javalang.parser.Parser(tokens)
    tree = parser.parse()
    return tree

def visualize_ast(node, graph, parent=None):
    node_id = str(id(node))
    label = type(node).__name__
    graph.node(node_id, label)
    
    if parent:
        graph.edge(parent, node_id)

    # Loop over the node's attributes and check for children
    for attr_name, attr_value in vars(node).items():
        if isinstance(attr_value, javalang.tree.Node):
            visualize_ast(attr_value, graph, node_id)
        elif isinstance(attr_value, list):
            for child in attr_value:
                if isinstance(child, javalang.tree.Node):
                    visualize_ast(child, graph, node_id)

def main():
    java_code = """
    public class HelloWorld {
        public static void main(String[] args) {
            System.out.println("Hello, World!");
        }
    }
    """
    ast = java_to_ast(java_code)
    graph = Digraph()
    visualize_ast(ast, graph)
    graph.render('ast', format='png', cleanup=True)

if __name__ == "__main__":
    main()

