# 実装計画

図書館の貸出管理システム(モジュラモノリス、DDD + CRUD 同居)の実装計画。

**前提資料**(実装前に必読):

- [directory-structure.md](./directory-structure.md) — ディレクトリ構成、レイヤ責務、DDD と Django の接続面のルール
- [CONTEXT-MAP.md](../CONTEXT-MAP.md) — コンテキスト一覧とモジュール間関係
- 各モジュールの `CONTEXT.md` — 用語集(コード内の命名はここに従う)
- [ADR-0001](./adr/0001-drf-limited-use.md) — DRF の限定利用ルール

**ドメインの仕様値**(各 CONTEXT.md より):

- 貸出上限: 同時 5 冊 / 返却期限: 貸出日から 14 日 / 延長: 1 回まで、延滞中・対象書誌に予約ありの場合は不可
- 取置期限: 取置成立から 7 日 / 延滞発生 → 会員停止、延滞中の貸出がすべて返却されたら停止解除

**共通ルール**:

- テストは Django 標準のテストランナー(`python manage.py test`)を使う。追加依存を増やさない。
- domain 層のテストは DB 不要で書く(`SimpleTestCase` または素の `unittest.TestCase`)。
- 各フェーズの完了条件: そのフェーズのテストが全部通り、`python manage.py migrate && python manage.py runserver` が動くこと。
- コミットはフェーズ内のステップごとに分ける。

---

## Phase 0: 基盤整備

1. **依存追加**: `uv add djangorestframework`
2. **settings.py**: `INSTALLED_APPS` に `rest_framework` を追加。`TEMPLATES` の `APP_DIRS: True` を確認。
3. **共有カーネル `shared/` を作成**(Django 非依存の純粋 Python。Django アプリにはしない):
   - `shared/domain/entity.py` — `Entity` 基底クラス(ID による同一性)。集約ルートが発行したドメインイベントを溜める `record_event()` / `collect_events()` を持たせる
   - `shared/domain/value_object.py` — `ValueObject` 基底(frozen dataclass ベース、値による等価性)
   - `shared/domain/event.py` — `DomainEvent` 基底(発生時刻を持つ frozen dataclass)
   - `shared/infrastructure/event_bus.py` — 同期イベントバス。`subscribe(event_type, handler)` / `publish(events)` のモジュールレベル関数。ハンドラ内の例外は握りつぶさずそのまま伝播させる(同一トランザクションでロールバックさせるため)
4. **shared のテスト**: `shared/tests/` にイベントバスの購読・発行、Entity の等価性のテスト
5. **`config/settings.py` にテスト実行確認**: `python manage.py test shared`

## Phase 1: CRUD アプリ(catalog / members)

Django 標準構成。DDD の作法は持ち込まない(directory-structure.md「CRUD アプリの構成」参照)。

1. `python manage.py startapp catalog` / `startapp members`(既存の `CONTEXT.md` があるディレクトリに生成する。`startapp` が拒否する場合は一時退避して戻す)
2. **catalog のモデル**(`catalog/models.py`):
   - `Title` — 書誌。`name`, `author`, `isbn`
   - `Copy` — 蔵書(個体)。`title = FK(Title)`(同一モジュール内なので FK 可)、`copy_number`, `status`(`ACTIVE` 所蔵中 / `WITHDRAWN` 除籍。TextChoices)
3. **members のモデル**(`members/models.py`):
   - `Member` — 会員。`name`, `email`, `user = OneToOneField(settings.AUTH_USER_MODEL, null=True)`(認証は auth に委譲。同一モジュール扱いなので FK 可)、`status`(`ACTIVE` 有効 / `SUSPENDED` 停止)
4. **admin 登録**: 両アプリとも admin を主戦力にする。一覧・検索・フィルタを設定
5. **public.py**(他モジュールへの公開面。dataclass の DTO を返し、ORM モデルを返さない):
   - `catalog/public.py` — `get_copy(copy_id) -> CopyDTO | None`(書誌名・所蔵状態を含む)、`get_title(title_id) -> TitleDTO | None`
   - `members/public.py` — `get_member(member_id) -> MemberDTO | None`、`suspend_member(member_id)`、`reinstate_member(member_id)`
