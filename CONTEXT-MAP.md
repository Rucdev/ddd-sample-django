# Context Map

カフェのモバイルオーダー。モジュラモノリス構成で、DDD ベースのコンテキストと CRUD モジュールが同居する。

## Contexts

- [Ordering(注文)](./ordering/CONTEXT.md) — DDD。注文(持ち帰り・店内)の受付・キャンセル・受取 / 提供と金額計算、店内の席ごとの会計を扱うコアドメイン
- [Kitchen(キッチン)](./kitchen/CONTEXT.md) — DDD。注文明細ごとの調理チケットの進行(調理待ち → 調理中 → 調理済)を扱う
- [Menu(メニュー)](./menu/CONTEXT.md) — CRUD。カテゴリと商品のマスタ管理
- [Customers(会員)](./customers/CONTEXT.md) — CRUD。会員のマスタ管理と会員ランク・ポイント
- [Seating(座席)](./seating/CONTEXT.md) — DDD。座席構成ファイル(YAML)から席を作り、空き・予約中・使用中を管理する。席の利用の始まり・終わりをイベントで知らせる

## Relationships

- **Ordering → Menu(照会)**: 注文時に Menu の公開 API(`get_menu_item`)で商品の販売状況と価格を照会し、商品名・単価を注文明細にスナップショットとして写す
- **Ordering → Customers(照会)**: 注文時に Customers の公開 API(`get_customer`)で会員の有効性とランクを照会し、ランクから割引率を引き当てる(`ordering/domain/value_objects.py` の `discount_rate_for_rank`)
- **Ordering → Kitchen(イベント)**: `OrderPlaced` で Kitchen が明細ごとに調理チケットを作り、`OrderCancelled` でその注文のチケットをすべて取り消す(`kitchen/apps.py` の `ready()` で購読)
- **Kitchen → Ordering(イベント)**: `CookingStarted` / `CookingCompleted` は明細ごと(明細番号つき)に届く。Ordering はその明細の調理状況を進め、最初の 1 品で注文を「調理中」に、全品そろったら「受取可」にする(`ordering/apps.py` の `ready()` で購読)。注文単位で足並みをそろえるのは Kitchen ではなく、注文の持ち主の Ordering の責務
- **Ordering → Customers(イベント)**: `OrderPickedUp` で Customers が支払額に応じたポイントを付与する(`customers/apps.py` の `ready()` で購読)。店内の注文は受取ではなく提供で終わり、このイベントは出ない
- **Seating → Ordering(イベント)**: `SeatOccupied` で Ordering がその席の会計を開き、`SeatVacated` で支払済にする(`ordering/apps.py` の `ready()` で購読)。席からの注文は、その席で開いている会計があるときだけ受け付ける。Seating は Ordering を知らない([ADR-0004](./docs/adr/0004-dine-in-orders-and-seat-bills.md))
- **Ordering / Kitchen → Menu, Customers, Seating**: 商品 ID・会員 ID・注文 ID・席 ID を値として保持する(モジュールをまたぐ ForeignKey は張らない)

Ordering と Kitchen の間は**イベントだけ**でやり取りし、互いの公開 API を同期的に照会することはしない。例えば「調理開始後はキャンセルできない」という判定は、Kitchen に照会する代わりに `CookingStarted` を受けて Ordering 自身が持つ明細の調理状況・注文ステータス(調理中)で行う。照会し合うと双方向の依存になるので、それを避けるための設計判断。import-linter の契約でも、Ordering から Kitchen へは `kitchen.domain.events` しか import できないようにしている(逆向きも同じ)。

```
                   (1)                              (2)
     menu ◀─────────────────────── ordering ──────────────────────▶ customers
                                   ▲ │ │  ▲                           ▲
                               (6) │ │ │  │ (4)                       │ (5)
                                   │ │ ▼  │                           │
                             seating │ kitchen                        │
                                     │  (3)                           │
                                     └────────────────────────────────┘
```

| 番号 | 向き | 種類 | 内容 |
| --- | --- | --- | --- |
| (1) | ordering → menu | 照会 | `get_menu_item`。商品の販売状況と価格 |
| (2) | ordering → customers | 照会 | `get_customer`。会員の有効性とランク |
| (3) | ordering → kitchen | イベント | `OrderPlaced` / `OrderCancelled` |
| (4) | kitchen → ordering | イベント | `CookingStarted` / `CookingCompleted`(明細ごと) |
| (5) | ordering → customers | イベント | `OrderPickedUp`。ポイント付与 |
| (6) | seating → ordering | イベント | `SeatOccupied` / `SeatVacated`。席の会計を開く / 支払済にする |

矢印は、照会なら呼び出す側から呼ばれる側へ、イベントなら発行する側から購読する側へ向けている。
