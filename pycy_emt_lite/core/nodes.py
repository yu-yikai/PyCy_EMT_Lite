"""
文件名称：nodes.py
文件作用：管理电路节点编号和参考节点。

主要内容：
1. 将用户可读节点名映射为 MNA 矩阵索引
2. 统一处理参考节点 ground
3. 提供节点电压结果字段名称
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

GROUND_NAMES = {"0", "gnd", "ground"}


def _is_ground(node: str) -> bool:
    return isinstance(node, str) and node.lower() in GROUND_NAMES


def _check_internal_nodes(name: str, internal: Iterable[str], external: Iterable[str]) -> None:
    """内部节点不能接地或与外部端点重合；普通节点仍区分大小写。"""
    ports = set(external)
    for node in internal:
        if _is_ground(node) or node in ports:
            raise ValueError(f"元件 {name!r} 的内部节点 {node!r} 与外部端点/参考地冲突；请重命名内部节点或外部端点。")


@dataclass(slots=True)
class NodeManager:
    """节点编号管理器。

    参考节点不进入 MNA 未知量向量，所有非参考节点按首次出现顺序编号。
    """

    _indices: dict[str, int] = field(default_factory=dict)

    def add(self, node: str) -> None:
        """添加节点名称。参考节点会被忽略。"""

        if not isinstance(node, str) or not node.strip():
            raise ValueError(f"节点名称必须是非空字符串，收到 {node!r}。")
        if _is_ground(node):
            return
        if node not in self._indices:
            self._indices[node] = len(self._indices)

    def add_many(self, nodes: Iterable[str]) -> None:
        """批量添加节点。"""

        for node in nodes:
            self.add(node)

    def index(self, node: str) -> int | None:
        """返回节点编号；参考节点返回 None。"""

        if _is_ground(node):
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