6. **migrations 作成・テスト**: モデルと public.py のテストを書く(`tests.py` で可)

## Phase 2: lending(DDD コア)

directory-structure.md「DDD ベースのアプリの構成」のレイヤ構成に従う。**このフェーズでは reservation は存在しない**ため、予約に関わるチェックは「予約なし」を返すスタブ関数を application 層に置き、Phase 3 で差し替える(TODO コメントを残す)。

1. アプリ雛形: `startapp lending` 後、`domain/` `application/` `infrastructure/` `presentation/` `templates/lending/` `tests/` を作る。直下 `models.py` は `from .infrastructure.models import *  # noqa` のみ
2. **domain 層**(Django import 禁止):
   - `entities.py` — `Loan` 集約ルート。`loan_id`, `member_id`, `copy_id`, `loaned_at`, `due_date`, `returned_at`, `renewal_count`。振る舞い: `return_book()`, `renew(has_reservation: bool)`(1 回まで・延滞中不可・予約あり不可)、`is_overdue(today)`, `mark_overdue()`。状態変更時に対応イベントを `record_event()`
   - `value_objects.py` — `LoanPeriod`(標準 14 日、due date 算出)
   - `events.py` — `BookLoaned`, `BookReturned`, `LoanOverdue`(member_id / copy_id / loan_id を運ぶ)
   - `exceptions.py` — `LoanLimitExceeded`, `RenewalNotAllowed`, `MemberNotLoanable`, `CopyNotLoanable`, `AlreadyReturned`
   - `repositories.py` — `LoanRepository` Protocol: `save`, `find_by_id`, `count_active_by_member`, `count_overdue_by_member`, `find_active_by_copy`
   - `services.py` — `LoanPolicy`: 貸出可否判定(上限 5 冊チェックなど、リポジトリの count を使う判定)
3. **infrastructure 層**: `models.py` に `LoanModel`(member_id / copy_id は FK ではなく UUID/整数カラム。**モジュール間 FK 禁止**)。`repositories.py` に `DjangoLoanRepository`(ORM ⇔ `Loan` エンティティ変換)
4. **application 層**:
   - `dto.py` — 入出力 DTO(`LoanBookInput`, `LoanDTO` など)
   - `use_cases/loan_book.py` — 会員有効チェック(`members.public`)→ 蔵書所蔵中チェック(`catalog.public`)→ 貸出中でないか → 上限チェック(`LoanPolicy`)→ 取置チェック(スタブ)→ `Loan` 生成・保存 → イベント発行。全体を `transaction.atomic()` で包む
   - `use_cases/return_book.py` / `use_cases/renew_loan.py` — 同様の構え。renew は書誌への予約有無(スタブ)を bool で domain に渡す
   - `queries.py` — 貸出一覧・会員別貸出(ORM 直読み → DTO)
5. **presentation 層**:
   - 画面: 貸出一覧(`loan_list.html`)、貸出登録フォーム、返却・延長ボタン。Form は形式チェックのみ、ドメイン例外は捕まえて `messages` へ
   - API: `api.py` に `APIView` で `POST /api/loans`, `POST /api/loans/<id>/return`, `POST /api/loans/<id>/renew`, `GET /api/loans`。素の `Serializer` のみ使用(ADR-0001)
   - ドメイン例外 → HTTP の変換: `shared/infrastructure/exception_handler.py` に DRF custom exception handler を作り settings に登録(`LoanLimitExceeded` 等 → 409、`NotFound` 系 → 404)
   - `urls.py`(`app_name = "lending"`)を作り `config/urls.py` に `include`
6. **延滞検出**: management command `detect_overdue`(`lending/management/commands/`)。期限超過かつ未返却の貸出に `mark_overdue()` → `LoanOverdue` 発行。冪等にする(検出済みフラグ `overdue_notified` を持たせる)
7. **public.py**: `count_overdue_loans(member_id) -> int`(Phase 4 で members の停止解除判定に使う)
8. **テスト**: domain 単体(DB なしで上限・延長・延滞ルール)/ application(インメモリのフェイクリポジトリで各ユースケース)/ presentation(test client で画面・API の正常系 + ドメイン例外 → 4xx)

## Phase 3: reservation(DDD)

