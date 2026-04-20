Q logic

Näytä aina vastauksen ajan vähintään, jotta on joku vaste kyselylle:
[Thinking...]

1) stream
- stream = true
  -> payload["stream"] = true
- stream = false
  ei stream-kenttää ja think ignoroidaan kokonaan, jos tream = false


2) think
- think = true
  -> merge think_payload payloadiin
- think = false
  -> merge nothink_payload payloadiin

3) view_thinking
- view_thinking = true
  -> näytä varsinainen thinking-prosessi
- view_thinking = false & think = true
  -> näytä vain [Thinking...]
- view_thinking ei saa vaikuttaa payloadiin
- view_thinking ei saa vaikuttaa stream-päätökseen


4) erot
- think = payload-intent
- view_thinking = UI-only
- stream = transport mode

5) summaus
- think ei toimi ilman streamia
- stream = false sammuttaa thinkin
- view_thinking ei saa vaikuttaa parseriin tai payloadiin

stream = gate
think = payload-intent
view_thinking = UI-only
