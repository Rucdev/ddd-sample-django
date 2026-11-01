from django.http import HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_exempt


def by_method(**views):
    """同じ URL を HTTP メソッドで参照側とコマンド側の View に振り分ける。

    Django の URL 解決はメソッドを見ないので、`GET /api/orders/` と `POST /api/orders/` を
    別々の path() に書くと先にマッチした方へ両方が流れる。URL はリソースの名前のまま保ち、
    C/Q の分離は View の単位で行うため、重なる URL だけこの関数で 1 か所にまとめる。

    使い方: path("api/orders/", by_method(get=OrderListAPIView.as_view(), post=...))
    """
    allowed = sorted(method.upper() for method in views)

    # DRF の as_view() は csrf_exempt 済み(CSRF は DRF の認証クラスが自前で検査する)。
    # ラッパーで属性が消えると CsrfViewMiddleware に弾かれるので、ここでも付け直す。
    @csrf_exempt
    def dispatch(request, *args, **kwargs):
        method = request.method.lower()
        view = views.get(method) or (views.get("get") if method == "head" else None)
        if view is None:
            return HttpResponseNotAllowed(allowed)
        return view(request, *args, **kwargs)

    return dispatch
