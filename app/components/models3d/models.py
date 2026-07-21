"""3D model API schemas."""

from pydantic import BaseModel


class HotspotOut(BaseModel):
    hotspot_key: str
    component: str
    position: list
    source_ref: dict | None = None

    class Config:
        from_attributes = True


class Model3DOut(BaseModel):
    id: int
    model_key: str
    name: str
    glb_uri: str
    suitable_for: str

    class Config:
        from_attributes = True


class Model3DDetail(Model3DOut):
    hotspots: list[HotspotOut] = []


class AssociateRequest(BaseModel):
    model_key: str


class ViewerPayload(BaseModel):
    lesson_id: int
    model_key: str
    name: str
    glb_uri: str
    hotspots: list[HotspotOut] = []
