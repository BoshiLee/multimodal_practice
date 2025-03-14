import json
import re
from pyproj import Transformer

# 建立 Transformer 物件 (TWD97 to WGS84)
transformer = Transformer.from_crs(
    "+proj=tmerc +lat_0=0 +lon_0=121 +k=0.9999 +x_0=250000 +y_0=0 +ellps=GRS80 +units=m +no_defs",
    "EPSG:4326",
    always_xy=True
)


def convert_twd97_to_wgs84(x, y):
    """
    將 TWD97 (台灣橫麥卡托) 轉換為 WGS84 (經緯度)

    :param x: TWD97 X 座標
    :param y: TWD97 Y 座標
    :return: 包含 lat (緯度) 和 lng (經度) 的字典
    """
    try:
        lon, lat = transformer.transform(x, y)
        return {"lat": lat, "lng": lon}
    except Exception as e:
        print(f"座標轉換錯誤: {e}")
        return None


def parse_inp(file_path):
    """
    解析 EPANET INP 檔案，提取 JUNCTIONS、PIPES、VERTICES、COORDINATES

    :param file_path: INP 檔案路徑
    :return: 字典格式的解析結果
    """
    nodes = {}
    pipes = {}
    vertices = {}

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    section = None
    for line in lines:
        line = line.strip()
        if not line or line.startswith(";"):  # 跳過空行和註解
            continue

        if ";" in line:
            line = line.split(";")[0].strip()  # 去掉行內註解

        # 檢測新區段
        if line.startswith("[") and line.endswith("]"):
            section = line.strip("[]")
            continue

        parts = re.split(r"\s+", line)

        # 解析節點座標 [COORDINATES]
        if section == "COORDINATES" and len(parts) >= 3:
            node_id, x, y = parts[0], float(parts[1]), float(parts[2])
            converted = convert_twd97_to_wgs84(x, y)
            if converted:
                nodes[node_id] = {"latlng": converted, "elevation": 0, "base_demand": 0, "pattern": None}

        # 解析節點 [JUNCTIONS]
        elif section == "JUNCTIONS" and len(parts) >= 3:
            node_id, elevation, base_demand = parts[0], float(parts[1]), float(parts[2])
            pattern = parts[3] if len(parts) > 3 else None
            if node_id not in nodes:
                nodes[node_id] = {"latlng": None, "elevation": 0, "base_demand": 0, "pattern": None}
            nodes[node_id].update({"elevation": elevation, "base_demand": base_demand, "pattern": pattern})

        # 解析管線 [PIPES]
        elif section == "PIPES" and len(parts) >= 6:
            pipe_id, start_node, end_node = parts[0], parts[1], parts[2]
            length, diameter, roughness = float(parts[3]), float(parts[4]), float(parts[5])
            pipes[pipe_id] = {"start": start_node, "end": end_node, "length": length, "diameter": diameter,
                              "roughness": roughness, "path": []}

        # 解析管線彎曲點 [VERTICES]
        elif section == "VERTICES" and len(parts) >= 3:
            pipe_id, x, y = parts[0], float(parts[1]), float(parts[2])
            converted = convert_twd97_to_wgs84(x, y)
            if converted:
                if pipe_id not in vertices:
                    vertices[pipe_id] = []
                vertices[pipe_id].append(converted)

    # 將彎曲點資訊加入管線
    for pipe_id, path_points in vertices.items():
        if pipe_id in pipes:
            pipes[pipe_id]["path"] = path_points

    return {"nodes": nodes, "pipes": pipes}


def save_to_json(data, output_file):
    """
    將解析結果儲存為 JSON 檔案

    :param data: 解析後的資料 (dict)
    :param output_file: JSON 檔案名稱
    """
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"解析完成，結果已儲存至 {output_file}")


if __name__ == "__main__":
    file_path = "0401-13-01-12.inp"  # 修改為你的 INP 檔案路徑
    parsed_data = parse_inp(file_path)

    # 儲存為 JSON
    output_file = "parsed_network.json"
    save_to_json(parsed_data, output_file)
