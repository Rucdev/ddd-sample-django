# ディレクトリ構成

Django でモジュラモノリスを構成し、**DDD ベースのアプリ**と**通常の CRUD アプリ**を同居させるための構成。

題材は**カフェのモバイルオーダー**(注文 → 調理 → 受取)。コンテキストの一覧と関係は [CONTEXT-MAP.md](../CONTEXT-MAP.md)、各コンテキストの用語集は `<context>/CONTEXT.md` を参照。

アプリは Django 標準の流儀に従い**プロジェクトルート直下にフラットに配置**する(`startapp` がそのまま使え、読者にも馴染みやすいため)。モジュール境界はディレクトリの入れ子ではなく、後述の「モジュール間のルール」で守る。

## 方針

- **1 Django アプリ = 1 モジュール**とする。DDD ベースのアプリは境界づけられたコンテキスト(Bounded Context)に対応させる。
- 複雑なドメインを持つモジュールだけ DDD のレイヤードアーキテクチャを採用し、マスタ管理などの単純なモジュールは Django 標準の CRUD 構成のままにする。**すべてを DDD にしない**ことが前提。
- モジュール間の依存は「公開された入口」経由に限定し、内部実装(モデル・リポジトリ実装など)への直接依存を禁止する。

## 全体構成

```
ddd-sample-django/
├── manage.py
├── pyproject.toml
├── config/                     # プロジェクト設定(settings / urls / wsgi / asgi)
│   ├── settings.py
│   └── urls.py
├── docs/                       # 設計ドキュメント
├── shared/                     # 共有カーネル(全モジュールから利用可)
│   ├── domain/                 # Entity / ValueObject / DomainEvent などの基底クラス
│   │   ├── entity.py
│   │   ├── value_object.py
│   │   └── event.py
│   └── infrastructure/
│       └── event_bus.py        # モジュール間のイベント伝搬(同期ディスパッチで開始)
├── ordering/                   # DDD: 注文コンテキスト(注文・キャンセル・受取・金額計算)
├── kitchen/                    # DDD: キッチンコンテキスト(調理チケットの進行)
├── menu/                       # CRUD: メニューマスタ(カテゴリ・商品)
├── customers/                  # CRUD: 会員マスタ(ランク・ポイント)
└── inventory/                  # CRUD: キットの在庫(入出庫・予約・在庫ログ)
```

## DDD ベースのアプリの構成

```
ordering/
├── __init__.py
├── apps.py                     # AppConfig(name = "ordering")。ready() でイベント購読を登録
├── models.py                   # infrastructure/models.py の再エクスポートのみ
├── migrations/                 # Django 標準の位置に置く(移動しない)
├── domain/                     # ドメイン層 —— Django に依存しない純粋な Python
│   ├── __init__.py
│   ├── entities.py             # エンティティ・集約ルート
│   ├── value_objects.py        # 値オブジェクト
│   ├── events.py               # ドメインイベント
│   ├── exceptions.py           # ドメイン例外
│   ├── repositories.py         # リポジトリの抽象(Protocol / ABC)
│   └── services.py             # ドメインサービス
├── application/                # アプリケーション層 —— ユースケースの実装
│   ├── __init__.py
│   ├── use_cases/              # 1 ユースケース 1 ファイル(コマンド側)
│   │   ├── place_order.py
│   │   ├── cancel_order.py
│   │   └── pick_up_order.py
│   ├── queries.py              # 参照系(CQRS の Q。ORM 直読みを許可、QuerySet を返してよい)
│   └── dto.py                  # 入出力 DTO
├── infrastructure/             # インフラ層 —— Django / 外部サービスへの依存を隔離
│   ├── __init__.py
│   ├── models.py               # Django ORM モデル(永続化モデル)
│   ├── repositories.py         # リポジトリ抽象の実装(ORM ⇔ エンティティ変換)
│   └── event_handlers.py       # 他モジュールのドメインイベントのハンドラ
├── presentation/               # プレゼンテーション層
│   ├── __init__.py
│   ├── views.py                # 画面 View。ユースケースを呼ぶだけの薄い層
│   ├── forms.py                # 画面入力の形式バリデーション(Django Form)
│   ├── api.py                  # API View(コマンドは APIView、参照は ListAPIView も可。ViewSet は使わない)
│   ├── filters.py              # 参照 API の絞り込み条件(django-filter の FilterSet)
│   ├── serializers.py          # API 入出力の形式バリデーション(素の Serializer)
│   └── urls.py                 # このモジュールの URL 定義(画面 + API)
├── templates/                  # 画面テンプレート(Django の規約どおりアプリ直下)
│   └── ordering/               # 名前空間用にアプリ名ディレクトリを挟む
│       └── order_list.html
├── public.py                   # 他モジュールへの公開 API(モジュールの唯一の入口)
└── tests/
    ├── test_domain/            # ドメイン層のテスト(DB 不要・高速)
    ├── test_application/
    └── test_presentation/
```

