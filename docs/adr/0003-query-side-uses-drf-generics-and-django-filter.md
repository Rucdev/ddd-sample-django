# 参照系(CQRS の Q)では DRF の汎用 View と django-filter を使ってよい

DDD アプリの参照 API は `ListAPIView` などの DRF 汎用 View と django-filter の `FilterSet` で組んでよい。ADR-0001 が `ModelViewSet` などを禁止した理由は「ユースケースを迂回してしまう」ことだったが、参照系はもともとユースケースもリポジトリも通らない(`queries.py` は ORM 直読み)ので、この理由が当てはまらない。参照系にまで同じ禁止をかけると、絞り込み条件が増えるたびに `queries.py` へ関数を手で足していくことになる。

まず kitchen のチケット一覧に適用した。ordering の注文一覧は、金額(小計・割引・合計)がドメイン層で計算されていて DB に列がないため、そのままでは移せない。金額を保存時に列として書き込むかどうかを決めてから移行する。

## Considered Options

- **ADR-0001 のまま(APIView + 手書きの queries 関数)**: DRF の仕組みが見えやすいが、絞り込み・並び替え・ページングを条件の組み合わせごとに手で書くことになる。
- **参照系だけ DRF 汎用 View + django-filter(採用)**: クエリパラメータの検証と `QuerySet.filter()` への変換を宣言だけで済ませられる。コマンド側の制約(ADR-0001)はそのまま残る。

## Consequences

- `queries.py` は DTO ではなく `QuerySet` を返す。絞り込み条件は `presentation/filters.py` の `FilterSet` に書く。
- 汎用 View を使ってよいのは**読み取り専用**のもの(`ListAPIView` / `RetrieveAPIView`)だけ。更新系の汎用 View(`CreateAPIView`、`ModelViewSet` など)は引き続き DDD アプリでは禁止する。
- `ModelSerializer` は使わず、素の `Serializer` を参照とコマンド応答の両方で使う。ORM のスキーマが変わっても API のレスポンス形が勝手に変わらないようにするためと、一覧と更新結果のレスポンス形を揃えるため。
- 参照系に限り、テンプレートに ORM モデル(`QuerySet`)を渡してよい。表示に計算ルールが絡む場合は、これまでどおりエンティティ経由で DTO にする。
- 依存パッケージに `django-filter` が加わる。
