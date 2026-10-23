"""Physical segment records corresponding to ASITIC ConductorSegment fields.

All geometry is in micrometres. Coordinates are local to the shape origin.
Separate ribbon edges are retained rather than inferred from a centerline.
"""
from dataclasses import dataclass, field, asdict
import math


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
        return math.dist(self.start, self.end)

    @property
    def area(self):
        p = self.polygon
        return abs(sum(a[0]*b[1]-a[1]*b[0] for a, b in zip(p, p[1:]+p[:1])))/2

    def reverse(self):
        self.start, self.end = self.end, self.start
        self.outer_start, self.outer_end = self.outer_end, self.outer_start
        self.inner_start, self.inner_end = self.inner_end, self.inner_start


@dataclass
class Shape:
    name: str
    kind: str
    origin: list[float]
    parameters: dict
    segments: list[Segment] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def bounds(self):
        points = [p for s in self.segments for p in s.points]
        return [min(p[0] for p in points), min(p[1] for p in points),
                max(p[0] for p in points), max(p[1] for p in points)]

    def offset(self, dx, dy):
        for s in self.segments:
            for p in s.points:
                p[0] += dx
                p[1] += dy

    def reflect(self, axis):
        bounds = self.bounds
        mirror = bounds[axis]+bounds[axis+2]
        for s in self.segments:
            for p in s.points:
                p[axis] = mirror-p[axis]
        # ASITIC moves the local minimum into the shape origin.
        self.offset(-bounds[0], -bounds[1])
        self.origin[0] += bounds[0]
        self.origin[1] += bounds[1]

    def rotate(self, angle):
        if abs(angle) <= 1e-10:
            return
        x0, y0, x1, y1 = self.bounds
        from .precision import rotate_xy,native_midpoint
        cx,cy=native_midpoint(x0,x1),native_midpoint(y0,y1)
        for s in self.segments:
            for p in s.points:
                p[0],p[1]=rotate_xy(p[0],p[1],cx,cy,angle)
        x0, y0, *_ = self.bounds
        self.offset(-x0, -y0)
        self.origin[0] += x0
        self.origin[1] += y0

    def to_dict(self):
        data = asdict(self)
        data.update(bounds=self.bounds, length=sum(s.length for s in self.segments),
                    area=sum(s.area for s in self.segments))
        return data
