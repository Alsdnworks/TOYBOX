import typing
import argparse
from dataclasses import dataclass
import pyproj
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString, MultiLineString
from shapely.ops import unary_union, linemerge, snap


@dataclass
class Param:
    lines_path: str
    points_path: str
    out_lines_path: str
    out_errors_path: str
    tol: float
    point_id_col: typing.Optional[str] = None
    val_chk_col: typing.Tuple[str, ...] = tuple()


class errlog:
    def __init__(self):
        self.rows = []
        self.pset = set()

    def enroll(self, pid, count, line_ids, issue, geometry):
        already_enrolled = pid in self.pset
        self.pset.add(pid)
        if not already_enrolled:
            self.rows.append(
                {
                    "point_id": pid,
                    "count": count,
                    "line_ids": line_ids,
                    "issue": issue,
                    "geometry": geometry,
                }
            )


errlog = errlog()


def validate_inputs(
    lines_gdf: gpd.GeoDataFrame,
    points_gdf: gpd.GeoDataFrame,
    tol: float,
    use_point_id_col: typing.Optional[str],
    val_chk_col: typing.Tuple[str, ...],
):
    # input validation function
    def chk_crs(crs: typing.Union[str, dict, pyproj.CRS]) -> bool:
        try:
            crs = pyproj.CRS.from_user_input(crs)
        except pyproj.exceptions.CRSError:
            return False
        if not crs.is_projected:
            return False
        try:
            unit = crs.coordinate_system.axis_list[0].unit_name.lower()
            return unit in ("metre", "meter")
        except (AttributeError, IndexError):
            return False

    if lines_gdf.empty:
        raise ValueError("lines_gdf is empty.")
    if points_gdf.empty:
        raise ValueError("points_gdf is empty.")
    if not all(lines_gdf.geometry.type.isin(["LineString", "MultiLineString"])):
        raise ValueError("lines_gdf must contain only LineString or MultiLineString geometries.")
    if not all(points_gdf.geometry.type == "Point"):
        raise ValueError("points_gdf must contain only Point geometries.")
    if tol <= 0:
        raise ValueError("tol must be a positive number.")
    if use_point_id_col and use_point_id_col not in points_gdf.columns:
        raise ValueError(f"use_point_id_col '{use_point_id_col}' not found in points_gdf columns.")
    if val_chk_col:
        for c in val_chk_col:
            if c not in lines_gdf.columns:
                raise ValueError(f"val_chk_col '{c}' not found in lines_gdf columns.")
    if lines_gdf.crs is None or points_gdf.crs is None:
        raise ValueError("layers must have a defined CRS.")
    if (chk_crs(lines_gdf.crs) and chk_crs(points_gdf.crs)) is False:
        raise ValueError("layers must have a projected CRS with meter unit.")


def iter_endpoints(geom: typing.Union[LineString, MultiLineString]):
    # yield start and end points of a LineString or MultiLineString
    if isinstance(geom, LineString):
        cs = list(geom.coords)
        yield Point(cs[0])
        yield Point(cs[-1])
    elif isinstance(geom, MultiLineString):
        for part in geom.geoms:
            cs = list(part.coords)
            yield Point(cs[0])
            yield Point(cs[-1])


def merge_two_lines(l1: LineString, l2: LineString, snap_tol: float) -> LineString:
    # to avoid TopologyException, snap each line to itself first
    u = unary_union([l1, l2])
    if snap_tol and snap_tol > 0:
        u = snap(u, u, snap_tol)
    m = linemerge(u)
    if m.geom_type == "MultiLineString":
        m = linemerge(unary_union(m))
    # raise error if not LineString NOTE: 이런경우는 직접 데이터를 봐야하므로 무리하게 처리하지 않음
    if m.geom_type != "LineString":
        raise ValueError("LineString Conversion Failed in merge_two_lines() check geometry validity.")
    return m


