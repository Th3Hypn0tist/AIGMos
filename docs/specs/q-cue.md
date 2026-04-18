# Q query cue

# aliakset
- jokaisella aliaksella on oma jononsa, jossa yksi slotti per q instanssi, mutta vapaassa järjestyksessä.
- fifo

# q instanssit
- jokaisella instanssilla on yksi slotti
- lisätään status eli kun kysely on lähtenyt |:<q id>:status = waiting ja kun :ch:n done = 1 niin status = done
- kun status waiting, niin näytetään joko [Thinking...] planssi tai thinking rutiini

tämä korvaa nykyisen jonotussysteemin.
