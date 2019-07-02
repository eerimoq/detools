/*-
 * Copyright 2003-2005 Colin Percival
 * Copyright (c) 2019, Erik Moqvist
 * All rights reserved
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted providing that the following conditions
 * are met:
 * 1. Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 * 2. Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the distribution.
 *
 * THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
 * IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
 * WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 * ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY
 * DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
 * DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
 * OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
 * HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
 * STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING
 * IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 * POSSIBILITY OF SUCH DAMAGE.
 */

#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <Python.h>

#define MIN(x, y) (((x) < (y)) ? (x) : (y))

static int32_t matchlen(uint8_t *from_p,
                        int32_t from_size,
                        uint8_t *to_p,
                        int32_t to_size)
{
    int32_t i;

    for (i = 0; i < MIN(from_size, to_size); i++) {
        if (from_p[i] != to_p[i]) {
            break;
        }
    }

    return (i);
}

static int32_t search(int32_t *sa_p,
                      uint8_t *from_p,
                      int32_t from_size,
                      uint8_t *to_p,
                      int32_t to_size,
                      int32_t from_begin,
                      int32_t from_end,
                      int32_t *pos_p)
{
    int32_t x;
    int32_t y;

    if (from_end - from_begin < 2) {
        x = matchlen(from_p + sa_p[from_begin],
                     from_size - sa_p[from_begin],
                     to_p,
                     to_size);
        y = matchlen(from_p + sa_p[from_end],
                     from_size - sa_p[from_end],
                     to_p,
                     to_size);

        if (x > y) {
            *pos_p = sa_p[from_begin];

            return (x);
        } else {
            *pos_p = sa_p[from_end];

            return (y);
        }
    }

    x = (from_begin + (from_end - from_begin) / 2);

    if (memcmp(from_p + sa_p[x], to_p, MIN(from_size - sa_p[x], to_size)) < 0) {
        return search(sa_p, from_p, from_size, to_p, to_size, x, from_end, pos_p);
    } else {
        return search(sa_p, from_p, from_size, to_p, to_size, from_begin, x, pos_p);
    }
}

static int pack_size(uint8_t *buf_p, int32_t value, size_t size)
{
    int res;

    if (size < 10) {
        return (-1);
    }

    res = 0;

    if (value == 0) {
        buf_p[0] = 0;
        res++;
    } else {
        if (value > 0) {
            buf_p[res] = 0;
        } else {
            buf_p[res] = 0x40;
            value *= -1;
        }

        buf_p[res] |= (0x80 | (value & 0x3f));
        value >>= 6;
        res++;

        while (value > 0) {
            buf_p[res] = (0x80 | (value & 0x7f));
            value >>= 7;
            res++;
        }
    }

    buf_p[res - 1] &= 0x7f;

    return (res);
}

static int append_bytes(PyObject *list_p, uint8_t *buf_p, int32_t size)
{
    int res;
    PyObject *bytes_p;

    bytes_p = PyBytes_FromStringAndSize((char *)buf_p, size);

    if (bytes_p == NULL) {
        return (-1);
    }

    res = PyList_Append(list_p, bytes_p);

    Py_DECREF(bytes_p);

    return (res);
}

static int append_size(PyObject *list_p, int32_t size)
{
    int res;
    uint8_t buf[10];

    res = pack_size(&buf[0], size, sizeof(buf));

    if (res <= 0) {
        return (-1);
    }

    return (append_bytes(list_p, &buf[0], res));
}

static int append_buffer(PyObject *list_p, uint8_t *buf_p, int32_t size)
{
    int res;

    res = append_size(list_p, size);

    if (res != 0) {
        return (res);
    }

    return (append_bytes(list_p, buf_p, size));
}

