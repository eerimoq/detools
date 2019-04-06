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

static int64_t matchlen(uint8_t *from_p,
                        int64_t from_size,
                        uint8_t *to_p,
                        int64_t to_size)
{
    int64_t i;

    for (i = 0; i < MIN(from_size, to_size); i++) {
        if (from_p[i] != to_p[i]) {
            break;
        }
    }

    return (i);
}

static int64_t search(int64_t *i_p,
                      uint8_t *from_p,
                      int64_t from_size,
                      uint8_t *to_p,
                      int64_t to_size,
                      int64_t st,
                      int64_t en,
                      int64_t *pos)
{
    int64_t x;
    int64_t y;

    if (en - st < 2) {
        x = matchlen(from_p + i_p[st], from_size - i_p[st], to_p, to_size);
        y = matchlen(from_p + i_p[en], from_size - i_p[en], to_p, to_size);

        if (x > y) {
            *pos = i_p[st];

            return (x);
        } else {
            *pos = i_p[en];

            return (y);
        }
    }

    x = (st + (en - st) / 2);

    if (memcmp(from_p + i_p[x], to_p, MIN(from_size - i_p[x], to_size)) < 0) {
        return search(i_p, from_p, from_size, to_p, to_size, x, en, pos);
    } else {
        return search(i_p, from_p, from_size, to_p, to_size, st, x, pos);
    }
}

static int pack_size(uint8_t *buf_p, int64_t value, size_t size)
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

static int append_bytes(PyObject *list_p, uint8_t *buf_p, int64_t size)
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

static int append_size(PyObject *list_p, int64_t size)
{
    int res;
    uint8_t buf[10];

    res = pack_size(&buf[0], size, sizeof(buf));

    if (res <= 0) {
        return (-1);
    }

    return (append_bytes(list_p, &buf[0], res));
}

static int append_buffer(PyObject *list_p, uint8_t *buf_p, int64_t size)
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
                      int64_t **i_pp,
                      char **from_pp,
                      char **to_pp,
                      Py_ssize_t *from_size_p,
                      Py_ssize_t *to_size_p)
{
    int res;
    PyObject *suffix_array_p;
    PyObject *from_bytes_p;
    PyObject *to_bytes_p;
    int i;

    res = PyArg_ParseTuple(args_p,
                           "OOO",
                           &suffix_array_p,
                           &from_bytes_p,
                           &to_bytes_p);

    if (res == 0) {
        return (-1);
    }

    *suffix_array_length_p = PyList_Size(suffix_array_p);

    if (*suffix_array_length_p <= 0) {
        return (-1);
    }

    *i_pp = PyMem_Malloc(*suffix_array_length_p * sizeof(**i_pp));

    if (*i_pp == NULL) {
        return (-1);
    }

    for (i = 0; i < *suffix_array_length_p; i++) {
        (*i_pp)[i] = PyLong_AsLong(PyList_GET_ITEM(suffix_array_p, i));
    }

    res = PyBytes_AsStringAndSize(from_bytes_p, from_pp, from_size_p);

    if (res != 0) {
        goto err1;
    }

    res = PyBytes_AsStringAndSize(to_bytes_p, to_pp, to_size_p);

    if (res != 0) {
        goto err1;
    }

    return (res);

 err1:
    PyMem_Free(*i_pp);

    return (-1);
}

static int create_patch_loop(PyObject *list_p,
                             int64_t *i_p,
                             uint8_t *from_p,
                             Py_ssize_t from_size,
                             uint8_t *to_p,
                             Py_ssize_t to_size,
                             uint8_t *db_p,
                             uint8_t *eb_p)
{
    int res;
    int64_t scan;
    int64_t pos;
    int64_t len;
    int64_t last_scan;
    int64_t last_pos;
    int64_t last_offset;
    int64_t from_score;
    int64_t scsc;
    int64_t s;
    int64_t sf;
    int64_t lenf;
    int64_t sb;
    int64_t lenb;
    int64_t overlap;
    int64_t ss;
    int64_t lens;
    int64_t i;

    scan = 0;
    len = 0;
    last_scan = 0;
    last_pos = 0;
    last_offset = 0;
    pos = 0;

    while (scan < to_size) {
        from_score = 0;

        for (scsc = scan += len; scan < to_size; scan++) {
            len = search(i_p,
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
            s = 0;
            sf = 0;
            lenf = 0;

            for (i = 0; (last_scan + i < scan) && (last_pos + i < from_size);) {
                if (from_p[last_pos + i] == to_p[last_scan + i]) {
                    s++;
                }

                i++;

                if (s * 2 - i > sf * 2 - lenf) {
                    sf = s;
                    lenf = i;
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

            if (last_scan + lenf > scan - lenb) {
                overlap = (last_scan + lenf) - (scan - lenb);
                s = 0;
                ss = 0;
                lens = 0;

                for (i = 0; i < overlap; i++) {
                    if (to_p[last_scan + lenf - overlap + i]
                        == from_p[last_pos + lenf - overlap + i]) {
                        s++;
                    }

                    if(to_p[scan - lenb + i] == from_p[pos - lenb + i]) {
                        s--;
                    }

                    if (s > ss) {
                        ss = s;
                        lens = (i + 1);
                    }
                }

                lenf += (lens - overlap);
                lenb -= lens;
            }

            for (i = 0; i < lenf; i++) {
                db_p[i] = (to_p[last_scan + i] - from_p[last_pos + i]);
            }

            for(i = 0; i < (scan - lenb) - (last_scan + lenf); i++) {
                eb_p[i] = to_p[last_scan + lenf + i];
            }

            /* Diff data. */
            res = append_buffer(list_p, &db_p[0], lenf);

            if (res != 0) {
                return (res);
            }

            /* Extra data. */
            res = append_buffer(list_p,
                                &eb_p[0],
                                (scan - lenb) - (last_scan + lenf));

            if (res != 0) {
                return (res);
            }

            /* Adjustment. */
            res = append_size(list_p, (pos - lenb) - (last_pos + lenf));

            if (res != 0) {
                return (res);
            }

            last_scan = (scan - lenb);
            last_pos = (pos - lenb);
            last_offset = (pos - scan);
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
    int64_t *i_p;
    uint8_t *db_p;
    uint8_t *eb_p;
    PyObject *list_p;
    Py_ssize_t suffix_array_length;

    res = parse_args(args_p,
                     &suffix_array_length,
                     &i_p,
                     (char **)&from_p,
                     (char **)&to_p,
                     &from_size,
                     &to_size);

    if (res != 0) {
        return (NULL);
    }

    list_p = PyList_New(0);

    if (list_p == NULL) {
        goto err1;
    }

    db_p = PyMem_Malloc(to_size + 1);

    if (db_p == NULL) {
        goto err2;
    }

    eb_p = PyMem_Malloc(to_size + 1);

    if (eb_p == NULL) {
        goto err3;
    }

    res = create_patch_loop(list_p,
                            i_p,
                            from_p,
                            from_size,
                            to_p,
                            to_size,
                            db_p,
                            eb_p);

    if (res != 0) {
        goto err4;
    }

    PyMem_Free(eb_p);
    PyMem_Free(db_p);
    PyMem_Free(i_p);

    return (list_p);

 err4:
    PyMem_Free(eb_p);

 err3:
    PyMem_Free(db_p);

 err2:
    Py_DECREF(list_p);

 err1:
    PyMem_Free(i_p);

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
