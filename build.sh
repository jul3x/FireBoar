#!/bin/bash

source env/bin/activate
rm -r build

# Generate version info before build so it gets bundled into the app
BUILD_DATE=$(date '+%Y-%m-%d %H:%M:%S')
VERSION=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
cat > fireboar/version.py << EOF
BUILD_DATETIME = "$BUILD_DATE"
VERSION = "$VERSION"
EOF
echo "Building version $VERSION ($BUILD_DATE)"

flet build web
cp -r splash build/web
cp favicon.png build/web
cp assets/beep.mp3 build/web/assets/
cp assets_web/.htaccess build/web/.htaccess

# Cache busting: add no-cache meta tags to index.html
# (Apache .htaccess is the primary mechanism; these are a fallback for CDN edges/proxies
#  that strip response headers. They don't affect the service worker cache, so offline works.)
sed -i "s|<meta charset=\"UTF-8\">|<meta charset=\"UTF-8\">\n  <meta http-equiv=\"Cache-Control\" content=\"no-cache, no-store, must-revalidate\">\n  <meta http-equiv=\"Pragma\" content=\"no-cache\">\n  <meta http-equiv=\"Expires\" content=\"0\">|" build/web/index.html
echo "Cache busting meta tags applied"

# Ask for persistent storage: SharedPreferences on web is localStorage, which is "best-effort"
# by default and Chrome may evict it under storage pressure. An installed PWA is usually
# granted persistence automatically. Does not protect against manual "clear site data".
sed -i "s|</head>|  <script>if (navigator.storage \&\& navigator.storage.persist) navigator.storage.persist();</script>\n</head>|" build/web/index.html
echo "Persistent storage request applied"

