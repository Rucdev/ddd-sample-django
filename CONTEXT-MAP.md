# Context Map

カフェのモバイルオーダー。モジュラモノリス構成で、DDD ベースのコンテキストと CRUD モジュールが同居する。

## Contexts

- [Ordering(注文)](./ordering/CONTEXT.md) — DDD。注文の受付・キャンセル・受取と金額計算を扱うコアドメイン
- [Kitchen(キッチン)](./kitchen/CONTEXT.md) — DDD。調理チケットの進行(調理待ち → 調理中 → 調理済)を扱う
- [Menu(メニュー)](./menu/CONTEXT.md) — CRUD。カテゴリと商品のマスタ管理
- [Customers(会員)](./customers/CONTEXT.md) — CRUD。会員のマスタ管理と会員ランク・ポイント
- [Inventory(在庫)](./inventory/CONTEXT.md) — CRUD(在庫操作は `services.py` に集約)。商品を作るキットの入出庫・予約・在庫ログ

## Relationships

- **Ordering → Menu(照会)**: 注文時に Menu の公開 API(`get_menu_item`)で商品の販売状況と価格を照会し、商品名・単価を注文明細にスナップショットとして写す
- **Ordering → Customers(照会)**: 注文時に Customers の公開 API(`get_customer`)で会員の有効性とランクを照会し、ランクから割引率を引き当てる(`ordering/domain/value_objects.py` の `discount_rate_for_rank`)
- **Ordering → Kitchen(イベント)**: `OrderPlaced` で Kitchen が調理チケットを作り、`OrderCancelled` で調理チケットを取り消す(`kitchen/apps.py` の `ready()` で購読)
- **Kitchen → Ordering(イベント)**: `CookingStarted` で Ordering が注文を「調理中」に、`CookingCompleted` で「受取可」にする(`ordering/apps.py` の `ready()` で購読)
- **Ordering → Customers(イベント)**: `OrderPickedUp` で Customers が支払額に応じたポイントを付与する(`customers/apps.py` の `ready()` で購読)
- **Ordering → Inventory(照会)**: 注文時に Inventory の公開 API(`allocate_for_order`)で商品のキットを消費する。足りなければ注文ごと取り消す
- **Ordering → Inventory(イベント)**: `OrderCancelled` で Inventory が消費したキットを戻す(`inventory/apps.py` の `ready()` で購読)
- **Inventory → Menu(照会・更新)**: キット登録時に商品の存在を照会し、キットの注文可能数が 0 になったら / 戻ったら `set_out_of_stock` で商品の在庫切れフラグを切り替える
- **Ordering / Kitchen / Inventory → Menu, Customers**: 商品 ID・会員 ID・注文 ID を値として保持する(モジュールをまたぐ ForeignKey は張らない)

Ordering と Kitchen の間は**イベントだけ**でやり取りし、互いの公開 API を同期的に照会することはしない。例えば「調理開始後はキャンセルできない」という判定は、Kitchen に照会する代わりに `CookingStarted` を受けて Ordering 自身が持つ注文ステータス(調理中)で行う。照会し合うと双方向の依存になるので、それを避けるための設計判断。import-linter の契約でも、Ordering から Kitchen へは `kitchen.domain.events` しか import できないようにしている(逆向きも同じ)。

```
                   (1)                              (2)
     menu ◀─────────────────────── ordering ──────────────────────▶ customers
      ▲                            │ │ │ ▲                            ▲
      │                        (3) │ │ │ │ (4) (5)                    │ (6)
      │                            │ │ ▼ │                            │
      │                            │ │ kitchen                        │
      │                            │ └────────────────────────────────┘
      │                            │
      │                            ▼
      └─────────────────────── inventory
                 (7)
```

| 番号 | 向き | 種類 | 内容 |
| --- | --- | --- | --- |
| (1) | ordering → menu | 照会 | `get_menu_item`。商品の販売状況と価格 |
| (2) | ordering → customers | 照会 | `get_customer`。会員の有効性とランク |
| (3) | ordering → inventory | 照会 + イベント | `allocate_for_order` でキットを消費 / `OrderCancelled` で戻す |
| (4) | ordering → kitchen | イベント | `OrderPlaced` / `OrderCancelled` |
| (5) | kitchen → ordering | イベント | `CookingStarted` / `CookingCompleted` |
| (6) | ordering → customers | イベント | `OrderPickedUp`。ポイント付与 |
| (7) | inventory → menu | 照会 + 更新 | `get_menu_item` / `set_out_of_stock` |

矢印は、照会なら呼び出す側から呼ばれる側へ、イベントなら発行する側から購読する側へ向けている。