### 各層の責務と依存方向

依存は必ず内側(domain)に向ける。

```
presentation ──▶ application ──▶ domain ◀── infrastructure
```

| 層 | 責務 | 依存してよいもの |
| --- | --- | --- |
| domain | ビジネスルール。エンティティ・値オブジェクト・ドメインイベント | shared/domain のみ(**Django 禁止**) |
| application | ユースケースのオーケストレーション。トランザクション境界 | domain(リポジトリは抽象経由で利用) |
| infrastructure | ORM モデル、リポジトリ実装、外部 API クライアント | domain, Django |
| presentation | HTTP の入出力変換。認証・バリデーション | application, Django |

### DDD と Django の接続面

DDD のレイヤと Django のフレームワーク機能が触れ合う箇所と、それぞれの方針。

#### モデルとマイグレーション

- **models.py**: Django はアプリ直下の `models.py` からモデルを検出するため、直下の `models.py` に `from .infrastructure.models import *  # noqa` と書いて再エクスポートする。実体は `infrastructure/models.py` に置く。
- **migrations/**: `MIGRATION_MODULES` で移動もできるが、標準の位置に置いたほうがトラブルが少ない。
- **ドメインモデルと ORM モデルの分離**: ドメイン層のエンティティと ORM モデルは別クラスとして定義し、リポジトリ実装が相互変換する。二重定義のコストはかかるが、DDD サンプルとしてはここを分離するのが主眼。
- **参照系(queries.py)は ORM 直読みを許可**: 一覧表示のためだけにエンティティを組み立てるのは過剰なので、参照系はリポジトリを通さず ORM → DTO で返してよい。計算ルールが絡まない参照は DTO にもせず `QuerySet` を返してよい(kitchen。[ADR-0003](./adr/0003-query-side-uses-drf-generics-and-django-filter.md))。

#### 画面(テンプレートと Form)

- DDD アプリも普通に **Django テンプレートで画面を提供する**。画面は presentation 層の一部であり、DDD だから API 専用ということはない。
- **templates/ はアプリ直下**に置く(`ordering/templates/ordering/…`)。presentation 配下に置くことも `DIRS` 設定で可能だが、migrations と同じく Django の規約(`APP_DIRS` ローダ)に従うほうがトラブルが少ない。
- **Django Form は presentation 層の道具**として使う。担当は「入力の形式チェック」(必須・型・日付フォーマットなど)まで。Form が valid になったら `cleaned_data` をユースケースの入力 DTO に詰め替えて渡す。
- **ModelForm は DDD アプリでは使わない**。ModelForm は画面と ORM モデルを直結させる道具であり、ユースケースを迂回してしまう。CRUD アプリでは逆に積極的に使ってよい。
- テンプレートに渡すのは queries.py が返す **DTO**(または dict)。エンティティをテンプレートに直接渡さない。ORM モデルは、計算ルールが絡まない参照系に限り `QuerySet` のまま渡してよい(ADR-0003)。

#### API(DRF の限定利用)

DDD アプリも API を公開する。API は画面と並ぶ presentation 層の一形態であり、ユースケースを呼ぶだけという点は画面 View と同じ。

- API フレームワークは **DRF を採用**する。理由は、CRUD アプリに API 連携が生えたとき `ModelViewSet` / `ModelSerializer` が最も安く効く領域であり、そのときに API スタック(認証・例外変換・ページネーション)をプロジェクトで一本化しておきたいため。
- ただし **DDD アプリでは DRF を限定利用**する。使ってよいのは `APIView`(または `@api_view`)と**素の `Serializer`** まで。
  - **`ModelSerializer` / `ModelViewSet` / ルーターは DDD アプリでは禁止**。ORM モデルと API を直結させ、ユースケースを迂回する道具だから(ModelForm を禁止するのと同じ理由)。CRUD アプリでは逆に主力として使ってよい。
  - **参照系(CQRS の Q)は例外**で、読み取り専用の汎用 View(`ListAPIView` / `RetrieveAPIView`)と django-filter の `FilterSet` を使ってよい。参照系はもともとユースケースを通らないので、迂回の問題が起きない([ADR-0003](./adr/0003-query-side-uses-drf-generics-and-django-filter.md))。Serializer は参照系でも素の `Serializer` を使う。
- Serializer の担当は Form と同じく**形式チェックまで**。`validated_data` をユースケースの入力 DTO に詰め替えて渡し、レスポンスは出力 DTO を dict 化して返す。エンティティや ORM モデルを直接シリアライズしない。
- ドメイン例外 → HTTP ステータスの変換は DRF の **custom exception handler** に一元化する(例: `TooManyInProgressOrders` → 409)。画面系の messages 変換と役割は同じで、ビジネスルール違反を 500 にしない。

```python
# presentation/api.py
class CancelOrderAPIView(APIView):
    def post(self, request, order_id):
        use_case = CancelOrderUseCase(order_repository=DjangoOrderRepository())
        result = use_case.execute(CancelOrderInput(order_id=order_id))
        return Response(OrderSerializer(result).data)
```

#### バリデーションの役割分担

| どこで | 何を検証する | 例 |
| --- | --- | --- |
| presentation(Form / Serializer) | 入力の形式 | 会員 ID が UUID として解釈できるか、数量が整数か |
| domain(エンティティ・値オブジェクト) | ビジネスルール | 数量が 1〜10 個か、調理開始後のキャンセルでないか |

ドメイン例外(`domain/exceptions.py`)は presentation 層で捕まえ、フォームエラーやメッセージ(`django.contrib.messages`)に変換して画面に返す。ビジネスルール違反を HTTP 500 にしない。

#### URL ルーティング

- 各モジュールの `presentation/urls.py`(CRUD アプリは `urls.py`)に `app_name` を付けて名前空間化し、`config/urls.py` が `include()` で束ねる。

```python
# config/urls.py
urlpatterns = [
    path("orders/", include("ordering.presentation.urls")),
    path("kitchen/", include("kitchen.presentation.urls")),
]
```

#### Django admin

- **CRUD アプリでは admin を主戦力にする**。マスタ管理は admin で完結してよい。
- **DDD アプリでは admin に書き込みをさせない**。admin は ORM モデルを直接更新するため、集約の不変条件やドメインイベントを素通りしてしまう。使うなら閲覧専用(`has_add/change/delete_permission` を False)にとどめ、状態を変える操作は必ず画面 → ユースケース経由にする。

#### 認証と会員

- ログイン認証は `django.contrib.auth` に任せる。**`User` は「認証情報」、customers の「会員」は「カフェのドメインの登場人物」**として分ける。会員(`Customer`)は `user` への OneToOne を持つが、これは customers モジュール内に閉じた参照で、他モジュールは会員 ID(値)だけを扱う。
- `request.user` を domain / application 層に持ち込まない。presentation 層で `request.user` → 会員 ID に解決し、ユースケースには会員 ID を渡す。

#### ユースケースの組み立て(依存の注入)

- ユースケースはコンストラクタでリポジトリ抽象を受け取る。組み立て(具象の注入)は presentation 層の担当とし、DI コンテナは使わず**ビュー(またはモジュールごとのファクトリ関数)で手で組む**。サンプルとしては仕掛けが見えるほうがよい。

```python
# presentation/views.py
def place_order_view(request):
    use_case = PlaceOrderUseCase(order_repository=DjangoOrderRepository())
    ...
```

- テストではフェイクリポジトリ(インメモリ実装)を渡すことで、DB なしでユースケースまで検証できる。

#### ドメインイベントと Django signals

- モジュール間の連携は **`shared/infrastructure/event_bus.py` のドメインイベントを使い、Django signals は使わない**。signals は発火元が ORM 操作(save/delete)に紐づくため、「何が起きたか」ではなく「どのテーブルが書かれたか」しか表現できない。
- イベントハンドラの購読登録は各モジュールの **`apps.py` の `AppConfig.ready()`** で行う。Django のアプリ初期化フックを配線ポイントとして使う。

#### トランザクション境界

- ユースケース内で `transaction.atomic()` を張る。domain 層には持ち込まない。
- 同期ディスパッチのイベントハンドラも同一トランザクションに入る(サンプルでは単純さを優先)。分離したくなったら `transaction.on_commit()` や非同期化を検討する。

## CRUD アプリの構成

複雑なビジネスルールを持たないモジュールは Django 標準構成のまま。

```
menu/
├── __init__.py
├── apps.py
├── models.py
├── views.py                    # 画面。API を生やすときは ModelViewSet も可
├── forms.py                    # ModelForm を積極的に使ってよい
├── serializers.py              # API を生やすときは ModelSerializer も可
├── admin.py                    # CRUD アプリでは admin が主戦力
├── urls.py
├── public.py                   # 他モジュールへの公開 API(DDD アプリと同じ規約)
├── migrations/
└── tests.py
```

CRUD アプリでも、守るべきルールを持つ更新操作がある場合は `services.py` にまとめ、画面・API・`public.py`・イベントハンドラはそれを呼ぶだけにする(例: inventory。在庫数の条件付き UPDATE・在庫ログ・在庫切れの反映を 1 トランザクションで行う)。その場合、admin や `ModelSerializer` では該当フィールドを読み取り専用にし、`create` / `update` を services に向ける。

## モジュール間のルール

モジュラモノリスの肝。DDD アプリ・CRUD アプリ共通で以下を守る。

1. **他モジュールの内部を import しない**
   - NG: `from menu.models import MenuItem`(他モジュールから)
   - OK: `from menu.public import get_menu_item`
2. **`public.py` がモジュールの唯一の公開面**。関数と DTO(dataclass)だけを公開し、ORM モデルやエンティティをそのまま返さない。
3. **DB レベルの結合を避ける**: モジュールをまたぐ ForeignKey は張らず、ID(値)のみ保持する。
4. **結果整合でよい連携はドメインイベント経由**にする(`shared/infrastructure/event_bus.py`)。まずは同期ディスパッチで実装し、必要になったら非同期(Celery 等)に差し替える。
5. **依存ルールは import-linter で機械的に強制する**(`pyproject.toml` の `[tool.importlinter]`)。各モジュールを `forbidden` contract で「他モジュールからは `public.py`(と、イベントを購読する側からの `domain.events`)以外 import 禁止」とし、`ordering.domain` / `kitchen.domain` / `shared.domain` が Django を import しない contract も追加している。フラット配置のため共通プレフィックスはないが、モジュール名を列挙した contract で同等のチェックができる。テストのフィクスチャ(他モジュールの `models` を直接使って前提データを作る)は `ignore_imports` で明示的に許容し、本番コードのみを対象にする。`uv run lint-imports` で実行できる。

## settings.py での登録

```python
INSTALLED_APPS = [
    # django標準アプリ...
    "rest_framework",
    "ordering",
    "kitchen",
    "menu",
    "customers",
    "inventory",
]
```

## DDD にするか CRUD にするかの判断基準

| DDD ベースにする | CRUD のままにする |
| --- | --- |
| 状態遷移や不変条件が多い(注文・調理の進行、金額計算など) | 単純な登録・参照・更新(メニュー・会員マスタ) |
| ドメインエキスパートとの会話に固有の語彙がある | 画面と DB がほぼ 1:1 |
| ビジネスルールのテストを DB なしで書きたい | Django admin で十分運用できる |
