# pairwise-mesh-lod

相机拉远时整栋建筑突然变成纸片，拉近又突然变回来，中间没有任何过渡；模型接缝处的顶点被简化掉，蒙皮一拉就裂开；不同分辨率的机器上同一个模型简化程度完全不一样。查下来是 render/lod.py 的 LOD 系统有严重问题：screen_error() 直接返回世界空间误差，不按距离和分辨率换算，远近判断完全失效；select_lod() 永远选第 0 级，永远用最精细模型；simplify_ratio() 恒返回 1，目标面数被忽略；weld_vertices() 不做顶点焊接，重复顶点原样保留，索引也不重映射；lock_boundary_vertices() 返回空集合，接缝顶点被简化掉；apply_lod_bias() 不裁剪偏置，越界索引直接崩；lod_fade_band() 返回零宽区间，级联之间硬切；fit_budget() 永远返回第 0 级，面数预算不起作用；bounding_radius() 用坐标最大值当半径，剔除范围完全不对。你要修的是：误差按距离、FOV 和分辨率换算成像素；按距离阈值选级；简化比例按目标面数计算并设下限；顶点按 epsilon 焊接并重映射索引；锁定边界顶点；偏置裁剪到合法区间；过渡区间有宽度；按面数预算选最精细的可接受级别；包围球按质心计算半径。render/lod.py 是核心，tests/test_lod.py 14个红。

## 运行

```
python -m pytest tests -q
```

初始状态：14 个用例失败。修复实现使全部用例通过，不要修改 `tests/` 下的测试。
