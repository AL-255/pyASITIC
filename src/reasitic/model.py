"""Physical segment records corresponding to ASITIC ConductorSegment fields.

All geometry is in micrometres. Coordinates are local to the shape origin.
Separate ribbon edges are retained rather than inferred from a centerline.
"""
from dataclasses import dataclass, field, asdict,replace
import copy
from .retained_scalar import Real as R


@dataclass
class Segment:
    start: list[float]
    end: list[float]
    outer_start: list[float]
    outer_end: list[float]
    inner_start: list[float]
    inner_end: list[float]
    width: float
    thickness: float
    metal: int
    nx: int = 0
    ny: int = 0
    primary_width: float | None = None
    primary_thickness: float | None = None
    secondary: list = field(default_factory=list)

    @property
    def points(self):
        return (self.start, self.end, self.outer_start, self.outer_end,
                self.inner_start, self.inner_end)

    @property
    def polygon(self):
        return [p[:2] for p in (self.outer_start, self.outer_end,
                                self.inner_end, self.inner_start)]

    @property
    def length(self):
        from .geometry_metrics import segment_length
        return float(segment_length(self.start,self.end))

    @property
    def area(self):
        p = self.polygon
        return abs(sum(a[0]*b[1]-a[1]*b[0] for a, b in zip(p, p[1:]+p[:1])))/2

    def reverse(self):
        self.start, self.end = self.end, self.start
        self.outer_start, self.outer_end = self.outer_end, self.outer_start
        self.inner_start, self.inner_end = self.inner_end, self.inner_start


def link_secondary(segment):
    for i,child in enumerate(segment.secondary):child._native_group_next=segment.secondary[i+1]if i+1<len(segment.secondary)else None


def native_group(segment):
    if segment.secondary:return segment.secondary
    result=[];current=getattr(segment,'_native_group_next',None)
    while current is not None:
        result.append(current);current=getattr(current,'_native_group_next',None)
    return result


def copy_record(segment,*,groups=False):
    values={key:getattr(segment,key).copy()for key in('start','end','outer_start','outer_end','inner_start','inner_end')}
    result=replace(segment,**values,secondary=[copy_record(c)for c in reversed(native_group(segment))]if groups else[])
    link_secondary(result);return result


def copy_geometry(shape):
    """Native descriptor/record copy, including reversed secondary chains."""
    result=copy.copy(shape);result.origin=shape.origin.copy();result.parameters=copy.deepcopy(shape.parameters);result.warnings=shape.warnings.copy();result.segments=[];previous=None
    for segment in shape.segments:
        node=copy_record(segment,groups=True)
        for child in node.secondary:child._native_next=previous
        result.segments.append(node);previous=node
    result.link_primary();return result


@dataclass
class Shape:
    name: str
    kind: str
    origin: list[float]
    parameters: dict
    segments: list[Segment] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    electrical_phase: int | None = 1

    @property
    def phase_sign(self):
        if self.electrical_phase is None:return self._opaque_phase_sign
        return(self.electrical_phase>0)-(self.electrical_phase<0)

    @property
    def all_segments(self):
        return [record for segment in self.segments for record in(segment,*segment.secondary)]

    def link_primary(self):
        for i,segment in enumerate(self.segments):segment._native_next=self.segments[i+1]if i+1<len(self.segments)else None

    def reverse_segments(self):
        self.segments.reverse();self.link_primary()

    @property
    def bounds(self):
        points = [p for s in self.all_segments for p in s.points]
        if not points:return [1e15,1e15,-1e15,-1e15]
        return [min(p[0] for p in points), min(p[1] for p in points),
                max(p[0] for p in points), max(p[1] for p in points)]

    def offset(self, dx, dy):
        for s in self.segments:
            for p in s.points:
                p[0] = float(R(p[0])+R(dx))
                p[1] = float(R(p[1])+R(dy))

    def _rebase(self,x,y):
        # Native first stores the new origin, then translates by old-new.
        # That retained difference can differ from simply subtracting x/y.
        old=self.origin.copy()
        self.origin[0]=float(R(old[0])+R(x));self.origin[1]=float(R(old[1])+R(y))
        dx,dy=R(old[0])-R(self.origin[0]),R(old[1])-R(self.origin[1])
        for segment in self.segments:
            records=[segment];child=segment.secondary[0]if segment.secondary else None
            while child is not None:
                records.append(child);child=getattr(child,'_native_next',None)
            for record in records:
                for p in record.points:p[0]=float(R(p[0])+dx);p[1]=float(R(p[1])+dy)

    def reflect(self, axis):
        bounds = self.bounds
        low,high=R(bounds[axis]),R(bounds[axis+2])
        mirror = (high-low)+(low+low)
        for s in self.all_segments:
            for p in s.points:
                p[axis] = float(mirror-R(p[axis]))
        # ASITIC moves the local minimum into the shape origin.
        self._rebase(bounds[0],bounds[1])

    def rotate(self, angle,*,force=False):
        if not force and abs(angle) <= 1e-10:
            return
        x0, y0, x1, y1 = self.bounds
        from .precision import rotate_xy,native_midpoint
        cx,cy=native_midpoint(x0,x1),native_midpoint(y0,y1)
        for s in self.all_segments:
            for p in s.points:
                p[0],p[1]=rotate_xy(p[0],p[1],cx,cy,angle)
        x0, y0, *_ = self.bounds
        self._rebase(x0,y0)

    def to_dict(self):
        data = asdict(self)
        def clean(record):
            if not record['secondary']:record.pop('secondary')
            else:
                for child in record['secondary']:clean(child)
        for record in data['segments']:clean(record)
        if self.electrical_phase is None:data['electrical_phase_sign']=self.phase_sign
        from .geometry_metrics import retained_geometry_metrics
        length,area,metal_area=retained_geometry_metrics(self)
        data.update(bounds=self.bounds,length=length,area=area,metal_area=float(metal_area))
        return data