static int parse_args(PyObject *args_p,
                      Py_ssize_t *suffix_array_length_p,
                      int32_t **sa_pp,
                      char **from_pp,
                      char **to_pp,
                      Py_ssize_t *from_size_p,
                      Py_ssize_t *to_size_p)
{
    int res;
    PyObject *sa_p;
    PyObject *from_bytes_p;
    PyObject *to_bytes_p;

    res = PyArg_ParseTuple(args_p,
                           "OOO",
                           &sa_p,
                           &from_bytes_p,
                           &to_bytes_p);

    if (res == 0) {
        return (-1);
    }

    *suffix_array_length_p = (PyByteArray_Size(sa_p) / sizeof(int32_t));

    if (*suffix_array_length_p <= 0) {
        return (-1);
    }

    *sa_pp = (int32_t *)PyByteArray_AsString(sa_p);

    res = PyBytes_AsStringAndSize(from_bytes_p, from_pp, from_size_p);

    if (res != 0) {
        return (-1);
    }

    res = PyBytes_AsStringAndSize(to_bytes_p, to_pp, to_size_p);

    if (res != 0) {
        return (-1);
    }

    return (res);
}

static int write_diff_extra_and_adjustment(PyObject *list_p,
                                           uint8_t *from_p,
                                           Py_ssize_t from_size,
                                           uint8_t *to_p,
                                           Py_ssize_t to_size,
                                           uint8_t *debuf_p,
                                           int32_t scan,
                                           int32_t pos,
                                           int32_t *last_scan_p,
                                           int32_t *last_pos_p,
                                           int32_t *last_offset_p)
{
    int res;
    int32_t s;
    int32_t sf;
    int32_t diff_size;
    int32_t extra_pos;
    int32_t extra_size;
    int32_t sb;
    int32_t lenb;
    int32_t overlap;
    int32_t ss;
    int32_t lens;
    int32_t i;
    int32_t last_scan;
    int32_t last_pos;

    last_scan = *last_scan_p;
    last_pos = *last_pos_p;
    s = 0;
    sf = 0;
    diff_size = 0;

    for (i = 0; (last_scan + i < scan) && (last_pos + i < from_size);) {
        if (from_p[last_pos + i] == to_p[last_scan + i]) {
            s++;
        }

        i++;

        if (s * 2 - i > sf * 2 - diff_size) {
            sf = s;
            diff_size = i;
        }
    }

    lenb = 0;

    if (scan < to_size) {
        s = 0;
        sb = 0;

        for (i = 1; (scan >= last_scan + i) && (pos >= i); i++) {
            if (from_p[pos - i] == to_p[scan - i]) {
                s++;
            }

            if (s * 2 - i > sb * 2 - lenb) {
                sb = s;
                lenb = i;
            }
        }
    }

    overlap = (last_scan + diff_size) - (scan - lenb);

    if (overlap > 0) {
        s = 0;
        ss = 0;
        lens = 0;

        for (i = 0; i < overlap; i++) {
            if (to_p[last_scan + diff_size - overlap + i]
                == from_p[last_pos + diff_size - overlap + i]) {
                s++;
            }

            if (to_p[scan - lenb + i] == from_p[pos - lenb + i]) {
                s--;
            }

            if (s > ss) {
                ss = s;
                lens = (i + 1);
            }
        }

        diff_size += (lens - overlap);
        lenb -= lens;
    }

    /* Diff data. */
    for (i = 0; i < diff_size; i++) {
        debuf_p[i] = (to_p[last_scan + i] - from_p[last_pos + i]);
    }

    res = append_buffer(list_p, &debuf_p[0], diff_size);

    if (res != 0) {
        return (res);
    }

    /* Extra data. */
    extra_pos = (last_scan + diff_size);
    extra_size = (scan - lenb - extra_pos);

    for (i = 0; i < extra_size; i++) {
        debuf_p[i] = to_p[extra_pos + i];
    }

    res = append_buffer(list_p, &debuf_p[0], extra_size);

    if (res != 0) {
        return (res);
    }

    /* Adjustment. */
    res = append_size(list_p, (pos - lenb) - (last_pos + diff_size));

    if (res != 0) {
        return (res);
    }

    *last_scan_p = (scan - lenb);
    *last_pos_p = (pos - lenb);
    *last_offset_p = (pos - scan);

    return (0);
}