def merge_at_points(
    lines_gdf: gpd.GeoDataFrame,
    points_gdf: gpd.GeoDataFrame,
    tol: float,
    use_point_id_col: str = None,
    val_chk_col: typing.Tuple[str, ...] = None,
) -> typing.Tuple[gpd.GeoDataFrame, pd.DataFrame]:
    global errlog
    # variable setup
    iteration = 0
    iterlim = 100
    total_merged = 0
    line_raw = lines_gdf.copy()
    lines = None
    ###############
    while iteration < iterlim:
        lines = (
            line_raw.copy().reset_index(drop=True) if lines is None else lines.copy().reset_index(drop=True)
        )
        lines["__row_id__"] = lines.index
        # collect endpoints from line GeoDataFrame to intersect with points
        end_rows = []
        for i, geom in enumerate(lines.geometry):
            for k, pt in enumerate(iter_endpoints(geom)):
                end_rows.append({"__row_id__": i, "which": f"end{k%2}", "geometry": pt})
        ends = gpd.GeoDataFrame(end_rows, geometry="geometry", crs=lines.crs)
        sidx = ends.sindex
        pts = points_gdf.copy()
        if use_point_id_col and use_point_id_col in pts.columns:
            pts["_pt_id_"] = pts[use_point_id_col]
        else:
            pts["_pt_id_"] = pts.index

        # define iteration variables
        used_line = set()
        merged_rows = []

        untouched_ids = set(lines["__row_id__"].tolist())
        merge_count = 0
        ###############

        # main loop
        for _, prow in pts.iterrows():
            # find candidate line ends using spatial index intersection
            pt = prow.geometry
            pid = prow["_pt_id_"]
            if pid in errlog.pset:
                continue
            buf = pt.buffer(tol)
            cand_idx = list(sidx.intersection(buf.bounds))
            if not cand_idx:
                continue
            cand = ends.iloc[cand_idx]
            hits = cand[cand.intersects(buf)]
            line_ids = set(hits["__row_id__"].tolist())

            # check only 2 lines joined
            if len(line_ids) != 2:
                errlog.enroll(
                    pid,
                    len(line_ids),
                    sorted(line_ids) if len(line_ids) > 0 else None,
                    "Not exactly 2 lines to merge.",
                    pt,
                )
                continue

            # check used lines
            a_id, b_id = sorted(line_ids)
            if a_id in used_line or b_id in used_line:
                continue

            try:
                # join, write new row
                l1 = lines.loc[lines["__row_id__"] == a_id, "geometry"].iloc[0]
                l2 = lines.loc[lines["__row_id__"] == b_id, "geometry"].iloc[0]
                if val_chk_col:
                    v1 = lines.loc[lines["__row_id__"] == a_id, val_chk_col].iloc[0]
                    v2 = lines.loc[lines["__row_id__"] == b_id, val_chk_col].iloc[0]
                    if not all(v1 == v2):
                        errlog.enroll(
                            pid,
                            len(line_ids),
                            sorted(line_ids) if len(line_ids) > 0 else None,
                            f"Value check failed at columns {val_chk_col}.",
                            pt,
                        )
                        continue
                merged_geom = merge_two_lines(l1, l2, snap_tol=tol)
                # TODO: add arguments to control merged attributes like.. sum, average, first, last etc..
                rep_row = lines.loc[lines["__row_id__"] == a_id].copy().iloc[[0]]
                rep_row.loc[:, "geometry"] = [merged_geom]
                rep_row.loc[:, "merged_from"] = [f"{a_id},{b_id}"]
                rep_row.loc[:, "merge_point_id"] = [pid]
                rep_row.loc[:, "merged_count"] = (
                    rep_row.loc[:, "merged_count"] + 1 if "merged_count" in rep_row.columns else 1
                )
                merged_rows.append(rep_row)
                merge_count += 1
                used_line.update({a_id, b_id})
                untouched_ids.discard(a_id)
                untouched_ids.discard(b_id)

            except Exception as e:
                errlog.enroll(
                    pid,
                    len(line_ids),
                    sorted(line_ids) if len(line_ids) > 0 else None,
                    f"Error in merging: {e}",
                    pt,
                )
                continue

        # reconstruct lines and unjoined lines(remain)
        remain = lines[lines["__row_id__"].isin(untouched_ids)].copy()
        if merged_rows:
            lines = gpd.GeoDataFrame(
                pd.concat([remain] + merged_rows, ignore_index=True), geometry="geometry", crs=lines.crs
            )
            # drop duplicates
            lines["__wkb__"] = lines.geometry.apply(lambda g: g.wkb if g else None)
            lines = lines.drop_duplicates(subset="__wkb__").drop(columns="__wkb__")

            # pipeline control
            total_merged += merge_count
            print(f"[INFO] iter {iteration + 1}: merged {merge_count} lines")
            if merge_count == 0:
                break
            lines = lines.copy()
        else:
            print(
                f"[INFO] No more line merges possible. - Total {total_merged} lines merged, {len(errlog.rows)} errors."
            )
            lines = remain
            break

        iteration += 1
    print(f"[INFO] max iterations reached. Check data if necessary.") if iteration >= iterlim else None
    errors = pd.DataFrame(errlog.rows, columns=["point_id", "count", "line_ids", "issue", "geometry"])
    return lines, errors


