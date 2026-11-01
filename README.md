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
| [kitchen](kitchen/CONTEXT.md) | DDD | 注文明細ごとの調理チケットの進行(調理待ち → 調理中 → 調理済) |
| [menu](menu/CONTEXT.md) | CRUD | カテゴリ・商品のマスタ管理 |
| [customers](customers/CONTEXT.md) | CRUD | 会員のマスタ管理、会員ランク・ポイント |
| [seating](seating/CONTEXT.md) | DDD | 座席構成ファイル(YAML)から席を作り、空き・予約中・使用中を管理する |

`shared/` は全モジュールが利用できる共有カーネル(Entity / ValueObject / DomainEvent の基底クラスと、モジュール間イベントバス)。

## セットアップ

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py loaddata demo   # デモ用のメニュー・会員を投入
uv run python manage.py apply_seat_layout   # 座席構成ファイル(seating/seat_layout.yaml)を DB に反映
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

1. **注文画面**(`/orders/`)で会員 ID と数量を入れて注文する(ドリンクとフードなど複数の商品を頼むと分かりやすい)→ ステータスは「受付済」
2. **キッチン画面**(`/kitchen/`)に商品ごとのチケットが出る(「1/2」は 2 品中 1 品目)。どれか 1 枚を「調理開始」→ 注文画面のステータスが「調理中」になる(この時点でキャンセルはできない)
3. チケットは商品ごとにばらばらに進めてよい。注文画面には「1/2 品できあがり」のように出て、全部「調理完了」すると注文が「受取可」になる
4. 注文画面で「受取」→ 「受取済」。管理サイトで会員のポイントが増えている(100 円につき 1 ポイント)
5. **座席画面**(`/seating/`)で、空き席を「予約」→「着席」、または予約なしで「案内」すると使用中になり、上の集計と使用率が変わる。「退席」で空きに戻る
6. `seating/seat_layout.yaml` の席を足したり定員を変えたりして `apply_seat_layout` を流し直すと、使用中の席はそのままで構成だけが変わる。使用中の席をファイルから消すと反映ごと断られる

## テスト

```bash
uv run python manage.py test shared ordering kitchen menu customers seating config
```

ドメイン層のテスト(`*/tests/test_domain/`)は DB を使わない素の `unittest.TestCase`。ルールは時刻に依存しないので、日付の差し替えは要らない。

モジュール間の依存ルール(他モジュールの内部を import しない、ドメイン層は Django に依存しない)は import-linter で機械的にチェックする。

```bash
uv run lint-imports
```
