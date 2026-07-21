# API は DRF を採用するが、DDD アプリでは限定利用にとどめる

API フレームワークとして DRF を採用する。ただし DDD アプリで使ってよいのは `APIView` と素の `Serializer` までとし、`ModelSerializer` / `ModelViewSet` / ルーターは CRUD アプリ専用とする。ORM モデルと API を直結させる道具はユースケースを迂回してしまうためで、ModelForm を DDD アプリで禁止しているのと同じ理由。

## Considered Options

- **素の Django のみ**(`json.loads` + Form + `JsonResponse`): 依存ゼロで仕掛けが見えるが、CRUD アプリに API 連携が生えたとき最も DRF が効く領域を手書きすることになり、そこで DRF を入れると API スタック(認証・例外変換・ページネーション)が二本化する。
- **django-ninja**: Pydantic スキーマ = DTO の発想は DDD と好相性だが、依存が増え Django 標準の流儀から離れる。
- **DRF 限定利用(採用)**: 将来の CRUD API に `ModelViewSet` がそのまま効き、スタックを一本化できる。「同じフレームワークをアプリの性格で使い分ける」形が ModelForm の使い分けと相似形で、サンプルとしても一貫する。

## Consequences

- ドメイン例外 → HTTP ステータスの変換は DRF の custom exception handler に一元化する。
- DDD アプリの Serializer は形式チェックのみを担い、`validated_data` はユースケースの入力 DTO に詰め替える。エンティティ・ORM モデルを直接シリアライズしない。
