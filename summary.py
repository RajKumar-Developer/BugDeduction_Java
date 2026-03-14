import javalang

java_code = """
public class QuickSort {
    public static void quickSort(int[] arr, int low, int high) {
        if (low < high) {
            int pi = partition(arr, low, high);
            quickSort(arr, low, pi - 1);
            quickSort(arr, pi + 1, high);
        }
    }

    public static int partition(int[] arr, int low, int high) {
        int pivot = arr[high];
        int i = (low - 1);
        for (int j = low; j < high; j++) {
            if (arr[j] < pivot) {
                i++;
                int temp = arr[i];
                arr[i] = arr[j];
                arr[j] = temp;
            }
        }
        int temp = arr[i + 1];
        arr[i + 1] = arr[high];
        arr[high] = temp;
        return i + 1;
    }

    public static void main(String[] args) {
        int[] arr = {10, 7, 8, 9, 1, 5};
        int n = arr.length;
        quickSort(arr, 0, n - 1);
        System.out.println("Sorted array: ");
        for (int i : arr) {
            System.out.print(i + " ");
        }
    }
}
"""

# Parse the Java code into an AST
tree = javalang.parse.parse(java_code)

def summarize_ast(node, depth=0):
    if hasattr(node, 'children'):
        children = node.children
        node_type = type(node).__name__
        summary = '  ' * depth + f'{node_type}\n'
        for child in children:
            if isinstance(child, list):
                for item in child:
                    summary += summarize_ast(item, depth + 1)
            elif child:
                summary += summarize_ast(child, depth + 1)
        return summary
    else:
        return ''

# Generate the summary
summary = summarize_ast(tree)
print(summary)
