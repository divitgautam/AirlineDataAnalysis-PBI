"""Shared PBIR helpers (from RetailPulse-PBI): palette, field/literal helpers, Page builder, theme writer.
Usage: import pbir_kit as k; k.init(report_folder); build Page objects; k.finish(pages)."""
import json, shutil, sys
from pathlib import Path

REPORT = DEF = PAGES = None


def init(report_path):
    """Point the kit at a <Project>.Report folder."""
    global REPORT, DEF, PAGES
    REPORT = Path(report_path); DEF = REPORT / "definition"; PAGES = DEF / "pages"
VC_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.14.0/schema.json"
PAGE_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json"

# ---------- palette ----------
# InXiteOut brand (inxiteout.ai): deep navy, violet primary, lilac secondary; orange for warnings
NAVY, TEAL, AMBER, CORAL, SLATE, GREEN = "#030734", "#682EFF", "#CD83FF", "#F05100", "#62748E", "#009588"
FONT, FONT_BOLD = "'Instrument Sans', 'Segoe UI', sans-serif", "'Instrument Sans', 'Segoe UI Semibold', sans-serif"
INK, MUTED, BG, LINE, WHITE = "#020618", "#62748E", "#F1F5F9", "#E2E8F0", "#FFFFFF"
W, H, M, G = 1280, 720, 16, 12  # page size, margin, gutter
SUBTITLE, ROW_ALT, EXTRA_COLORS = "#C8C3F5", "#F6F3FF", ["#AC24FF", "#FCBB00"]
THEME_NAME, THEME_FILE = "InXiteOut", "InxiteOut.json"
HEADER_IMAGE, HEADER_TEXT_X = None, 0   # optional SVG banner behind the header text
IMAGES = {}                              # name -> SVG text, registered as report images


def set_theme(**kw):
    """Override palette/theme globals, e.g. set_theme(NAVY="#0A2540", THEME_NAME="Runway")."""
    g = globals()
    for k_, v_ in kw.items():
        if k_ not in g: raise KeyError(k_)
        g[k_] = v_


def image_ref(item):
    return {"expr": {"ResourcePackageItem": {"PackageName": "RegisteredResources", "PackageType": 1, "ItemName": item}}}


# ---------- literal helpers ----------
def L(v):
    if isinstance(v, bool):
        s = "true" if v else "false"
    elif isinstance(v, (int, float)):
        s = f"{v}D"
    else:
        s = "'" + str(v).replace("'", "''") + "'"
    return {"expr": {"Literal": {"Value": s}}}


def C(hex_):
    return {"solid": {"color": L(hex_)}}


def col(t, c):
    return {"Column": {"Expression": {"SourceRef": {"Entity": t}}, "Property": c}}


def mea(c, t="_Measures"):
    return {"Measure": {"Expression": {"SourceRef": {"Entity": t}}, "Property": c}}


def proj(field, display=None):
    kind = "Column" if "Column" in field else "Measure"
    t = field[kind]["Expression"]["SourceRef"]["Entity"]
    c = field[kind]["Property"]
    p = {"field": field, "queryRef": f"{t}.{c}", "nativeQueryRef": c}
    if kind == "Column":
        p["active"] = True
    if display:
        p["displayName"] = display
    return p


def qref(field):
    kind = "Column" if "Column" in field else "Measure"
    return f'{field[kind]["Expression"]["SourceRef"]["Entity"]}.{field[kind]["Property"]}'


def cat_filter(name, t, c, values, exclude=False):
    cond = {"In": {"Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "s"}}, "Property": c}}],
                   "Values": [[{"Literal": {"Value": v}}] for v in values]}}
    if exclude:
        cond = {"Not": {"Expression": cond}}
    return {"name": name, "field": col(t, c), "type": "Categorical", "howCreated": "User",
            "filter": {"Version": 2, "From": [{"Name": "s", "Entity": t, "Type": 0}], "Where": [{"Condition": cond}]}}


def series_color_by_value(t, c, value, hex_):
    return {"properties": {"fill": C(hex_)},
            "selector": {"data": [{"scopeId": {"Comparison": {"ComparisonKind": 0, "Left": col(t, c),
                                                               "Right": {"Literal": {"Value": f"'{value}'"}}}}}]}}


def series_color_by_measure(field, hex_):
    return {"properties": {"fill": C(hex_)}, "selector": {"metadata": qref(field)}}


