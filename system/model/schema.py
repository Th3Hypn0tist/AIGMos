# system/model/schema.py
#
# LobsterFarm-tui Stage0
#
# This file provides:
# - logical root namespaces (in-memory anchor points)
# - SQLite schema (DDL) for future persistence
#
# NOTE:
# The current Core is memory-only. The DDL here is a ready-to-wire contract,
# not yet enforced by Core. Keep roots stable to avoid breaking imports.

# -----------------------------
# Stage0 logical roots
# -----------------------------

KVL_ROOTS = (
    "texts",
)

LIST_ROOTS = (
    "routines",
)

TABLES_ROOT = "tables"


# -----------------------------
# SQLite schema (Stage0)
# -----------------------------
# Design goals:
# - deterministic, minimal, explicit
# - generic enough to store $, &, # without baking in topic logic
#
# Naming:
#   lf_* prefix (lobsterfarm)
#
# Tables:
# - lf_meta: schema version + misc
# - lf_kv_sub / lf_kv_item:  $ store (root/sub/key/value)
# - lf_list_sub / lf_list_item: & store (root/sub/idx/value)
# - lf_tbl_node: # tree store (adjacency list with explicit parent/key)

SCHEMA_VERSION = 1

SQLITE_PRAGMAS = (
    "PRAGMA foreign_keys = ON;",
    "PRAGMA journal_mode = WAL;",
    "PRAGMA synchronous = NORMAL;",
)

SQLITE_DDL = (
    # ---------------- meta ----------------
    """
    CREATE TABLE IF NOT EXISTS lf_meta (
        k TEXT PRIMARY KEY,
        v TEXT NOT NULL
    );
    """,
    """
    INSERT OR IGNORE INTO lf_meta(k, v) VALUES ('schema_version', CAST(? AS TEXT));
    """,
    # ---------------- $ (kvlists) ----------------
    """
    CREATE TABLE IF NOT EXISTS lf_kv_sub (
        root TEXT NOT NULL,
        sub  TEXT NOT NULL,
        PRIMARY KEY (root, sub)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS lf_kv_item (
        root TEXT NOT NULL,
        sub  TEXT NOT NULL,
        k    TEXT NOT NULL,
        v    TEXT NOT NULL DEFAULT '',
        PRIMARY KEY (root, sub, k),
        FOREIGN KEY (root, sub) REFERENCES lf_kv_sub(root, sub) ON DELETE CASCADE
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS lf_kv_item_by_sub ON lf_kv_item(root, sub);
    """,
    # ---------------- & (lists) ----------------
    """
    CREATE TABLE IF NOT EXISTS lf_list_sub (
        root TEXT NOT NULL,
        sub  TEXT NOT NULL,
        PRIMARY KEY (root, sub)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS lf_list_item (
        root TEXT NOT NULL,
        sub  TEXT NOT NULL,
        idx  INTEGER NOT NULL,
        v    TEXT NOT NULL DEFAULT '',
        PRIMARY KEY (root, sub, idx),
        FOREIGN KEY (root, sub) REFERENCES lf_list_sub(root, sub) ON DELETE CASCADE
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS lf_list_item_by_sub ON lf_list_item(root, sub, idx);
    """,
    # ---------------- # (tables/tree) ----------------
    # Adjacency list node model:
    # - node_path is a canonical ':'-joined path (no leading '#')
    # - parent_path is NULL for the root node of a tree
    # - node_key is the final segment (NULL for root)
    # - kind: 'dict' or 'leaf'
    """
    CREATE TABLE IF NOT EXISTS lf_tbl_node (
        root        TEXT NOT NULL,
        node_path   TEXT NOT NULL,
        parent_path TEXT,
        node_key    TEXT,
        kind        TEXT NOT NULL CHECK(kind IN ('dict','leaf')),
        v           TEXT,
        PRIMARY KEY (root, node_path)
    );
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS lf_tbl_node_siblings
        ON lf_tbl_node(root, parent_path, node_key);
    """,
    """
    CREATE INDEX IF NOT EXISTS lf_tbl_node_children
        ON lf_tbl_node(root, parent_path);
    """,
)


def sqlite_init(conn) -> None:
    """Initialize Stage0 SQLite schema on an existing sqlite3 connection."""
    cur = conn.cursor()
    for p in SQLITE_PRAGMAS:
        cur.execute(p)
    for stmt in SQLITE_DDL:
        # schema_version statement takes a parameter
        if "INSERT OR IGNORE INTO lf_meta" in stmt:
            cur.execute(stmt, (SCHEMA_VERSION,))
        else:
            cur.execute(stmt)
    conn.commit()
