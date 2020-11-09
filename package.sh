#!/bin/bash
script_name="pycodesign"

tar cvzf $script_name.tgz ./$script_name.py

git commit -m "refresh tgz" $script_name.tgz
git push
