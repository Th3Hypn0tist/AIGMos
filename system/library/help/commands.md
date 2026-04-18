> /help
/help [/cmd] | /time | /greeting | /clear | /health q[.alias] | /exit
add -> add <target> <source>
bind -> bind alt-1..alt-9|alt-0 <command...>
binds -> binds
cat -> cat <target>
cp -> cp <src> <dst>
cycle -> cycle <source>
echo -> echo <message>
emit -> emit @event | emit !trigger
export.code -> export.code <src> <dst>
export.file -> export.file <src> <dst>
export.json -> export.json <src> <dst>
get -> get <output> <symbol>
hget -> hget <output> <url|symbol>
hpost -> hpost <output> <url|symbol> <raw-body...>
import.code -> import.code <src> <dst>
import.file -> import.file <src> <target>
import.json -> import.json <input> <output>
import.list -> import.list <source> <target>
loop -> loop &name
ls -> ls [target|prefix*]
map.files -> map.files #input [$output]
map.structure -> map.structure #input [$output]
mk -> mk <target>
mv -> mv <src> <dst>
new -> new |<instance> /<module-or-layout>
on -> on !trigger @event "command"
q -> q[.profile] <target> <prompt...>
qc -> qc[.profile] <output> <prompt...>
reload -> reload [help|roles|role <name>|prompts|routines|layout|config|commands|adapters|inputs|all]
rm -> rm <target>
run -> run <command|&source>
set -> set <symbol> <value>
trig -> trig !name <expr> | trig !name onchange <ref> | trig !name cron "spec"
unbind -> unbind alt-1..alt-9|alt-0
