"""Mesh LOD selection and simplification helpers.

本模块提供 LOD（细节层级）流水线用到的纯函数：

* 误差度量：``screen_error`` 把世界空间几何误差按距离、FOV 和渲染分辨率
  换算成像素误差，作为选级与边折叠的依据；
* 选级：``select_lod`` 按距离阈值选择 LOD，``apply_lod_bias`` 在合法
  区间内应用偏置，``fit_budget`` 在三角形面数预算内选最精细的可用级；
* 简化：``simplify_ratio`` 计算目标/源面数比例并设下限，
  ``weld_vertices`` / ``remap_indices`` 做 epsilon 焊接与索引重映射，
  ``lock_boundary_vertices`` 锁定只属于单个三角形的接缝/边界顶点
  （UV、材质边界同样表现为非共享边，折叠时不得越过这些顶点）；
* 过渡：``lod_fade_band`` 返回有宽度的淡入淡出区间，避免硬切；
* 剔除：``bounding_radius`` 按质心重新计算包围球半径。
"""

import math


def screen_error(world_error, distance, fov=1.0, screen_height=1080):
    """把世界空间误差投影成屏幕空间的像素误差。

    透视投影下，世界误差在屏幕上的张角近似为 ``world_error / distance``，
    再乘以每弧度对应的像素数 ``screen_height / (2*tan(fov/2))``
    （``fov`` 为垂直视场角，弧度）。因此结果与距离成反比、与屏幕高度
    成正比：距离加倍像素误差减半，分辨率加倍像素误差加倍。
    """
    if distance <= 0:
        raise ValueError("distance must be positive")
    if fov <= 0:
        raise ValueError("fov must be positive")
    pixels_per_radian = screen_height / (2.0 * math.tan(fov / 2.0))
    return (world_error / distance) * pixels_per_radian


def select_lod(thresholds, distance):
    """按距离阈值选择 LOD 层级。

    ``thresholds[i]`` 是从第 i 级切到第 i+1 级的距离（升序）。
    距离落在第几个阈值之后就选第几级；超过全部阈值时返回最粗一级
    （索引为 ``len(thresholds)``，即 N 个阈值对应 N+1 个层级）。
    """
    level = 0
    for threshold in thresholds:
        if distance >= threshold:
            level += 1
        else:
            break
    return level


def simplify_ratio(source_tris, target_tris, min_ratio=0.05):
    """计算目标面数占源面数的简化比例，并夹到 ``[min_ratio, 1.0]``。

    比例不允许超过 1（简化不会增加面数），也不允许低于 ``min_ratio``
    （防止过度简化把模型塌成空壳）。
    """
    if source_tris <= 0:
        raise ValueError("source_tris must be positive")
    if target_tris < 0:
        raise ValueError("target_tris must be non-negative")
    ratio = target_tris / source_tris
    return max(min_ratio, min(1.0, ratio))


def weld_vertices(vertices, epsilon=1e-4):
    """按 epsilon 距离焊接重复顶点。

    采用顺序贪心聚类：每个顶点与已经建立的聚类代表点比较，若欧氏距离
    不超过 ``epsilon`` 就并入该聚类，否则新建聚类。支持 2D/3D 等任意
    维度的坐标元组。

    返回 ``(unique_vertices, mapping)``：``unique_vertices`` 是每个聚类
    的代表顶点（保留首次出现的坐标），``mapping[i]`` 是原顶点 ``i``
    焊接后的索引，可直接交给 :func:`remap_indices` 重写索引缓冲。
    """
    unique = []
    mapping = []
    for vertex in vertices:
        found = -1
        for j, representative in enumerate(unique):
            dist_sq = sum(
                (a - b) * (a - b) for a, b in zip(vertex, representative)
            )
            if dist_sq <= epsilon * epsilon:
                found = j
                break
        if found < 0:
            found = len(unique)
            unique.append(tuple(vertex))
        mapping.append(found)
    return unique, mapping


def remap_indices(indices, mapping):
    """按焊接/折叠产生的映射表重写索引缓冲。

    每个旧索引 ``i`` 被替换成 ``mapping[i]``。每一级 LOD 使用独立的
    索引缓冲时都要走一遍该重映射，避免共用缓冲导致绘制错位。
    """
    return [mapping[index] for index in indices]


def lock_boundary_vertices(triangles):
    """找出边界（接缝）上必须锁定、不得折叠的顶点。

    统计每条无向边被多少个三角形引用：只被一个三角形引用的边是开放
    边界边，其端点即为边界顶点。UV 断开处与材质切换处在几何上同样
    表现为非共享边——焊接后两侧顶点互不共享，因此这些接缝顶点也会
    被识别并锁定，防止简化撕裂 UV、漏光或破坏材质分组。
    """
    edge_count = {}
    for triangle in triangles:
        a, b, c = triangle
        edges = (
            tuple(sorted((a, b))),
            tuple(sorted((b, c))),
            tuple(sorted((c, a))),
        )
        for edge in edges:
            edge_count[edge] = edge_count.get(edge, 0) + 1

    locked = set()
    for (a, b), count in edge_count.items():
        if count == 1:
            locked.add(a)
            locked.add(b)
    return locked


def apply_lod_bias(current_index, bias, max_index=3):
    """对 LOD 索引施加偏置，并裁剪到合法区间 ``[0, max_index]``。

    正偏置倾向更粗的层级（省面数），负偏置倾向更精细的层级。
    裁剪保证返回值永远是合法索引，不会越界崩溃。
    """
    desired = current_index + bias
    return max(0, min(max_index, desired))


def lod_fade_band(threshold, band_ratio=0.15):
    """计算切换阈值周围的淡入淡出区间 ``(low, high)``。

    区间宽度为 ``threshold * band_ratio``，下界低于阈值、上界等于阈值：
    在区间内两级 LOD 按距离做交叉淡化（geomorph），到阈值处完成切换，
    从而消除硬切时的突跳。``band_ratio=0`` 时退化为零宽硬切。
    """
    width = threshold * band_ratio
    return (threshold - width, threshold)


def fit_budget(lods, triangle_budget):
    """在三角形面数预算内返回最精细的可用 LOD 索引。

    ``lods`` 按从精细到粗糙排列，每项为带 ``"tris"`` 面数的字典。
    选择第一个面数不超过预算的层级；若所有层级都超预算，则回退到
    最粗（最便宜）的一级。
    """
    for index, lod in enumerate(lods):
        if lod["tris"] <= triangle_budget:
            return index
    return len(lods) - 1


def bounding_radius(vertices):
    """计算以顶点质心为球心的包围球半径。

    简化改变顶点位置和数量后必须重算包围体，否则视锥剔除会沿用旧球
    把已经变小的模型错误裁掉。返回质心到最远顶点的距离（取包围半径）。
    支持 2D/3D 等任意维度的坐标元组；空顶点集没有合法包围球。
    """
    if not vertices:
        raise ValueError("cannot compute bounding radius of empty mesh")
    dimension = len(vertices[0])
    centroid = [
        sum(vertex[axis] for vertex in vertices) / len(vertices)
        for axis in range(dimension)
    ]
    return max(
        math.sqrt(
            sum((vertex[axis] - centroid[axis]) ** 2 for axis in range(dimension))
        )
        for vertex in vertices
    )
