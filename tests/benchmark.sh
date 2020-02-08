#!/usr/bin/env bash

PYTHON="${PYTHON:-python3}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"

echo "Python: $PYTHON"

export PYTHONPATH=$SCRIPT_DIR/..

function create_patch() {
    echo "================= $1 ================="
    \time -f "RSS=%M elapsed=%E" \
          $PYTHON -m detools create_patch $1 $from_file $to_file $patch_file \
          > /dev/null
    ls -lh $patch_file
}

if [ ! -e Python-3.7.3.tar ] ; then
    wget https://www.python.org/ftp/python/3.7.3/Python-3.7.3.tgz
    gunzip Python-3.7.3.tgz
fi

if [ ! -e Python-3.8.1.tar ] ; then
    wget https://www.python.org/ftp/python/3.8.1/Python-3.8.1.tgz
    gunzip Python-3.8.1.tgz
fi

from_file=Python-3.7.3.tar
to_file=Python-3.8.1.tar
patch_file=benchmark.patch

for algorithm in bsdiff hdiffpatch match-blocks ; do
    for patch_type in normal hdiffpatch ; do
        for compression in lzma none ; do
            create_patch "-a $algorithm -t $patch_type -c $compression"
        done
    done
done
