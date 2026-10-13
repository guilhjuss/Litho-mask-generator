from dataclasses import replace
from pathlib import Path
import gdstk
import pytest
from nanofab_process.config import load_config, MaskConfig
from nanofab_process.geometry import generate_geometry
from nanofab_process.gds import export_gds


@pytest.mark.parametrize("kind,count", [("rectangle",1),("circle",1),("contact_pad",2),("alignment_mark",8)])
def test_new_geometries(kind,count,tmp_path):
    cfg=load_config(Path(__file__).with_name("example.json"))
    s=replace(cfg.structures[0],type=kind,width_um=100,length_um=200,angle_deg=45)
    cfg=replace(cfg,structures=(s,))
    polygons=generate_geometry(cfg)
    assert len(polygons)==count
    lib=gdstk.read_gds(export_gds(cfg,tmp_path/"shape.gds"))
    assert len(lib.top_level()[0].polygons)==count
    if kind=="circle":
        assert len(polygons[0].points)==128


def test_auto_label_updates_and_custom_label(tmp_path):
    cfg=load_config(Path(__file__).with_name("example.json"))
    target=cfg.structures[0]
    label=replace(target,type="label",id="text",width_um=20,label_target=target.id)
    a=generate_geometry(replace(cfg,structures=(target,label)))
    b=generate_geometry(replace(cfg,structures=(replace(target,length_um=125),label)))
    assert [p.points for p in a[1:]] != [p.points for p in b[1:]]
    custom=replace(label,label_auto=False,text="DEVICE 1")
    assert generate_geometry(replace(cfg,structures=(custom,)))
