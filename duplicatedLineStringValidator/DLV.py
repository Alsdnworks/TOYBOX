# find overlapping line strings in a GeoDataFrame based on buffer area overlap

import geopandas as gpd


class DLV:
    def __init__(self, gdf, buffer_size, min_threshold):
        self.gdf = gdf.reset_index(drop=True).copy()
        self.buffer_size = float(buffer_size)
        self.min_threshold = str(min_threshold).strip()
        self.gdf["geom_line"] = self.gdf.geometry
        self.buf = self.gdf[["geom_line"]].copy().set_geometry("geom_line")
        self.buf["buf_geom"] = self.buf.buffer(self.buffer_size, cap_style="flat", join_style="round")
        self.buf = self.buf.set_geometry("buf_geom")
        self.buf["buf_area"] = self.buf.geometry.area
        self.result = None

    def run(self):
        pairs = self.collect_pair()
        rows = []
        for L, R in pairs.itertuples(index=False):
            i, j = int(L), int(R)
            inter_poly = self.buf.geometry.iloc[i].intersection(self.buf.geometry.iloc[j])
            area_L = float(self.buf["buf_area"].iloc[i])
            area_R = float(self.buf["buf_area"].iloc[j])
            inter_area = inter_poly.area
            inter_line = self.gdf.geom_line.iloc[i].intersection(inter_poly)
            inter_length = inter_line.length
            pct_L = inter_area / area_L * 100.0
            pct_R = inter_area / area_R * 100.0
            if self.threshold(max(pct_L, pct_R), inter_length):
                rows.append(
                    {
                        "L": i,
                        "R": j,
                        "ENCLOSED_2": "L" if pct_L >= pct_R else "R",
                        "OVLP_PCT_L": pct_L,
                        "OVLP_PCT_R": pct_R,
                        "OVLP_LENGT": inter_length,
                        "BUFER_SIZE": self.buffer_size,
                        "geometry": inter_line if inter_length > 0 else inter_poly.boundary,
                    }
                )
        return gpd.GeoDataFrame(rows, geometry="geometry", crs=self.gdf.crs).reset_index(drop=True)

    def collect_pair(self):
        left = (
            self.buf.reset_index(names="L")
            .rename(columns={"buf_geom": "geom_L"})[["L", "buf_area", "geom_L"]]
            .set_geometry("geom_L")
        )
        right = (
            self.buf.reset_index(names="R")
            .rename(columns={"buf_geom": "geom_R"})[["R", "buf_area", "geom_R"]]
            .set_geometry("geom_R")
        )
        pairs = gpd.sjoin(left, right, predicate="intersects", how="inner")[["L", "R"]]
        pairs = pairs[pairs["L"] != pairs["R"]].copy()
        pairs["pair_key"] = pairs.apply(lambda s: tuple(sorted((int(s.L), int(s.R)))), axis=1)
        self._pairs = pairs.drop_duplicates("pair_key")[["L", "R"]].reset_index(drop=True)
        return self._pairs

    def threshold(self, max_pct, inter_len):
        t = self.min_threshold
        if t.endswith("p"):
            return max_pct > float(t[:-1])  # percent
        if t.endswith("m"):
            return inter_len > float(t[:-1])  # meters
        raise ValueError("min_threshold must end with 'm' or 'p'")


if __name__ == "main":

    ## SAMPLE USAGE :##
    from os.path import basename

    # Load data
    data_path = r"MOCT_LINK.shp"
    gdf = gpd.read_file(data_path)

    # Set buffer to intersect line strings
    buffer_size = 0.1  # m

    # Set minimum threshold to filter silmilar line strings
    # percentage of buffer intersection like "50p"
    # length of intersected line like "5m"
    min_threshold = "10m"

    # Run overlap checker
    res = DLV(gdf, buffer_size=buffer_size, min_threshold=min_threshold).run()

    # Save result to file
    res.to_file(
        f"{basename(data_path).split('.')[0]}-DUPCHK-{str(buffer_size).replace('.','_')}m_buf-{min_threshold}_lim.gpkg"
    )
