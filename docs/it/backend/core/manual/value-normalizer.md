# Value normalizer (Core Django)

## Scopo
Centralizzare utility riusabili di normalizzazione valori input.

## Contesto
Utility condivise in:
- `apps/core/services/value_normalizer.py`

## Input
- valori eterogenei (`Any`) da payload/JSON/config

## Output
- `as_bool(value, default=False)` -> `bool`
- `empty_to_none(value)` -> valore normalizzato

## Regole
- `as_bool`: `None` -> `default`; un `bool` passa invariato; altrimenti `True` se il valore, ripulito dagli spazi e in minuscolo, e' uno fra `1,true,t,yes,y,on`, `False` in tutti gli altri casi.
- `empty_to_none` converte in `None` le stringhe vuote o di soli spazi; gli altri valori passano invariati (le stringhe non vengono ripulite).

## Dipendenze DB
- Nessuna

## Note di migrazione
- Evita duplicazione di helper equivalenti nelle app dominio.
