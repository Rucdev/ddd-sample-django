# ddd-sample-django

Django でモジュラモノリスを構成し、**DDD ベースのモジュール**と**通常の CRUD モジュール**を同居させるサンプルプロジェクト。題材は図書館の貸出管理システム。

設計の詳細は以下を参照:

- [docs/directory-structure.md](docs/directory-structure.md) — ディレクトリ構成、レイヤ責務、DDD と Django の接続面のルール
- [CONTEXT-MAP.md](CONTEXT-MAP.md) — コンテキスト(モジュール)一覧とモジュール間の関係
- 各モジュールの `CONTEXT.md`(`lending/CONTEXT.md` など) — ドメイン用語集
- [docs/adr/](docs/adr/) — アーキテクチャ上の決定記録
- [docs/implementation-plan.md](docs/implementation-plan.md) — フェーズごとの実装計画

## モジュール一覧

| モジュール | 種類 | 役割 |
| --- | --- | --- |
| [lending](lending/CONTEXT.md) | DDD | 貸出・返却・延長・延滞 |
| [reservation](reservation/CONTEXT.md) | DDD | 予約待ち行列・取置 |
| [catalog](catalog/CONTEXT.md) | CRUD | 書誌・蔵書(個体)のマスタ管理 |
| [members](members/CONTEXT.md) | CRUD | 会員のマスタ管理 |

`shared/` は全モジュールが利用できる共有カーネル(Entity / ValueObject / DomainEvent の基底クラスと、モジュール間イベントバス)。

## セットアップ

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

起動したら `http://127.0.0.1:8000/` がトップページ(各画面へのリンク)、`/admin/` が管理サイト。

## テスト

```bash
uv run python manage.py test shared lending reservation catalog members config
```

モジュール間の依存ルール(他モジュールの内部を import しない、ドメイン層は Django に依存しない)は import-linter で機械的にチェックする。

```bash
uv run lint-imports
```

## 定期実行系のコマンド

- `uv run python manage.py detect_overdue` — 返却期限を過ぎた貸出を延滞にし、`LoanOverdue` イベントを発行する
- `uv run python manage.py expire_holds` — 期限切れの取置を解除し、次の予約者がいれば取置を引き継ぐ

本来は cron 等で定期実行する想定(このサンプルには定期実行の仕組み自体は含まれていない)。
