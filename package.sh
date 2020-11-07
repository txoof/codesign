#!/bin/bash

tar cvzf codesign.tgz ./codesign.py

git commit -m "refresh tgz" codesign.tgz
git push
