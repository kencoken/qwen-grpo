"""Repo-wide pytest bootstrap: exclude sentencepiece from the test
process (171_s test-suite finding — the `-W error` exit-139 teardown
segfault).

Nothing in this suite uses sentencepiece: the pinned Qwen2 models
tokenize through the BPE `tokenizers` backend. The only importer is
transformers' optional-dependency probe
(`is_sentencepiece_available()` in AutoTokenizer machinery), which
imports the package merely to see whether it exists.

That probe is what killed the suite. sentencepiece's SWIG-generated C
extension emits cosmetic DeprecationWarnings ("builtin type
SwigPyPacked/SwigPyObject/swigvarlink has no __module__ attribute")
during its own init and again at interpreter finalization. Under
pytest `-W error` (specifically `error::DeprecationWarning`) that
poisons the extension's lifecycle, and the process segfaults inside
CPython finalization AFTER every test has passed and every artifact
is flushed — all tests green, exit 139, no Python frame. Minimal
repro: `python -W error -c "import sentencepiece"`.

Setting `sys.modules["sentencepiece"] = None` makes `import
sentencepiece` raise ImportError, so transformers takes its designed
sentencepiece-not-installed path and the SWIG extension never loads.
This must run before any test imports transformers, which is exactly
what a root conftest guarantees. Formal (non-pytest) runs are
unaffected: they neither load this file nor run under `-W error`,
and the pinned tokenizers do not touch sentencepiece either way.
"""

import sys

sys.modules["sentencepiece"] = None
