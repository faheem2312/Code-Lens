import sys, os
sys.path.insert(0, os.getcwd())

from tree_sitter import Language, Parser
import tree_sitter_python as tspython

PY_LANGUAGE = Language(tspython.language())

parser = Parser()
parser.language = PY_LANGUAGE

with open("src/gemini_client.py", "rb") as f:
    source = f.read()

tree = parser.parse(source)
root = tree.root_node

print("Root type:", root.type)
print("Root children count:", len(root.children))
print("First 5 child types:")
for child in root.children[:5]:
    print(f"  {child.type}  —  {child.start_point}")

print()
print("Searching for function nodes...")
found = []
def walk(node, depth=0):
    if "function" in node.type or "method" in node.type:
        print(f"  {'  '*depth}{node.type}  at line {node.start_point[0]+1}")
        found.append(node.type)
    for child in node.children:
        walk(child, depth+1)

walk(root)
print(f"Total function-like nodes: {len(found)}")
