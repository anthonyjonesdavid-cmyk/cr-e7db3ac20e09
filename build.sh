#!/bin/sh
# Rebuilds the single-file index.html from src/ (no dependencies needed).
cd "$(dirname "$0")"
{ cat src/head.html; echo '<style>'; cat src/style.css; echo '</style>'; echo '</head>'; cat src/body.html;
  echo '<script type="module">'; cat src/config.js src/core.js src/shelf.js src/drive.js src/reader.js src/boot.js; echo '</script>'; echo '</body>'; echo '</html>'; } > index.html
echo "built index.html ($(wc -c < index.html) bytes)"
