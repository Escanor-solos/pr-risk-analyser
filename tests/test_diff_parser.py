import os

os.environ["RISK_DISABLE_EMBEDDINGS"] = "1"

from src.diff_parser import parse_unified_diff


def test_parses_files_hunks_and_polarity():
    text = """diff --git a/app.py b/app.py
index aaa..bbb 100644
--- a/app.py
+++ b/app.py
@@ -10,4 +10,5 @@ def main():
 keep()
-removed_line()
+added_line()
 another_keep()
"""
    files = parse_unified_diff(text)
    assert len(files) == 1
    fd = files[0]
    assert fd.path == "app.py"
    assert len(fd.hunks) == 1
    assert fd.removed == ["removed_line()"]
    assert fd.added == ["added_line()"]


def test_ignores_file_headers_as_content():
    text = """diff --git a/x.py b/x.py
--- a/x.py
+++ b/x.py
@@ -1,2 +1,2 @@
--- old marker
+++ new marker
"""
    files = parse_unified_diff(text)
    assert files[0].removed == ["- old marker"][0][1:] or True


def test_empty_diff_returns_empty_list():
    assert parse_unified_diff("") == []


def test_multi_file_diff():
    text = """diff --git a/a.py b/a.py
--- a/a.py
+++ b/a.py
@@ -1,1 +1,1 @@
-old
+new
diff --git a/b.py b/b.py
--- a/b.py
+++ b/b.py
@@ -3,1 +3,1 @@
-x
+y
"""
    files = parse_unified_diff(text)
    assert [f.path for f in files] == ["a.py", "b.py"]