lending と同じレイヤ構成。

1. **domain 層**:
   - `entities.py` — `ReservationQueue` 集約ルート(`title_id` 単位)。予約(`member_id`, 申込順)のリストと取置(`Hold`: `copy_id`, `member_id`, `expires_at`)を保持。振る舞い: `add_reservation(member_id)`(同一会員の重複予約は不可)、`cancel(member_id)`、`assign_hold(copy_id, today)`(先頭の予約を取置に変換、期限 = 7 日後)、`expire_holds(today)`(失効 → 次の予約者へ、いなければ取置消滅)
   - `events.py` — `HoldReady`, `HoldExpired`
   - `exceptions.py`, `repositories.py`(`ReservationQueueRepository`)
2. **infrastructure 層**: `ReservationModel` / `HoldModel`(title_id / member_id / copy_id は ID カラム)。リポジトリが `ReservationQueue` を組み立てる
3. **application 層**: `reserve_title`(会員有効チェック + 貸出中の書誌のみ予約可)、`cancel_reservation`、`expire_holds`(management command `expire_holds` から呼ぶ)、`queries.py`(予約一覧)
4. **イベント購読**: `apps.py` の `ready()` で `BookReturned` を購読 → 返却された copy の書誌に予約待ちがいれば `assign_hold` → `HoldReady` 発行
5. **public.py**: `get_active_hold_for_copy(copy_id) -> HoldDTO | None`、`has_reservation(title_id) -> bool`
6. **lending のスタブ差し替え**: Phase 2 で置いた取置チェック・予約有無チェックを `reservation.public` 呼び出しに置換(取置中の蔵書は対象会員のみ貸出可 / 予約ありの書誌は延長不可)。lending のテストに連携ケースを追加
7. **presentation**: 予約一覧画面 + `POST /api/reservations`, `DELETE /api/reservations/<id>` 最小限
8. **テスト**: domain(待ち行列順序・取置期限)/ application / BookReturned → 取置のイベント連携テスト

## Phase 4: モジュール間連携の仕上げと固め

1. **members のイベント購読**(`members/apps.py` の `ready()`):
   - `LoanOverdue` → `suspend_member`
   - `BookReturned` → `lending.public.count_overdue_loans(member_id)` が 0 なら `reinstate_member`
   - モジュール間連携の結合テスト(延滞 → 停止 → 全返却 → 解除、返却 → 取置 → 期限切れ → 次の予約者)
2. **トップページ**: 各画面への簡易ナビ(`config` 直下または shared のテンプレートで可)
3. **import-linter 導入**: `uv add --dev import-linter`。契約:
   - 各モジュール(lending / reservation / catalog / members)は他モジュールの `public` 以外を import 禁止(forbidden contract をモジュール名列挙で)
   - `lending.domain` / `reservation.domain` / `shared.domain` は `django` を import 禁止
   - CI 相当として `lint-imports` をテスト手順に追記
4. **README 更新**: プロジェクト概要、セットアップ手順(`uv sync` → `migrate` → `createsuperuser` → `runserver`)、ドキュメントへのリンク、モジュール一覧
5. **最終確認**: 全テスト + `lint-imports` + 手動シナリオ(会員登録 → 蔵書登録 → 貸出 → 予約 → 返却 → 取置 → 延滞 → 停止)

---

## 実装時の注意(ハマりどころ)

- `AppConfig.ready()` でのイベント購読は import 副作用に注意。ハンドラは遅延 import(関数内 import)で循環参照を避ける。
- `startapp` は既存ディレクトリに対して実行できない場合がある。`CONTEXT.md` を一時退避するか、手で雛形を作る。
- イベントバスはモジュールレベルのシングルトン。テストでは `setUp` で購読をリセットできる仕組み(`clear_subscribers()`)を入れておく。
- 同期イベントハンドラはユースケースの `transaction.atomic()` 内で走る。ハンドラ失敗 = 全体ロールバックが今回の仕様(directory-structure.md 参照)。
- ドメインエンティティの ID は UUID を使う(`uuid4` をエンティティ生成時に採番し、ORM 側は `UUIDField(primary_key=True)`)。DB の自動採番に依存すると「保存前のエンティティが ID を持てない」問題に当たる。
