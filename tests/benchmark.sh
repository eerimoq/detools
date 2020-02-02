#!/usr/bin/env bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"

export PYTHONPATH=$SCRIPT_DIR/..

from_file=Python-3.7.3.tar
to_file=Python-3.8.1.tar
patch_file=benchmark.patch

if [ ! -e Python-3.7.3.tar ] ; then
    wget https://www.python.org/ftp/python/3.7.3/Python-3.7.3.tgz
    gunzip Python-3.7.3.tgz
fi

if [ ! -e Python-3.8.1.tar ] ; then
    wget https://www.python.org/ftp/python/3.8.1/Python-3.8.1.tgz
    gunzip Python-3.8.1.tgz
fi

echo "=== create_patch ==="
echo
\time -f "RSS=%M elapsed=%E" \
      python3 -m detools create_patch \
      $from_file $to_file $patch_file
ls -lh $patch_file
echo

echo "=== create_patch_hdiffpatch ==="
echo
\time -f "RSS=%M elapsed=%E" \
      python3 -m detools create_patch_hdiffpatch \
      $from_file $to_file $patch_file
ls -lh $patch_file
echo

echo "=== create_patch_hdiffpatch --match-block-size 64 ==="
echo
\time -f "RSS=%M elapsed=%E" \
      python3 -m detools create_patch_hdiffpatch --match-block-size 64 \
      $from_file $to_file $patch_file
ls -lh $patch_file
echo

echo "=== create_patch_hdiffpatch --match-block-size 1k ==="
echo
\time -f "RSS=%M elapsed=%E" \
      python3 -m detools create_patch_hdiffpatch --match-block-size 1k \
      $from_file $to_file $patch_file
ls -lh $patch_file
echo

echo "=== create_patch_hdiffpatch -c none --match-block-size 64 ==="
echo
\time -f "RSS=%M elapsed=%E" \
      python3 -m detools create_patch_hdiffpatch -c none --match-block-size 64 \
      $from_file $to_file $patch_file
ls -lh $patch_file
echo

echo "=== create_patch_hdiffpatch -c none  --match-block-size 1k ==="
echo
\time -f "RSS=%M elapsed=%E" \
      python3 -m detools create_patch_hdiffpatch -c none  --match-block-size 1k \
      $from_file $to_file $patch_file
ls -lh $patch_file
echo
