/*
 * sais.c for sais-lite
 * Copyright (c) 2008-2010 Yuta Mori All Rights Reserved.
 * Copyright (c) 2019, Erik Moqvist (Python wrapper).
 *
 * Permission is hereby granted, free of charge, to any person
 * obtaining a copy of this software and associated documentation
 * files (the "Software"), to deal in the Software without
 * restriction, including without limitation the rights to use,
 * copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the
 * Software is furnished to do so, subject to the following
 * conditions:
 *
 * The above copyright notice and this permission notice shall be
 * included in all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 * EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
 * OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 * NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
 * HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
 * WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
 * FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 * OTHER DEALINGS IN THE SOFTWARE.
 */

#include <stdint.h>
#include <Python.h>
#include "sais/sais.h"
#include "libdivsufsort/divsufsort.h"

typedef int32_t (*create_t)(const uint8_t *buf_p,
                            int32_t *suffix_array_p,
                            int32_t length);

static PyObject *create(PyObject *self_p,
                        PyObject* arg_p,
                        create_t create_callback)
{
    int res;
    char *buf_p;
    Py_ssize_t size;
    int32_t *suffix_array_p;
    PyObject *byte_array_p;

    /* Input argument conversion. */
    res = PyBytes_AsStringAndSize(arg_p, &buf_p, &size);

    if (res == -1) {
        return (NULL);
    }

    if (size > 0x7fffffff) {
        PyErr_SetString(PyExc_ValueError, "SA-IS data too long (over 0x7fffffff).");

        return (NULL);
    }

    byte_array_p = PyByteArray_FromStringAndSize("", 1);

    if (byte_array_p == NULL) {
        return (NULL);
    }

    res = PyByteArray_Resize(byte_array_p, (size + 1) * sizeof(*suffix_array_p));

    if (res != 0) {
        goto err1;
    }

    suffix_array_p = (int32_t *)PyByteArray_AsString(byte_array_p);
    suffix_array_p[0] = (int32_t)size;

    /* Execute the SA-IS algorithm. */
    res = create_callback((uint8_t *)buf_p, &suffix_array_p[1], (int32_t)size);

    if (res != 0) {
        goto err1;
    }

    return (byte_array_p);

 err1:
    Py_DECREF(byte_array_p);

    return (NULL);
}

/**
 * def sais(data) -> suffix array
 */
static PyObject *m_sais(PyObject *self_p, PyObject* arg_p)
{
    return (create(self_p, arg_p, sais));
}

/**
 * def divsufsort(data) -> suffix array
 */
static PyObject *m_divsufsort(PyObject *self_p, PyObject* arg_p)
{
    return (create(self_p, arg_p, divsufsort));
}

static PyMethodDef module_methods[] = {
    { "sais", m_sais, METH_O },
    { "divsufsort", m_divsufsort, METH_O },
    { NULL }
};

static PyModuleDef module = {
    PyModuleDef_HEAD_INIT,
    .m_name = "suffix_array",
    .m_doc = NULL,
    .m_size = -1,
    .m_methods = module_methods
};

PyMODINIT_FUNC PyInit_suffix_array(void)
{
    PyObject *m_p;

    /* Module creation. */
    m_p = PyModule_Create(&module);

    if (m_p == NULL) {
        return (NULL);
    }

    return (m_p);
}
