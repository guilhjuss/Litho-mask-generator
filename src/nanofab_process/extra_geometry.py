"""Extra shapes expressed as physical polygons."""
from dataclasses import dataclass
import math
from .coordinate_text import text_rectangles, format_coordinate


@dataclass(frozen=True)
class GeometryPolygon:
    points: tuple[tuple[float, float], ...]
    layer: str
    structure_id: str


def resolved_text(s, config):
    if not s.label_auto:
        return s.text
    target = next((t for t in config.structures if t.id == s.label_target and t.type != "label"), None)
    if target is None:
        return s.id
    if target.type == "circle":
        return f"{target.id} D={format_coordinate(target.width_um)} UM"
    return f"{target.id} W={format_coordinate(target.width_um)} L={format_coordinate(target.length_um)} UM"


def special_geometry(s):
    out = []
    a = math.radians(s.angle_deg % 360)
    c, sn = math.cos(a), math.sin(a)
    cx, cy = s.center_um

    def polygon(points, layer=None):
        out.append(GeometryPolygon(tuple((cx+x*c-y*sn, cy+x*sn+y*c) for x,y in points), layer or s.layer, s.id))

    def rect(x0, y0, x1, y1, layer=None):
        polygon(((x0,y0),(x1,y0),(x1,y1),(x0,y1)), layer)

    w, l = s.width_um, s.length_um
    if s.type == "rectangle":
        rect(-l/2, -w/2, l/2, w/2)
    elif s.type == "circle":
        polygon(tuple((w/2*math.cos(i*2*math.pi/128),w/2*math.sin(i*2*math.pi/128)) for i in range(128)))
    elif s.type == "contact_pad":
        rect(-l/2,-w/2,l/2,w/2)
        rect(-l/2-s.lead_length_um,-s.lead_width_um/2,-l/2,s.lead_width_um/2)
    elif s.type == "label":
        rectangles = text_rectangles(s.text if not s.label_auto else s.id, w)
        if not rectangles:
            return []
        dx = (min(r[0] for r in rectangles)+max(r[2] for r in rectangles))/2
        dy = (min(r[1] for r in rectangles)+max(r[3] for r in rectangles))/2
        for x0,y0,x1,y1 in rectangles:
            rect(x0-dx,y0-dy,x1-dx,y1-dy)
    elif s.type == "alignment_mark":
        t = s.frame_width_um
        for scale,layer in ((1,s.layer),(.6,s.inner_layer or s.layer)):
            x,y = l*scale/2,w*scale/2
            rect(-x,-y,x,-y+t,layer)
            rect(-x,y-t,x,y,layer)
            rect(-x,-y+t,-x+t,y-t,layer)
            rect(x-t,-y+t,x,y-t,layer)
    else:
        raise ValueError(f"Unsupported type: {s.type}")
    return out
