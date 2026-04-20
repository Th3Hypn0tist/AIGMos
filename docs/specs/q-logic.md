# Q / QC logiikka

## Roles

Kirjasto:
#ROLES

Fileet:
extensions/roles < #ROLES
system/library/roles < #ROLES:system

2 tiedostoa help.role ja help.system
.role:
json kaikista payload asetuksista
-temperature
-think
-stream
-top_k
-top_p
-repeat_penalty
-etc  

.system
system prompt file

role luetaan kun q instanssi luodaan ja täytetään |<instanssi>:q:variaabelit

kun q tai qc ajetaan roolitettuna, otetaan |<instanssi>:<q instanssi id> llm asetukset mukaan payloadiin.

q:ssa backend hoitaa sen eli määrittyy q id:n (|instance hande>:<q id> mukaan, mutta qc:ssä se on aina kertakäyttöinen ja käytetään qc.r.system:help jolloin mukaan luetaan #ROLES:system:help.role ja #ROLES:system:help.system

## Layoutsääntö
|:q & #ROLES:system:help
<q id="q" role="system/help">

## export

export.file |:q
- exporttaa q-runtime snapshotin
- snapshot voi vastata roolin payload-osuutta
- sen voi ottaa talteen ja lisätä käsin #ROLES alle uutena canonical role -entrynä

## <q>

Think ja stream seuraa |<instance>:<id>:think & |<instance>:<id>:stream

## LUKITTU EROTUS

qc:
- lukee vain canonical rolea
- lähde: #ROLES:*
- ei koskaan lue |instance:q:* runtimea

q:
- lukee vain runtimea
- lähde: |<instance>:<q_id>:*
- ei koskaan liko payload-buildissä takaisin #ROLES:* canonicaliin

KIELLETTY:
- hiljainen fallback qc -> runtime
- hiljainen fallback q -> canonical
- default-root oikopolut
- |Q special-case
- $Q legacy-fallback
