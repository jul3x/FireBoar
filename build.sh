#!/bin/bash

source env/bin/activate
rm -r build
flet build web
cp -r splash build/web
cp favicon.png build/web
cp assets/beep.mp3 build/web/assets/

