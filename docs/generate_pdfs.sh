#!/usr/bin/env bash

pandoc gse-velocity.md -f gfm -o gse-velocity.pdf --pdf-engine=xelatex -V geometry:margin=1in
