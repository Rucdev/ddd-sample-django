# 実装計画

カフェのモバイルオーダー(モジュラモノリス、DDD + CRUD 同居)の実装計画。題材は図書館の貸出管理から切り替えた([ADR-0002](./adr/0002-switch-domain-to-cafe-mobile-order.md))。図書館版の計画とコードは git の履歴から参照できる。

**前提資料**(実装前に必読):

- [directory-structure.md](./directory-structure.md) — ディレクトリ構成、レイヤ責務、DDD と Django の接続面のルール
- [CONTEXT-MAP.md](../CONTEXT-MAP.md) — コンテキスト一覧とモジュール間関係
- 各モジュールの `CONTEXT.md` — 用語集(コード内の命名はここに従う)
- [ADR-0001](./adr/0001-drf-limited-use.md) — DRF の限定利用ルール
- [ADR-0003](./adr/0003-query-side-uses-drf-generics-and-django-filter.md) — 参照系での DRF 汎用 View と django-filter の利用

**ドメインの仕様値**(各 CONTEXT.md より):

- 数量: 1 明細あたり 1〜10 個 / 進行中の注文: 1 人 3 件まで
- 割引率: 一般 0% / シルバー 5% / ゴールド 10%(1 円未満切り捨て)
- キャンセル: 受付済(調理開始前)のみ / ポイント: 支払額 100 円につき 1 ポイント

**共通ルール**:

- テストは Django 標準のテストランナー(`python manage.py test`)を使う。追加依存を増やさない。
- domain 層のテストは DB 不要で書く(素の `unittest.TestCase`)。
- ルールを時刻に依存させない(期限・定期実行のバッチを持ち込まない)。

---

## Phase 0: 基盤整備

`shared/`(Entity / ValueObject / DomainEvent / 同期イベントバス / DRF の例外ハンドラ)は図書館版から変更なしで流用する。

## Phase 1: CRUD アプリ(menu / customers)

1. **menu のモデル**: `Category`(`name`, `display_order`)、`MenuItem`(`category = FK(Category)`(同一モジュール内なので FK 可)、`name`, `price`(円の整数), `status`(`ON_SALE` 販売中 / `SOLD_OUT` 品切れ))
2. **customers のモデル**: `Customer`(`name`, `email`, `user = OneToOneField(User, null=True)`, `status`(`ACTIVE` / `SUSPENDED`), `rank`(`REGULAR` / `SILVER` / `GOLD`), `points`)
3. **admin 登録**: 両アプリとも admin を主戦力にする
4. **public.py**: `menu.public.get_menu_item` / `list_available_menu_items`、`customers.public.get_customer` / `add_points`
5. **デモデータ**: `fixtures/demo.json`(固定 UUID の会員・商品)

## Phase 2: ordering(DDD コア)

1. **domain 層**(Django import 禁止):
   - `value_objects.py` — `Money`, `DiscountRate`(+ ランク → 割引率の表 `discount_rate_for_rank`), `OrderLine`(数量 1〜10 を `__post_init__` で検証), `OrderStatus`
   - `entities.py` — `Order` 集約ルート。`place()`(明細が空なら `EmptyOrder`)、`start_preparing()`, `mark_ready()`, `pick_up()`, `cancel()`。金額は `subtotal` / `discount` / `total` プロパティ
   - `events.py` — `OrderPlaced`(明細の商品名・数量を運ぶ), `OrderCancelled`, `OrderPickedUp`(支払額を運ぶ)
   - `services.py` — `OrderPolicy`: 進行中の注文数の上限チェック(リポジトリの集計を使う)
2. **infrastructure 層**: `OrderModel` + `OrderLineModel`(明細は別テーブル。注文時点の商品名・単価をスナップショット)、`DjangoOrderRepository`
3. **application 層**: `place_order`(会員・商品を public API で照会 → 明細生成 → 上限チェック → 割引率決定 → 保存 → イベント発行)、`cancel_order`、`pick_up_order`、`start_preparing` / `mark_ready`(kitchen のイベントから呼ばれる)、`queries.py`
4. **presentation 層**: 注文画面(販売中の商品ごとに数量欄を動的に生やす Form)と API(`APIView` + 素の `Serializer`)

## Phase 3: kitchen(DDD)

1. **domain 層**: `Ticket` 集約ルート(`open()`, `start_cooking()`, `complete()`, `cancel()`)、`TicketItem`、`CookingStarted` / `CookingCompleted`
2. **infrastructure 層**: `TicketModel`(明細は JSONField。ordering の別テーブル方式との比較用)、`DjangoTicketRepository`
3. **イベント購読**: `OrderPlaced` → チケット作成(冪等)、`OrderCancelled` → チケット取消
4. **presentation**: キッチン画面(調理開始・調理完了ボタン)と API

## Phase 4: モジュール間連携の仕上げ

1. **ordering のイベント購読**: `CookingStarted` → 調理中、`CookingCompleted` → 受取可
2. **customers のイベント購読**: `OrderPickedUp` → ポイント加算
3. **結合テスト**: 本番の購読配線を通して「注文 → チケット → 調理 → 受取 → ポイント」「キャンセル → チケット取消」「調理開始後はキャンセル不可」を確認(`kitchen/tests/test_application/test_order_flow_integration.py`)
4. **import-linter**: 各モジュールは他モジュールの `public`(とイベントを購読する側からの `domain.events`)以外を import 禁止。ordering ↔ kitchen はイベントのみ。ドメイン層の Django 非依存
5. **最終確認**: 全テスト + `lint-imports` + README の「画面で一通り動かす」の手順

## Phase 5: inventory(CRUD + services)

1. **menu の在庫切れフラグ**: `MenuItem.out_of_stock`(inventory だけが書く。admin では読み取り専用)。注文できる = 販売中 かつ 在庫切れでない。`menu.public.set_out_of_stock` を追加
2. **モデル**: `Kit`(`menu_item_id` 一意、実在庫・予約数・管理中/管理停止、DB 制約で 実在庫 ≥ 予約数)、`Reservation`(確保中 → 使用済 / 取消)、`StockMovement`(在庫ログ)
3. **services.py**: 入庫・出庫・予約の確保/使用/取消・管理停止/再開・注文での消費/戻し。条件付き UPDATE で売り越しを防ぎ、在庫ログと在庫切れフラグを同じトランザクションで更新する
4. **ordering との連携**: `PlaceOrderUseCase` が `inventory.public.allocate_for_order` を呼び、`InsufficientStock` を `OutOfStock`(409)に詰め替える。`OrderCancelled` を inventory が購読して戻す
5. **画面・API**: キットの登録・名前の編集と閲覧は admin、在庫数を動かす操作は専用画面(`/inventory/`)と API(`/inventory/api/`。ViewSet + `@action`、削除なし)

---

## 実装時の注意(ハマりどころ)

- `AppConfig.ready()` でのイベント購読は import 副作用に注意。ハンドラは遅延 import(関数内 import)で循環参照を避ける。ordering と kitchen は互いのイベントを購読し合うので特に注意。
- 同期イベントハンドラはユースケースの `transaction.atomic()` 内で走る。ハンドラ失敗 = 全体ロールバックが今回の仕様(例: チケットの取消に失敗したら注文のキャンセルも戻る)。
- モジュール単体のテストで本物の購読が邪魔になる場合(kitchen のテストで ordering 側の注文が存在しない等)は、`event_bus.unsubscribe` で一時的に外し、`addCleanup` で戻す。
- ドメインエンティティの ID は UUID を使う(エンティティ生成時に `uuid4` で採番)。
