# ddd-sample-django

Django でモジュラモノリスを構成し、**DDD ベースのモジュール**と**通常の CRUD モジュール**を同居させるサンプルプロジェクト。題材はカフェのモバイルオーダー(注文 → 調理 → 受取)。

題材は以前「図書館の貸出管理システム」だった。変更の理由は [ADR-0002](docs/adr/0002-switch-domain-to-cafe-mobile-order.md) を参照。

設計の詳細は以下を参照:

- [docs/directory-structure.md](docs/directory-structure.md) — ディレクトリ構成、レイヤ責務、DDD と Django の接続面のルール
- [CONTEXT-MAP.md](CONTEXT-MAP.md) — コンテキスト(モジュール)一覧とモジュール間の関係
- 各モジュールの `CONTEXT.md`(`ordering/CONTEXT.md` など) — ドメイン用語集
- [docs/adr/](docs/adr/) — アーキテクチャ上の決定記録
- [docs/implementation-plan.md](docs/implementation-plan.md) — フェーズごとの実装計画

## モジュール一覧

| モジュール | 種類 | 役割 |
| --- | --- | --- |
| [ordering](ordering/CONTEXT.md) | DDD | 注文の受付・キャンセル・受取、金額計算(会員ランク割引) |
| [kitchen](kitchen/CONTEXT.md) | DDD | 調理チケットの進行(調理待ち → 調理中 → 調理済) |
| [menu](menu/CONTEXT.md) | CRUD | カテゴリ・商品のマスタ管理 |
| [customers](customers/CONTEXT.md) | CRUD | 会員のマスタ管理、会員ランク・ポイント |
| [inventory](inventory/CONTEXT.md) | CRUD | 商品を作るキットの入出庫・予約・在庫ログ。在庫が足りない商品は注文できない |

`shared/` は全モジュールが利用できる共有カーネル(Entity / ValueObject / DomainEvent の基底クラスと、モジュール間イベントバス)。

## セットアップ

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py loaddata demo   # デモ用のメニュー・会員・キットを投入
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

起動したら `http://127.0.0.1:8000/` がトップページ(各画面へのリンク)、`/admin/` が管理サイト。

図書館版の `db.sqlite3` が手元に残っている場合は、削除してから `migrate` し直す(図書館版のテーブルが残ったままになるため)。

## 画面で一通り動かす

デモデータの会員 ID は覚えやすい固定値にしてある。

| 会員 ID | 名前 | ランク(割引率) |
| --- | --- | --- |
| `00000000-0000-0000-0000-000000000001` | 一般 太郎 | 一般(0%) |
| `00000000-0000-0000-0000-000000000002` | シルバー 花子 | シルバー(5%) |
| `00000000-0000-0000-0000-000000000003` | ゴールド 次郎 | ゴールド(10%) |
| `00000000-0000-0000-0000-000000000004` | 停止 三郎 | 利用停止(注文できない) |

1. **注文画面**(`/orders/`)で会員 ID と数量を入れて注文する → ステータスは「受付済」
2. **キッチン画面**(`/kitchen/`)にチケットが出る。「調理開始」→ 注文画面のステータスが「調理中」になる(この時点でキャンセルはできない)
3. キッチン画面で「調理完了」→ 注文が「受取可」になる
4. 注文画面で「受取」→ 「受取済」。管理サイトで会員のポイントが増えている(100 円につき 1 ポイント)
5. **在庫管理画面**(`/inventory/`)で、スコーン(10 個)・ホットサンド(3 個)のキットが減っているのを確認する。ホットサンドを 4 個注文しようとすると在庫不足で断られ、残りを全部予約で確保すると注文画面から消える(在庫切れ)。予約を取り消すと注文画面に戻る

## テスト

```bash
uv run python manage.py test shared ordering kitchen menu customers inventory config
```

ドメイン層のテスト(`*/tests/test_domain/`)は DB を使わない素の `unittest.TestCase`。ルールは時刻に依存しないので、日付の差し替えは要らない。

モジュール間の依存ルール(他モジュールの内部を import しない、ドメイン層は Django に依存しない)は import-linter で機械的にチェックする。

```bash
uv run lint-imports
```
