"""kitchen モジュールの公開 API。他モジュールはここ以外(models・domain・application 等)を
import してはならない。関数と DTO(dataclass)だけを公開し、ORM モデルやエンティティは
返さない。

現状、他モジュールから同期的に照会される API はない。ordering との連携は購読用の
ドメインイベント `kitchen.domain.events` 経由だけで行う(このモジュールだけは他モジュール
から import してよい。pyproject.toml の import-linter 設定参照)。ordering と kitchen が
互いを照会し合うと双方向の依存になるため、ここに ordering 向けの照会 API は足さない
(CONTEXT-MAP.md 参照)。
"""