def run(Param: Param):
    lines = gpd.read_file(Param.lines_path)
    points = gpd.read_file(Param.points_path)

    validate_inputs(lines, points, Param.tol, Param.point_id_col, Param.val_chk_col)
    out_gdf, err_df = merge_at_points(
        lines, points, Param.tol, use_point_id_col=Param.point_id_col, val_chk_col=Param.val_chk_col
    )
    out_gdf.to_file(Param.out_lines_path, driver="GPKG")
    if len(err_df) > 0:
        gpd.GeoDataFrame(err_df, geometry="geometry", crs=points.crs).to_file(
            Param.out_errors_path, driver="GPKG"
        )
    print(f"[Done] Result saved: {Param.out_lines_path}", end=". ")
    if len(err_df) > 0:
        print(f"ErrorPoint  {Param.out_errors_path}")


def _parse_args():
    p = argparse.ArgumentParser(
        description="Merge LineString features at Point locations within a specified tolerance.",
        epilog=(
            "Examples:\n"
            "  # Default usage\n"
            "  merge_at_points --lines C:\\edge.shp"
            "                  --points C:\\node.gpkg \\\n"
            "                  --out C:\\out.gpkg "
            "                  --out-errors C:\\errors.gpkg \\\n"
            "                  --tol 0.2\n\n"
            "  # Optional arguments usage, using None or null string for point-id-col to use index as ID\n"
            "  merge_at_points ..."
            "                  --point-id-col NODE_ID \\\n"
            "                  --val-chk-col ROAD_TYPE LANE_NUM\n"
            "  or\n"
            "  merge_at_points ..."
            "                  --point-id-col none \\\n"
            "                  --val-chk-col AAA BBB CCC\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--lines", required=True, help="Line layer to be merged (GPKG or SHP)")
    p.add_argument("--points", required=True, help="Point layer to merge at (GPKG or SHP)")
    p.add_argument("--out", required=True, help="Merged output as LineString (GPKG or SHP)")
    p.add_argument("--out-errors", required=True, help="Error log output as Point (GPKG or SHP)")
    p.add_argument(
        "--tol", type=float, required=True, help="Tolerance in meter (projected CRS with meter unit only)."
    )
    p.add_argument(
        "--point-id-col", default=None, help="Optional Point ID column in points layer, if None, use index."
    )
    p.add_argument(
        "--val-chk-col",
        nargs="+",
        default=(),
        help="Optional column list to check values before merging, if any column value mismatched, skip merging and log as error.",
    )
    return p.parse_args()


def main():
    args = _parse_args()

    def _norm_none(v):
        if v is None:
            return None
        v_str = str(v).strip().lower()
        return None if v_str in ("", "none", "null") else v

    s = Param(
        lines_path=args.lines,
        points_path=args.points,
        out_lines_path=args.out,
        out_errors_path=args.out_errors,
        tol=args.tol,
        point_id_col=_norm_none(args.point_id_col),
        val_chk_col=tuple(args.val_chk_col) if args.val_chk_col else tuple(),
    )
    run(s)


if __name__ == "__main__":
    # run main function

    # General GIS Format like GPKG, SHP etc or replace gpd.to~ to save in other format
    LINES_PATH = r"C:ㅇㅇㅇ.shp"  # EDGE to be merged
    POINTS_PATH = r"C:ㅇㅇㅇ.gpkg"  # NODE to merge at

    OUT_LINES_PATH = r"C:ㅇㅇㅇ.gpkg"  # merged output as LineString
    OUT_ERRORS = r"C:ㅇㅇㅇ.gpkg"  # error log output as Point

    POINT_ID_COL = None  # NODE ID column in POINTS_PATH, if None, use index

    TOL = 0.2  # tolerance in meter (USE PROJECTED CRS with meter unit only)

    # optional column list to check values before merging, if any column value mismatched, skip merging and log as error
    VAL_CHK_COL = [
        "AAA",
        "BBB",
        "CCC",
    ]

    run(
        Param(
            lines_path=LINES_PATH,
            points_path=POINTS_PATH,
            out_lines_path=OUT_LINES_PATH,
            out_errors_path=OUT_ERRORS,
            tol=TOL,
            point_id_col=POINT_ID_COL,
            val_chk_col=tuple(VAL_CHK_COL),
        )
    )
