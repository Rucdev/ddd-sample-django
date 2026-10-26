"""ordering モジュールの公開 API。他モジュールはここ以外(models・domain・application 等)を
import してはならない。関数と DTO(dataclass)だけを公開し、ORM モデルやエンティティは
返さない。

現状、他モジュールから同期的に照会される API はない。kitchen・customers との連携は
すべて購読用のドメインイベント `ordering.domain.events` 経由で行う(このモジュールだけは
他モジュールから import してよい。pyproject.toml の import-linter 設定参照)。
照会が必要になったら、ここに関数と DTO を足す。
"""
