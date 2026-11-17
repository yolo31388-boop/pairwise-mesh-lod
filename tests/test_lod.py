import pytest

from render.lod import (apply_lod_bias, bounding_radius, fit_budget,
                        lock_boundary_vertices, lod_fade_band, remap_indices,
                        screen_error, select_lod, simplify_ratio,
                        weld_vertices)


def test_screen_error_shrinks_with_distance():
    near = screen_error(1.0, 10.0)
    far = screen_error(1.0, 100.0)
    assert near / far == pytest.approx(10.0, rel=0.01)


def test_screen_error_scales_with_resolution():
    assert screen_error(1.0, 10.0, screen_height=2160) == pytest.approx(
        2 * screen_error(1.0, 10.0, screen_height=1080))
    assert 0 < screen_error(1.0, 10.0, screen_height=1080)


def test_select_lod_uses_distance_thresholds():
    assert select_lod([10, 30, 80], 40) == 2


def test_select_lod_clamps_to_coarsest_level():
    assert select_lod([10, 30, 80], 200) == 3


def test_simplify_ratio_is_target_over_source():
    assert simplify_ratio(10000, 2500) == pytest.approx(0.25)


def test_weld_merges_identical_vertices():
    vertices = [(0.0, 0.0), (0.0, 0.0), (1.0, 0.0)]
    unique, mapping = weld_vertices(vertices)
    assert len(unique) == 2  # 前两个点在 epsilon 内合并
    assert mapping == [0, 0, 1]


def test_weld_respects_epsilon_distance():
    vertices = [(0.0, 0.0), (0.0, 0.0005), (1.0, 0.0)]
    unique, _ = weld_vertices(vertices, epsilon=1e-3)
    assert len(unique) == 2  # 前两个点在 epsilon 内合并


def test_indices_are_remapped_after_weld():
    assert remap_indices([0, 1, 2, 0], [0, 0, 1]) == [0, 0, 1, 0]


def test_boundary_vertices_are_locked():
    assert lock_boundary_vertices([(0, 1, 2)]) == {0, 1, 2}


def test_lod_bias_is_clamped():
    assert apply_lod_bias(1, 5) == 3
    assert apply_lod_bias(1, -5) == 0


def test_fade_band_has_width():
    low, high = lod_fade_band(20, band_ratio=0.1)
    assert low == pytest.approx(18.0)
    assert high == pytest.approx(20.0)


def test_budget_picks_finest_level_that_fits():
    lods = [{"tris": 50000}, {"tris": 20000}, {"tris": 5000}, {"tris": 1000}]
    assert fit_budget(lods, 8000) == 2


def test_budget_falls_back_to_cheapest_level():
    lods = [{"tris": 50000}, {"tris": 20000}, {"tris": 5000}, {"tris": 1000}]
    assert fit_budget(lods, 500) == 3


def test_bounding_radius_is_centered_on_the_mesh():
    assert bounding_radius([(0.0, 0.0), (3.0, 4.0)]) == pytest.approx(2.5)

