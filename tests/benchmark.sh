#!/usr/bin/env bash

set -e

PYTHON="${PYTHON:-python3}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"

echo "Python: $PYTHON"

export PYTHONPATH=$SCRIPT_DIR/..

# create_patch with zeros is very slow, so bigger file size is not
# feasible.
FILE_SIZE=600000

function create_patch() {
    echo "===== $1 ====="
    echo
    echo "$PYTHON -m detools -l info $1 $from_file $to_file $patch_file"
    \time -f "RSS=%M elapsed=%E" \
          $PYTHON -m detools -l info $1 $from_file $to_file $patch_file
    ls -lh $patch_file
    echo
    echo "----- $2 -----"
    echo
    echo "$PYTHON -m detools -l info $2 $from_file $patch_file to.tar"
    \time -f "RSS=%M elapsed=%E" \
          $PYTHON -m detools -l info $2 $from_file $patch_file to.tar
    cmp $to_file to.tar
    echo
}

if [ ! -e Python-3.7.3.tar ] ; then
    wget https://www.python.org/ftp/python/3.7.3/Python-3.7.3.tgz
    gunzip Python-3.7.3.tgz
    cp Python-3.7.3.tar Trunc-3.7.3.tar
    truncate -s $FILE_SIZE Trunc-3.7.3.tar
fi

if [ ! -e Python-3.8.1.tar ] ; then
    wget https://www.python.org/ftp/python/3.8.1/Python-3.8.1.tgz
    gunzip Python-3.8.1.tgz
    cp Python-3.8.1.tar Trunc-3.8.1.tar
    truncate -s $FILE_SIZE Trunc-3.8.1.tar
fi

if [ ! -e Trunc-3.7.3.tar ] ; then
    cp Python-3.7.3.tar Trunc-3.7.3.tar
    truncate -s $FILE_SIZE Trunc-3.7.3.tar
fi

if [ ! -e Trunc-3.8.1.tar ] ; then
    cp Python-3.8.1.tar Trunc-3.8.1.tar
    truncate -s $FILE_SIZE Trunc-3.8.1.tar
fi

if [ ! -e Random-3.7.3.bin ] ; then
    dd if=/dev/urandom of=Random-3.7.3.bin bs=$FILE_SIZE count=1 iflag=fullblock
fi

if [ ! -e Random-3.8.1.bin ] ; then
    dd if=/dev/urandom of=Random-3.8.1.bin bs=$FILE_SIZE count=1 iflag=fullblock
fi

if [ ! -e Zeros-3.7.3.bin ] ; then
    dd if=/dev/zero of=Zeros-3.7.3.bin bs=$FILE_SIZE count=1 iflag=fullblock
fi

if [ ! -e Zeros-3.8.1.bin ] ; then
    dd if=/dev/zero of=Zeros-3.8.1.bin bs=$FILE_SIZE count=1 iflag=fullblock
fi

from_file=Trunc-3.7.3.tar
to_file=Trunc-3.8.1.tar
patch_file=benchmark.patch

create_patch "create_patch" "apply_patch"
create_patch "create_patch_hdiffpatch" "apply_patch"

from_file=Random-3.7.3.bin
to_file=Random-3.8.1.bin
patch_file=benchmark.patch

create_patch "create_patch" "apply_patch"
create_patch "create_patch_hdiffpatch" "apply_patch"

from_file=Zeros-3.7.3.bin
to_file=Zeros-3.8.1.bin
patch_file=benchmark.patch

create_patch "create_patch" "apply_patch"
create_patch "create_patch_hdiffpatch" "apply_patch"

from_file=Python-3.7.3.tar
to_file=Python-3.8.1.tar
patch_file=benchmark.patch

create_patch "create_patch" "apply_patch"
create_patch "create_patch_bsdiff" "apply_patch_bsdiff"
create_patch "create_patch_hdiffpatch" "apply_patch"
create_patch "create_patch_hdiffpatch --match-block-size 64" "apply_patch"
create_patch "create_patch_hdiffpatch --match-block-size 1k" "apply_patch"
create_patch "create_patch_hdiffpatch -c none --match-block-size 64" "apply_patch"
create_patch "create_patch_hdiffpatch -c none --match-block-size 1k" "apply_patch"
