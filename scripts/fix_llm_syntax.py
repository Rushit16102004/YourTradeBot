import os

path = os.path.join("RAG", "llm_client.py")
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
skip = False
for i, line in enumerate(lines):
    if "elif d_list:" in line:
        new_lines.append(line)
        new_lines.append('                lines_buf = [f"Hey {uname},\\n\\nI am tracking **{len(d_list)} on-chart drawing(s)**:"]\n')
        new_lines.append('                for idx, d in enumerate(d_list[:4], 1):\n')
        new_lines.append("                    r = d.get('remark') or 'Unnamed'\n")
        new_lines.append("                    p1 = d.get('price1', '--')\n")
        new_lines.append("                    p2 = d.get('price2', '--')\n")
        new_lines.append('                    lines_buf.append(f"• **{idx}. {d.get(\'type\', \'line\').upper()} \'{r}\':** ₹{p1} → ₹{p2}")\n')
        new_lines.append('                lines_buf.append("• **Naming Tip:** Click on any drawing and assign a name (e.g. \'Major Support\') so I can give you high-precision alerts!")\n')
        new_lines.append('                synthesis = "\\n\\n".join(lines_buf)\n')
        skip = True
    elif skip and "else:" in line and "synthesis = (" in lines[i+1]:
        skip = False
        new_lines.append(line)
    elif not skip:
        new_lines.append(line)

with open(path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("Fixed syntax in RAG/llm_client.py successfully.")