# ---------- page builder ----------
class Page:
    def __init__(self, name, display):
        self.name, self.display, self.visuals, self.z = name, display, [], 0

    def add(self, name, vtype, x, y, w, h, roles=None, title=None, subtitle=None, objects=None,
            sort=None, filters=None, container=None):
        vis = {"visualType": vtype, "drillFilterOtherVisuals": True}
        if roles is not None:
            vis["query"] = {"queryState": {r: {"projections": [proj(*f) if isinstance(f, tuple) else proj(f) for f in fs]}
                                           for r, fs in roles.items()}}
            if sort:
                vis["query"]["sortDefinition"] = {"sort": [{"field": f, "direction": d} for f, d in sort],
                                                  "isDefaultSort": False}
        if objects:
            vis["objects"] = objects
        vco = {}
        if title is not None:
            vco["title"] = [{"properties": {"show": L(True), "text": L(title), "fontSize": L(11),
                                            "fontColor": C(INK), "bold": L(True)}}]
        if subtitle:
            vco["subTitle"] = [{"properties": {"show": L(True), "text": L(subtitle), "fontSize": L(9),
                                               "fontColor": C(MUTED)}}]
        vco.update(container or {})
        if vco:
            vis["visualContainerObjects"] = vco
        v = {"$schema": VC_SCHEMA, "name": name,
             "position": {"x": x, "y": y, "z": self.z * 1000, "height": h, "width": w, "tabOrder": self.z * 1000},
             "visual": vis}
        if filters:
            v["filterConfig"] = {"filters": filters}
        self.z += 1
        self.visuals.append(v)
        return v

    # --- composite helpers ---
    def header(self, title, subtitle, width=W - 2 * M):
        if HEADER_IMAGE:
            self.add("hdr_art", "image", 0, 0, W, 72,
                     objects={"general": [{"properties": {"imageUrl": image_ref(HEADER_IMAGE)}}],
                              "imageScaling": [{"properties": {"imageScalingType": L("Fill")}}]},
                     container={"background": [{"properties": {"show": L(False)}}], "border": [{"properties": {"show": L(False)}}],
                                "padding": [{"properties": {"top": L(0), "bottom": L(0), "left": L(0), "right": L(0)}}],
                                "title": [{"properties": {"show": L(False)}}], "visualHeader": [{"properties": {"show": L(False)}}]})
        self.add("hdr_band", "textbox", HEADER_TEXT_X, 0, W - HEADER_TEXT_X, 72, objects={"general": [{"properties": {"paragraphs": [
            {"textRuns": [{"value": title, "textStyle": {"fontWeight": "bold", "fontSize": "18pt", "color": WHITE,
                                                          "fontFamily": FONT_BOLD}}]},
            {"textRuns": [{"value": subtitle, "textStyle": {"fontSize": "10pt", "color": SUBTITLE}}]}]}}]},
            container={"background": [{"properties": {"show": not HEADER_IMAGE and L(True) or L(False), "color": C(NAVY), "transparency": L(0)}}],
                       "border": [{"properties": {"show": L(False)}}],
                       "padding": [{"properties": {"top": L(8), "left": L(16)}}]})

    def slicer(self, name, field, label, x, w):
        self.add(name, "slicer", x, 8, w, 56, roles={"Values": [field]},
                 objects={"data": [{"properties": {"mode": L("Dropdown")}}],
                          "header": [{"properties": {"show": L(True), "text": L(label), "fontColor": C(MUTED),
                                                     "textSize": L(9)}}],
                          "items": [{"properties": {"fontColor": C(INK), "textSize": L(10)}}]},
                 container={"background": [{"properties": {"show": L(True), "color": C(WHITE), "transparency": L(0)}}],
                            "border": [{"properties": {"show": L(True), "color": C(LINE), "radius": L(6)}}],
                            "padding": [{"properties": {"top": L(2), "bottom": L(2), "left": L(8), "right": L(8)}}]})

    def cards(self, items, y=84, h=88, filters=None, small=()):
        n = len(items)
        cw = (W - 2 * M - (n - 1) * G) / n
        for i, (name, field, label) in enumerate(items):
            self.add(name, "cardVisual", round(M + i * (cw + G)), y, round(cw), h,
                     roles={"Data": [(field, label)]}, filters=filters,
                     objects={"accentBar": [{"properties": {"show": L(True), "color": C(TEAL if i % 2 == 0 else AMBER)},
                                             "selector": {"id": "default"}}],
                              "label": [{"properties": {"fontSize": L(10)}, "selector": {"id": "default"}}],
                              "value": [{"properties": {"fontSize": L(14 if name in small else 24)}, "selector": {"id": "default"}}]})

    def textbox(self, name, x, y, w, h, title, lines, accent=None, size="10pt", gap=False):
        accent = accent or TEAL   # read at call time so set_theme() applies
        lines = [tuple(s.replace("Rs ", "₹") for s in ln) if isinstance(ln, tuple) else ln.replace("Rs ", "₹")
                 for ln in lines]
        paras = [{"textRuns": [{"value": title, "textStyle": {"fontWeight": "bold", "fontSize": "12pt", "color": INK,
                                                              "fontFamily": FONT_BOLD}}]}]
        for ln in lines:
            if isinstance(ln, tuple):  # (bold lead, rest)
                paras.append({"textRuns": [
                    {"value": ln[0], "textStyle": {"fontWeight": "bold", "fontSize": size, "color": accent}},
                    {"value": ln[1], "textStyle": {"fontSize": size, "color": INK}}]})
            else:
                paras.append({"textRuns": [{"value": ln, "textStyle": {"fontSize": size, "color": INK}}]})
            if gap:
                paras.append({"textRuns": [{"value": "", "textStyle": {"fontSize": "6pt"}}]})
        self.add(name, "textbox", x, y, w, h, objects={"general": [{"properties": {"paragraphs": paras}}]},
                 container={"padding": [{"properties": {"top": L(10), "left": L(14), "right": L(14)}}]})

    def write(self):
        pdir = PAGES / self.name
        if pdir.exists():
            shutil.rmtree(pdir)
        (pdir / "visuals").mkdir(parents=True)
        page = {"$schema": PAGE_SCHEMA, "name": self.name, "displayName": self.display, "displayOption": "FitToPage",
                "height": H, "width": W,
                "objects": {"background": [{"properties": {"color": C(BG), "transparency": L(0)}}],
                            "outspace": [{"properties": {"color": C(BG)}}]}}
        (pdir / "page.json").write_text(json.dumps(page, indent=2), encoding="utf-8")
        for v in self.visuals:
            d = pdir / "visuals" / v["name"]
            d.mkdir()
            (d / "visual.json").write_text(json.dumps(v, indent=2, ensure_ascii=False), encoding="utf-8")




