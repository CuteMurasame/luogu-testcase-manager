## Luogu Testcase Manager GUI

Features:
- Choose a directory and scan for matching pairs of *.in and *.ans files (matching by basename).
- List each pair as an item with properties: Name (*.in), timeLimit (ms), memoryLimit (kb), score, subtaskId
- Defaults: timeLimit=2000, memoryLimit=1048576, score=0, subtaskId=0
- Reorder items (move up / move down)
- Multi-select items and bulk-edit timeLimit/memoryLimit/score/subtaskId (leave blank to skip changing a field)
- Double-click an item to edit its fields individually
- Export to a YAML file with the format shown by the user

No external dependencies (uses Tkinter which is included with Python).

Run: 
```
python3 tcman.py
```
