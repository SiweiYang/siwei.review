#!/usr/bin/env bash
jekyll build && gsutil -m -o rsync -r _site/ gs://siwei.review
