#!/bin/bash

set -e

l2path() {
    echo "${IMAP_DATA_DIR}/imap/dependency/hit/l2/2026/08/${1}"
}

l3path() {
    echo "${IMAP_DATA_DIR}/imap/dependency/hit/l3/2026/08/${1}"
}

cdfpath() {
    echo "${IMAP_DATA_DIR}/imap/hit/l3/2026/08/${1}"
}

# Base directories for IMAP
IMAP_L3_PROCESSING_DIR=/Users/lw3620/imap/imap_L3_processing
IMAP_PROCESSING_DIR=/Users/lw3620/imap/imap_processing
IMAP_DATA_ACCESS_DIR=/Users/lw3620/imap/imap-data-access

TEST_DIR="$(pwd)/hit_l2_l3_test"
IMAP_DATA_DIR="${TEST_DIR}/imap_data"

rm -rf "$IMAP_DATA_DIR"
mkdir -p "$IMAP_DATA_DIR"

# L2 dependency file names
L2_DEP_OLD="imap_hit_l2_macropixel-intensity-ed398e36-635a606f_20260819_v001.0003.json"
L2_DEP_NEW="imap_hit_l2_macropixel-intensity-test_20260819_v001.0004.json"

# L3 dependency file names
L3_DEP_OLD="imap_hit_l3_macropixel-6bf00ff0-1e59d123_20260819_v001.0005.json"
L3_DEP_NEW="imap_hit_l3_macropixel-test_20260819_v001.0006.json"

# Trusted and test CDFs
TRUSTED_CDF="imap_hit_l3_macropixel_20260819_v001.0005.cdf"
TEST_CDF="imap_hit_l3_macropixel_20260819_v001.0006.cdf"

# First, download all three data files
cd "$IMAP_DATA_ACCESS_DIR"
poetry run imap-data-access download "$L2_DEP_OLD"
poetry run imap-data-access download "$L3_DEP_OLD"
poetry run imap-data-access download "$TRUSTED_CDF"

# Update L2 dependency file
mv "$(l2path $L2_DEP_OLD)" "$(l2path $L2_DEP_NEW)"
sed -i 's/"minor_version": 3/"minor_version": 4/' "$(l2path $L2_DEP_NEW)"

# Update L3 dependency file
mv "$(l3path $L3_DEP_OLD)" "$(l3path $L3_DEP_NEW)"
sed -i 's/\"minor_version\": 5/\"minor_version\": 6/; s/0003/0004/' "$(l3path $L3_DEP_NEW)"

# Run L2 processing
cd "$IMAP_PROCESSING_DIR"
echo "===Starting L2 Processing==="
poetry run imap_cli                \
        --dependency "$L2_DEP_NEW" \
        --instrument hit           \
        --data-level l2            \
        --start-date 20260819      \
        --descriptor macropixel-intensity
echo "===Finished L2 Processing==="

# Run L3 processing
cd "$IMAP_L3_PROCESSING_DIR"
echo "===Starting L3 Processing==="
uv run ./imap_l3_data_processor.py \
        --dependency "$L3_DEP_NEW" \
        --instrument hit           \
        --data-level l3            \
        --start-date 20260819      \
        --descriptor macropixel
echo "===Finished L3 Processing==="

echo "===Starting CDF Comparison==="
cdfcompare -nonumber -noetc "$(cdfpath $TRUSTED_CDF)" "$(cdfpath $TEST_CDF)"
echo "===Finished CDF Comparison==="

echo "All done!"
