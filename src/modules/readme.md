project_folder should have python files as follows:
- __init__.py
- config.py
- state.py
- prompt.py
- graph.py
- node.py(if necessary)

If a node is intended for reuse in the future, please define it in common/nodes.py.
If the node is specific to a particular use case, create a node.py file within the relevant project folder.

The project folder name should be simple and concise.


recommend to follow below mentioned steps.
1. create folder.
2. create python codes
   1. __init__.py
   2. config.py
   3. state.py
   4. graph.py
   5. prompt.py
3. added the module to module's __init__.py
4. implementation