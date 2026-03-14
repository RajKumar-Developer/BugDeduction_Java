import javalang
import networkx as nx
import matplotlib.pyplot as plt

# Function to parse Java code into an AST
def java_to_ast(java_code):
    tokens = javalang.tokenizer.tokenize(java_code)
    parser = javalang.parser.Parser(tokens)
    tree = parser.parse()
    return tree

# Function to construct a Control Flow Graph (CFG) for a given method
def construct_cfg(method_node, graph, parent=None, block_id=0):
    # Create a new block for the method
    block_label = f"Block_{block_id}"
    graph.add_node(block_label, label=block_label)

    # Process statements in the method
    for statement in method_node.body:
        if isinstance(statement, javalang.tree.IfStatement):
            condition_block = f"Condition_{block_id}"
            true_block = f"True_{block_id}"
            false_block = f"False_{block_id}"
            graph.add_node(condition_block, label="If Condition")
            graph.add_node(true_block, label="True Branch")
            graph.add_node(false_block, label="False Branch")
            graph.add_edge(block_label, condition_block)
            graph.add_edge(condition_block, true_block)
            graph.add_edge(condition_block, false_block)
            block_id += 1
        elif isinstance(statement, javalang.tree.ForStatement):
            loop_start = f"LoopStart_{block_id}"
            loop_end = f"LoopEnd_{block_id}"
            graph.add_node(loop_start, label="For Loop Start")
            graph.add_node(loop_end, label="For Loop End")
            graph.add_edge(block_label, loop_start)
            graph.add_edge(loop_start, loop_end)
            graph.add_edge(loop_end, loop_start)
            block_id += 1
        elif isinstance(statement, javalang.tree.WhileStatement):
            while_start = f"WhileStart_{block_id}"
            while_end = f"WhileEnd_{block_id}"
            graph.add_node(while_start, label="While Loop Start")
            graph.add_node(while_end, label="While Loop End")
            graph.add_edge(block_label, while_start)
            graph.add_edge(while_start, while_end)
            graph.add_edge(while_end, while_start)
            block_id += 1
        else:
            graph.add_node(f"Statement_{block_id}", label=str(statement))
            graph.add_edge(block_label, f"Statement_{block_id}")
            block_id += 1

    return graph, block_id

# Function to draw the graph using Matplotlib and NetworkX
def draw_graph(graph):
    labels = nx.get_node_attributes(graph, 'label')
    pos = nx.spring_layout(graph)  # Layout algorithm for positioning nodes
    nx.draw(graph, pos, labels=labels, with_labels=True, node_size=2000, node_color='lightblue', font_size=10, font_color='black', font_weight='bold')
    plt.show()  # Display the graph using Matplotlib

def main():
    java_code = """
    public class Example {

        public void exampleMethod() {
            int x = 10;
            if (x > 5) {
                x = x + 1;
            } else {
                x = x - 1;
            }
            for (int i = 0; i < 10; i++) {
                x = x + i;
            }
            while (x < 20) {
                x = x + 1;
                System.out.println(x);
            }
        }

    }
    """

    # Parse the Java code into an AST
    ast = java_to_ast(java_code)

    # Find the method node to create the CFG
    for path, node in ast.filter(javalang.tree.MethodDeclaration):
        graph = nx.DiGraph()
        graph, _ = construct_cfg(node, graph)
        draw_graph(graph)
        break

if __name__ == "__main__":
    main()
