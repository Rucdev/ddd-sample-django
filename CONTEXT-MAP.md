# Context Map

図書館の貸出管理システム。モジュラモノリス構成で、DDD ベースのコンテキストと CRUD モジュールが同居する。

## Contexts

- [Lending(貸出)](./lending/CONTEXT.md) — DDD。蔵書の貸出・返却・延長・延滞を扱うコアドメイン
- [Reservation(予約)](./reservation/CONTEXT.md) — DDD。貸出中の書誌への予約と、返却後の取置を扱う
- [Catalog(蔵書)](./catalog/CONTEXT.md) — CRUD。書誌と蔵書(個体)のマスタ管理
- [Members(会員)](./members/CONTEXT.md) — CRUD。会員のマスタ管理と会員ステータス

## Relationships

- **Lending → Members**: `LoanOverdue` イベントを発行し、Members が会員を貸出停止にする
- **Lending → Reservation**: `BookReturned` イベントを発行し、Reservation が予約待ち行列の先頭会員のために取置を作る
- **Reservation → Lending**: 取置中の蔵書は取置対象の会員にしか貸し出せない(Lending が Reservation の公開 API に照会する)
- **Lending / Reservation → Catalog, Members**: 書誌 ID・蔵書 ID・会員 ID を値として保持し、必要時に公開 API で照会する(モジュールをまたぐ ForeignKey は張らない)
