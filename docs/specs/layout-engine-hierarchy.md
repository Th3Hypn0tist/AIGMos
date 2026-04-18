#reload 

/reload rikotaan omaksi käskykseen reload, jolloin on helpompi hallita mitä ladataan uusiksi.

tehdään ekaan boottiin import rutiini (oma tiedosto tälle, että pystyy säätään käsin lisää importteja. voi käyttää suoraan parserin import.file ja import.code jne eli oman käskykannan kautta) system/init.cs (.cs on käsky per rivi fileitä jatkossa eli vastaava, kuin import.list, mutta import.cs eli vain käsykyrimpsu per rivi)

system/library/help > #HELP

kaikki system/library/roles alla on #ROLES:system
lataa ensin extensions/roles #ROLES symboliin ja sitten perään system/library/roles #ROLES:system alle
tämä on reload roles 

sama extensions/prompts & system/library/prompts, mutta #P:ksi < tämä on reload prompts

sama extensions/routines & system/library/routines, mutta #R:ksi  < tämä on reload routines

näin system tilut pysyy user tiluista nätisti irti


# layouts
käytetään | instansseissa samaa rakennetta, kuin # eli |eli:saadaan:moni:tasoset:referenssit

|:buffer
|:command_history
|:show_thinking < tämä on layout instanssin uusi muuttuja valitsee vain näytetäänkö thinking vai ei

layout moduulit varaavat luomisvaiheessa itelleen tarvittavat muuttujat id:llään.

esim <q> = |:q1:ch

alkaa aina ykkösestä, jolloin kaikilla on id.

jos reload role/roles vaiheessa on useampi personoitava moduli ilman id:tä tai päällekkäisillä, niin error ja mikä template sen aiheutti

# q roles

2 tiedostoa <role>.role ja <role>.system, joista <role>.system optionaalinen system prompt

system/library/roles/help.role - json muoto
{   
    "temperature": "0.2",
    "top_p": "0.9",
    "top_k": "40",
    "repeat_penalty": "1.05",
    "thinking": "off",
}


rooli overridet tulee |:role alle ne luodaan samalla, kun layout instanssi, mutta tyhjinä.
|:q1:temperature
|:q1:top_p
|:q1:top_k
|:q1:repeat penalty
|:q1:thinking

reload role <role> nollaa nämä

valinnainen system prompt tulee erilliseen .system fileeseen samalla nimellä kuin .role

system/library/roles/help.system:

Here is the reference: #HELP Do not make things up. Use only reference. No extra
comments. Keep answers short and clear.

molemmat tottelee samaa polkua <q role="system/help">

kun q käsky roolilla lähtee, niin ensin tarkistetaan overridet, mergetään ne #ROLES:<role> :sta saataviin arvoihin. listätään system prompt jos on ja puretaan kaikki symbolit > dispatch q command


Tämä taitaa kuulua johonkin muualle, kuin rooliin? aliakseen?

    "stop": ["<|im_start|>", "<|im_end|>"]
