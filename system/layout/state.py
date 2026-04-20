from __future__ import annotations

from typing import Any

from .lib import io as layout_io


meta_prefix = layout_io.meta_prefix
get_value = layout_io.get_value
set_value = layout_io.set_value
get_meta = layout_io.get_meta
set_meta = layout_io.set_meta
set_title = layout_io.set_title
set_prompt = layout_io.set_prompt
set_view_material = layout_io.set_view_material
refresh_instance_material = layout_io.refresh_instance_material
get_active_handle = layout_io.get_active_handle
set_active_handle = layout_io.set_active_handle


__all__ = [
    'meta_prefix',
    'get_value',
    'set_value',
    'get_meta',
    'set_meta',
    'set_title',
    'set_prompt',
    'set_view_material',
    'refresh_instance_material',
    'get_active_handle',
    'set_active_handle',
]
