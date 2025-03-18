import zipfile
import os
import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd

# 加入 tkinter 的檔案對話框
import tkinter as tk
from tkinter import filedialog

def extract_shp(zip_path, extract_path):
    """解壓縮 SHP 壓縮檔"""
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_path)

def load_shapefiles(directory):
    """
    讀取指定目錄中的 SHP 檔案，並以 dict 形式回傳：
    {
      'pipe.shp': GeoDataFrame,
      'valve.shp': GeoDataFrame,
      ...
    }
    """
    shp_files = [f for f in os.listdir(directory) if f.endswith(".shp")]
    shapefiles = {}
    for shp_file in shp_files:
        file_path = os.path.join(directory, shp_file)
        shapefiles[shp_file] = gpd.read_file(file_path)
    return shapefiles

def plot_shapefiles(shapefiles, output_path="map.png"):
    """
    讀取多個 GeoDataFrame，轉成 WGS84 後繪圖，輸出 PNG。
    """
    # 取得各層 GeoDataFrame
    gdf_pipe = shapefiles.get("pipe.shp", gpd.GeoDataFrame())
    gdf_valve = shapefiles.get("valve.shp", gpd.GeoDataFrame())
    gdf_hydrant = shapefiles.get("hydrant.shp", gpd.GeoDataFrame())
    gdf_manhole = shapefiles.get("manhole.shp", gpd.GeoDataFrame())

    # 設定預設 CRS= EPSG:3826 (TWD97 TM2)，再轉 WGS84
    def to_wgs84(gdf):
        if gdf.crs is None:
            gdf.set_crs("EPSG:3826", inplace=True)
        return gdf.to_crs("EPSG:4326")

    if not gdf_pipe.empty:    gdf_pipe = to_wgs84(gdf_pipe)
    if not gdf_valve.empty:   gdf_valve = to_wgs84(gdf_valve)
    if not gdf_hydrant.empty: gdf_hydrant = to_wgs84(gdf_hydrant)
    if not gdf_manhole.empty: gdf_manhole = to_wgs84(gdf_manhole)

    # 繪圖
    fig, ax = plt.subplots(figsize=(10, 10))
    if not gdf_pipe.empty:
        gdf_pipe.plot(ax=ax, color="blue", linewidth=0.5, label="Pipes")
    if not gdf_valve.empty:
        gdf_valve.plot(ax=ax, color="red", markersize=10, label="Valves", marker="o")
    if not gdf_hydrant.empty:
        gdf_hydrant.plot(ax=ax, color="green", markersize=10, label="Hydrants", marker="s")
    if not gdf_manhole.empty:
        gdf_manhole.plot(ax=ax, color="orange", markersize=10, label="Manholes", marker="^")

    plt.legend()
    plt.title("Water Pipe Network (WGS84) with Valves, Hydrants, and Manholes")
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.savefig(output_path)
    plt.close()
    print(f"[INFO] map saved to {output_path}")

def save_individual_geojson(shapefiles, output_dir="geojson_output"):
    """
    各 shp 存成各自的 .geojson
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for shp_name, gdf in shapefiles.items():
        if gdf.empty:
            continue
        if gdf.crs is None:
            gdf.set_crs("EPSG:3826", inplace=True)
        gdf_4326 = gdf.to_crs("EPSG:4326")

        out_name = os.path.splitext(shp_name)[0] + ".geojson"
        out_path = os.path.join(output_dir, out_name)
        gdf_4326.to_file(out_path, driver="GeoJSON")
        print(f"[INFO] saved {out_path}")

def merge_all_to_single_geojson(shapefiles, out_file="all_in_one.geojson"):
    """
    將所有 shp（可能有不同屬性、幾何型態）合併到一個 GeoDataFrame 中，
    然後一次輸出成單一 GeoJSON。
    """
    frames = []
    for shp_name, gdf in shapefiles.items():
        if shp_name not in ["pipe.shp", "valve.shp", "hydrant.shp", "manhole.shp"]:
            continue
        if gdf.empty:
            continue
        # 若尚未有 crs，就先設 EPSG:3826
        if gdf.crs is None:
            gdf.set_crs("EPSG:3826", inplace=True)
        # 轉為 WGS84
        gdf_4326 = gdf.to_crs("EPSG:4326")
        # 給個欄位紀錄這筆來源
        gdf_4326["src_layer"] = shp_name
        frames.append(gdf_4326)

    if len(frames) == 0:
        print("[WARN] no valid shapefiles to merge.")
        return

    # 利用 pandas 的 concat 合併
    combined_gdf = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True, sort=False),
                                    crs="EPSG:4326")
    # 輸出
    combined_gdf.to_file(out_file, driver="GeoJSON")
    print(f"[INFO] Merged {len(frames)} shapefiles into {out_file}")

if __name__ == "__main__":
    # 使用 tkinter 讓使用者選擇 zip 檔
    root = tk.Tk()
    root.withdraw()  # 隱藏主視窗
    zip_path = filedialog.askopenfilename(
        title="選擇 SHP 壓縮檔",
        filetypes=[("ZIP files", "*.zip"), ("All Files", "*.*")]
    )
    if not zip_path:
        print("[ERROR] 使用者未選擇檔案，程式結束。")
        exit()

    extract_path = "shp_files"
    shp_folder = os.path.join(extract_path, "SHP")

    # 1. 解壓縮
    extract_shp(zip_path, extract_path)

    # 2. 讀取 SHP
    shapefiles = load_shapefiles(shp_folder)

    # 3. 繪製並輸出
    plot_shapefiles(shapefiles, "map.png")

    # 4. 各別輸出 GeoJSON（可選）
    save_individual_geojson(shapefiles, "geojson_output")

    # 5. 整合為單一檔
    # merge_all_to_single_geojson(shapefiles, "all_in_one.geojson")
