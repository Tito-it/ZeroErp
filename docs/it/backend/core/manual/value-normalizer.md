# Value normalizer (Core Django)

## Scopo
Centralizzare utility riusabili di normalizzazione valori input.

## Contesto
Utility condivise in:
- `apps/core/services/value_normalizer.py`

## Input
- valori eterogenei (`Any`) da payload/JSON/config

## Output
- `as_bool(...)` -> `bool`
- `empty_to_none(...)` -> valore normalizzato

## Regole
- `as_bool` riconosce `1,true,t,yes,y,on`.
- `empty_to_none` converte stringhe vuote in `None`.

## Dipendenze DB
- Nessuna

## Note di migrazione
- Evita duplicazione di helper equivalenti nelle app dominio.