def finish(pages):
    """Write all pages, page order and the InXiteOut theme."""
    for pg in pages:
        pg.write()

    pj = PAGES / "pages.json"
    meta = json.loads(pj.read_text(encoding="utf-8"))
    old = [n for n in meta["pageOrder"] if n not in {pg.name for pg in pages}]
    meta["pageOrder"] = [pg.name for pg in pages] + old
    meta["activePageName"] = pages[0].name
    pj.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    # ---------- theme ----------
    theme = {
        "name": THEME_NAME,
        "dataColors": [TEAL, AMBER, NAVY, CORAL, SLATE, GREEN] + EXTRA_COLORS,
        "foreground": INK, "foregroundNeutralSecondary": MUTED, "background": WHITE, "backgroundLight": BG,
        "tableAccent": TEAL, "good": GREEN, "neutral": AMBER, "bad": CORAL,
        "textClasses": {
            "title": {"fontFace": FONT_BOLD, "fontSize": 11, "color": INK},
            "label": {"fontFace": FONT, "fontSize": 10, "color": MUTED},
            "callout": {"fontFace": FONT_BOLD, "fontSize": 24, "color": NAVY},
            "header": {"fontFace": FONT_BOLD, "fontSize": 11, "color": INK},
        },
        "visualStyles": {
            "*": {"*": {
                "background": [{"show": True, "color": {"solid": {"color": WHITE}}, "transparency": 0}],
                "border": [{"show": True, "color": {"solid": {"color": LINE}}, "radius": 8, "width": 1}],
                "dropShadow": [{"show": False}],
                "title": [{"show": True, "fontColor": {"solid": {"color": INK}}, "fontSize": 11, "fontFamily": FONT_BOLD}],
                "padding": [{"top": 8, "bottom": 8, "left": 12, "right": 12}],
            }},
            "page": {"*": {"background": [{"color": {"solid": {"color": BG}}, "transparency": 0}]}},
            "pivotTable": {"*": {
                "columnHeaders": [{"backColor": {"solid": {"color": NAVY}}, "fontColor": {"solid": {"color": WHITE}}, "fontSize": 10}],
                "values": [{"fontSize": 10, "backColorSecondary": {"solid": {"color": ROW_ALT}}}],
                "subTotals": [{"rowSubtotals": True}],
                "total": [{"fontColor": {"solid": {"color": NAVY}}}],
            }},
        },
    }
    rr = REPORT / "StaticResources" / "RegisteredResources"
    rr.mkdir(parents=True, exist_ok=True)
    (rr / THEME_FILE).write_text(json.dumps(theme, indent=2), encoding="utf-8")
    for img, svg in IMAGES.items():
        (rr / img).write_text(svg, encoding="utf-8")

    rj = DEF / "report.json"
    rep = json.loads(rj.read_text(encoding="utf-8"))
    base = rep["themeCollection"]["baseTheme"]
    rep["themeCollection"]["customTheme"] = {"name": THEME_FILE, "reportVersionAtImport": base["reportVersionAtImport"],
                                             "type": "RegisteredResources"}
    pk = [r for r in rep["resourcePackages"] if r["name"] != "RegisteredResources"]
    pk.append({"name": "RegisteredResources", "type": "RegisteredResources",
               "items": [{"name": THEME_FILE, "path": THEME_FILE, "type": "CustomTheme"}]
                        + [{"name": img, "path": img, "type": "Image"} for img in IMAGES]})
    rep["resourcePackages"] = pk
    rj.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    print("pages:", [pg.name for pg in pages], "visuals:", sum(len(pg.visuals) for pg in pages))
