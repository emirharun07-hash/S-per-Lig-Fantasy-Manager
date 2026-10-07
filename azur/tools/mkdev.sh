#!/bin/sh
# wraps the artifact page into a full document for local testing
P=/home/user/S-per-Lig-Fantasy-Manager/azur/prototype
{ echo '<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"></head><body>'; cat $P/index.html; echo '</body></html>'; } > $P/_dev.html
