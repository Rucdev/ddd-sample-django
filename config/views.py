from django.shortcuts import render
from django.views.static import serve

# アップロードされたファイル(MEDIA)を配信するときに付けるヘッダ。万一スクリプト入りの
# ファイル(SVG・HTML など)が置かれていても、URL を直接開かれたときにスクリプトを動かさない。
# - sandbox: 別オリジン扱いにしてスクリプトを止める(Cookie や CSRF トークンに触れない)
# - default-src 'none': 外部リソースも読ませない(SVG 内のインライン style だけ許す)
# <img> で表示する分にはもともとスクリプトは動かないので、画面の見た目には影響しない。
# 本番で Web サーバ(nginx 等)から MEDIA を配信する場合は、同じヘッダをそちらで付けること。
MEDIA_SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; sandbox",
    "X-Content-Type-Options": "nosniff",
}


def home_view(request):
    return render(request, "home.html")


def serve_media(request, path, document_root=None):
    """開発サーバ用の MEDIA 配信。django.views.static.serve に安全用のヘッダを足すだけ。"""
    response = serve(request, path, document_root=document_root)
    for header, value in MEDIA_SECURITY_HEADERS.items():
        response[header] = value
    return response
