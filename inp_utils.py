def convert_inp_to_txt(inp_file_path):
    txt_file_path = inp_file_path.replace(".inp", ".txt")

    with open(inp_file_path, "r", encoding="utf-8") as inp_file:
        content = inp_file.read()

    with open(txt_file_path, "w", encoding="utf-8") as txt_file:
        txt_file.write(content)

    print(f"轉換完成: {txt_file_path}")
    return txt_file_path