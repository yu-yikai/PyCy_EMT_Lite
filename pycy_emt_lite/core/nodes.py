"""
文件名称：nodes.py
文件作用：管理电路节点编号和参考节点。

主要内容：
1. 将用户可读节点名映射为 MNA 矩阵索引
2. 统一处理参考节点 ground
3. 提供节点电压结果字段名称
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

GROUND_NAMES = {"0", "gnd", "ground", "GND", "GROUND"}


@dataclass(slots=True)
class NodeManager:
    """节点编号管理器。

    参考节点不进入 MNA 未知量向量，所有非参考节点按首次出现顺序编号。
    """

    _indices: dict[str, int] = field(default_factory=dict)

    def add(self, node: str) -> None:
        """添加节点名称。参考节点会被忽略。"""

        if node in GROUND_NAMES:
            return
        if node not in self._indices:
            self._indices[node] = len(self._indices)

    def add_many(self, nodes: Iterable[str]) -> None:
        """批量添加节点。"""

        for node in nodes:
            self.add(node)

    def index(self, node: str) -> int | None:
        """返回节点编号；参考节点返回 None。"""

        if node in GROUND_NAMES:
            return None
        try:
            return self._indices[node]
        except KeyError as exc:
            raise KeyError(f"节点 {node!r} 尚未注册。") from exc

    @property
    def count(self) -> int:
        """返回非参考节点数量。"""

        return len(self._indices)

    @property
    def names(self) -> list[str]:
        """按 MNA 索引顺序返回节点名称。"""

        return [name for name, _ in sorted(self._indices.items(), key=lambda item: item[1])]
