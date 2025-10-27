from dataclasses import dataclass
from typing import Optional, Tuple
import geopandas as gpd
from shapely.geometry import CAP_STYLE, JOIN_STYLE
from shapely.geometry.base import BaseGeometry

# find overlapping line strings in a GeoDataFrame based on buffer area overlap


@dataclass(frozen=True)
class Threshold:
    value: float
    kind: str

    @classmethod
    def parse(cls, s: str) -> "Threshold":
        s = s.strip().lower()
        if not s:
            raise ValueError("min_threshold cannot be empty")
        if s.endswith("p"):
            return cls(float(s[:-1]), "p")
        if s.endswith("m"):
            return cls(float(s[:-1]), "m")
        raise ValueError("min_threshold must end with 'm' or 'p'")


class DLV:
    def __init__(
        self,
        gdf: gpd.GeoDataFrame,
        buffer_size: float,
        min_threshold: str,
        as_idx: Optional[str] = None,
    ):
        if "geometry" not in gdf:
            raise ValueError("Input GeoDataFrame must have a 'geometry' column.")
        self.gdf = gdf.reset_index(drop=True).copy()
        self.buffer_size = float(buffer_size)
        self.threshold_cfg = Threshold.parse(min_threshold)

        if as_idx is not None:
            if as_idx not in self.gdf.columns:
                raise ValueError(f"as_idx='{as_idx}' is not a column in the GeoDataFrame.")
            if not self.gdf[as_idx].is_unique or self.gdf[as_idx].isna().any():
                raise ValueError("as_idx must be unique and non-null.")
            self.gdf.set_index(as_idx, inplace=True)

        self.gdf["geom_line"] = self.gdf.geometry
        self.buf = self.gdf[["geom_line"]].copy().set_geometry("geom_line")
        self.buf["buf_geom"] = self.buf.buffer(
            self.buffer_size,
            cap_style=CAP_STYLE.flat,
            join_style=JOIN_STYLE.round,
        )
        self.buf = self.buf.set_geometry("buf_geom")
        self.buf["buf_area"] = self.buf.geometry.area

        self.result: Optional[gpd.GeoDataFrame] = None
        self._pairs: Optional[gpd.GeoDataFrame] = None

        if self.gdf.crs is not None and self.gdf.crs.is_geographic:
            raise ValueError("Input GeoDataFrame must have a projected CRS (not geographic).")

    def run(self) -> gpd.GeoDataFrame:
        pairs = self.collect_pairs()
        rows = []
        buf_geom = self.buf.geometry
        buf_area = self.buf["buf_area"]
        lines = self.gdf["geom_line"]

        for L, R in pairs.itertuples(index=False):
            inter_poly = buf_geom.loc[L].intersection(buf_geom.loc[R])
            if inter_poly.is_empty:
                continue
            area_L = float(buf_area.loc[L])
            area_R = float(buf_area.loc[R])
            inter_area = inter_poly.area
            inter_line = lines.loc[L].intersection(inter_poly)
            inter_length = getattr(inter_line, "length", 0.0) or 0.0
            pct_L = (inter_area / area_L * 100.0) if area_L > 0 else 0.0
            pct_R = (inter_area / area_R * 100.0) if area_R > 0 else 0.0

            if self._passes_threshold(max(pct_L, pct_R), inter_length):
                rows.append(
                    {
                        "L": L,
                        "R": R,
                        "ENCLOSED_2": "L" if pct_L >= pct_R else "R",
                        "OVLP_PCT_L": pct_L,
                        "OVLP_PCT_R": pct_R,
                        "OVLP_LENGT": inter_length,
                        "BUFER_SIZE": self.buffer_size,
                        "geometry": inter_line if inter_length > 0 else inter_poly.boundary,
                    }
                )

        result = gpd.GeoDataFrame(rows, geometry="geometry", crs=self.gdf.crs).reset_index(drop=True)
        self.result = result
        return result

    def collect_pairs(self) -> gpd.GeoDataFrame:
        left = self._sideframe("L")
        right = self._sideframe("R")
        joined = gpd.sjoin(left, right, predicate="intersects", how="inner")
        pairs = joined[["L", "R"]].copy()
        pairs = pairs[pairs["L"] != pairs["R"]]
        pairs["pair_key"] = pairs.apply(
            lambda s: tuple(sorted((s["L"], s["R"]), key=lambda x: str(x))), axis=1
        )
        pairs = pairs.drop_duplicates("pair_key")[["L", "R"]].reset_index(drop=True)
        self._pairs = pairs
        return pairs

    def _sideframe(self, side: str) -> gpd.GeoDataFrame:
        if side not in {"L", "R"}:
            raise ValueError("side must be 'L' or 'R'.")
        oneside = f"geom_{side}"
        gdf = self.buf.copy()
        out = (
            gdf.reset_index(names=side)
            .rename(columns={"buf_geom": oneside})[[side, "buf_area", oneside]]
            .set_geometry(oneside)
        )
        out.set_crs(self.buf.crs, allow_override=True, inplace=True)
        return out

    def _passes_threshold(self, max_pct: float, inter_len: float) -> bool:
        t = self.threshold_cfg
        if t.kind == "p":
            return max_pct > t.value
        if t.kind == "m":
            return inter_len > t.value
        raise RuntimeError("Unknown threshold kind.")

    @staticmethod
    def _as_tuple(geom: BaseGeometry) -> Tuple[float, float]:
        return geom.area, geom.length


if __name__ == "__main__":
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
    min_threshold = "1m"

    # Run overlap checker
    res = DLV(gdf, buffer_size=buffer_size, min_threshold=min_threshold, as_idx="LINK_ID").run()

    # Save result to file
    res.to_file(
        f"{basename(data_path).split('.')[0]}-DUPCHK-{str(buffer_size).replace('.','_')}m_buf-{min_threshold}_lim.gpkg"
    )
    print("Done.")
