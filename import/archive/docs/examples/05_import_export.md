# 05_import_export

Direction convention example.

```text
import.file ./note.txt $texts:note
import.code ./steps.txt &boot

export.file $texts:note ./note_out.txt
export.code &boot ./boot_out.txt
```

Rule:

```text
<src> <dst>
```

That same direction should stay consistent across copy/move/import/export.
