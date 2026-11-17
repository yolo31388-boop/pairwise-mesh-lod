"""Mesh LOD selection and simplification helpers (starter code with defects)."""

import math


def screen_error(world_error, distance, fov=1.0, screen_height=1080):
    return world_error


def select_lod(thresholds, distance):
    return 0


def simplify_ratio(source_tris, target_tris, min_ratio=0.05):
    return 1.0


def weld_vertices(vertices, epsilon=1e-4):
    return list(vertices), list(range(len(vertices)))


def remap_indices(indices, mapping):
    return list(indices)


def lock_boundary_vertices(triangles):
    return set()


def apply_lod_bias(current_index, bias, max_index=3):
    return current_index


def lod_fade_band(threshold, band_ratio=0.15):
    return (threshold, threshold)


def fit_budget(lods, triangle_budget):
    return 0


def bounding_radius(vertices):
    return max(max(abs(x), abs(y)) for x, y in vertices)
