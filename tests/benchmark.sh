#!/usr/bin/env bash

set -e

PYTHON="${PYTHON:-python3}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"

echo "Python: $PYTHON"

export PYTHONPATH=$SCRIPT_DIR/..

function create_patch() {
    echo "=== $1 ==="
    echo
    \time -f "RSS=%M elapsed=%E" \
          $PYTHON -m detools $1 $from_file $to_file $patch_file
    ls -lh $patch_file
    echo
}

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

create_patch "create_patch"
create_patch "create_patch_bsdiff"
create_patch "create_patch_hdiffpatch"
create_patch "create_patch_hdiffpatch --match-block-size 64"
create_patch "create_patch_hdiffpatch --match-block-size 1k"
create_patch "create_patch_hdiffpatch -c none --match-block-size 64"
create_patch "create_patch_hdiffpatch -c none  --match-block-size 1k"