static int create_patch_loop(PyObject *list_p,
                             int32_t *sa_p,
                             uint8_t *from_p,
                             Py_ssize_t from_size,
                             uint8_t *to_p,
                             Py_ssize_t to_size,
                             uint8_t *debuf_p)
{
    int res;
    int32_t scan;
    int32_t pos;
    int32_t len;
    int32_t last_scan;
    int32_t last_pos;
    int32_t last_offset;
    int32_t from_score;
    int32_t scsc;

    scan = 0;
    len = 0;
    last_scan = 0;
    last_pos = 0;
    last_offset = 0;
    pos = 0;

    while (scan < to_size) {
        from_score = 0;
        scan += len;

        for (scsc = scan; scan < to_size; scan++) {
            len = search(sa_p,
                         from_p,
                         from_size,
                         to_p + scan,
                         to_size - scan,
                         0,
                         from_size,
                         &pos);

            for (; scsc < scan + len; scsc++) {
                if ((scsc + last_offset < from_size)
                    && (from_p[scsc + last_offset] == to_p[scsc])) {
                    from_score++;
                }
            }

            if (((len == from_score) && (len != 0)) || (len > from_score + 8)) {
                break;
            }

            if ((scan + last_offset < from_size)
                && (from_p[scan + last_offset] == to_p[scan])) {
                from_score--;
            }
        }

        if ((len != from_score) || (scan == to_size)) {
            res = write_diff_extra_and_adjustment(list_p,
                                                  from_p,
                                                  from_size,
                                                  to_p,
                                                  to_size,
                                                  debuf_p,
                                                  scan,
                                                  pos,
                                                  &last_scan,
                                                  &last_pos,
                                                  &last_offset);

            if (res != 0) {
                return (res);
            }
        }
    }

    return (0);
}

static PyObject *m_pack_size(PyObject *self_p, PyObject *arg_p)
{
    int res;
    long long size;
    uint8_t buf[10];
    PyObject *bytes_p;

    size = PyLong_AsLongLong(arg_p);

    if ((size == -1) && PyErr_Occurred()) {
        return (NULL);
    }

    res = pack_size(&buf[0], size, sizeof(buf));

    if (res <= 0) {
        PyErr_Format(PyExc_ValueError, "Pack size failed with %d.", res);

        return (NULL);
    }

    bytes_p = PyBytes_FromStringAndSize((char *)&buf[0], res);

    if (bytes_p == NULL) {
        return (NULL);
    }

    return (bytes_p);
}

static PyObject *m_create_patch(PyObject *self_p, PyObject *args_p)
{
    int res;
    uint8_t *from_p;
    uint8_t *to_p;
    Py_ssize_t from_size;
    Py_ssize_t to_size;
    int32_t *sa_p;
    uint8_t *debuf_p;
    PyObject *list_p;
    Py_ssize_t suffix_array_length;

    res = parse_args(args_p,
                     &suffix_array_length,
                     &sa_p,
                     (char **)&from_p,
                     (char **)&to_p,
                     &from_size,
                     &to_size);

    if (res != 0) {
        return (NULL);
    }

    debuf_p = PyMem_Malloc(to_size + 1);

    if (debuf_p == NULL) {
        goto err1;
    }

    list_p = PyList_New(0);

    if (list_p == NULL) {
        goto err2;
    }

    res = create_patch_loop(list_p,
                            sa_p,
                            from_p,
                            from_size,
                            to_p,
                            to_size,
                            debuf_p);

    if (res != 0) {
        goto err3;
    }

    PyMem_Free(debuf_p);

    return (list_p);

 err3:
    Py_DECREF(list_p);

 err2:
    PyMem_Free(debuf_p);

 err1:
    PyMem_Free(sa_p);

    return (NULL);
}

static PyMethodDef module_methods[] = {
    { "pack_size", m_pack_size, METH_O },
    { "create_patch", m_create_patch, METH_VARARGS },
    { NULL }
};

static PyModuleDef module = {
   PyModuleDef_HEAD_INIT,
   .m_name = "cbsdiff",
   .m_doc = NULL,
   .m_size = -1,
   .m_methods = module_methods
};

PyMODINIT_FUNC PyInit_cbsdiff(void)
{
    PyObject *m_p;

    /* Module creation. */
    m_p = PyModule_Create(&module);

    if (m_p == NULL) {
        return (NULL);
    }

    return (m_p);
}
