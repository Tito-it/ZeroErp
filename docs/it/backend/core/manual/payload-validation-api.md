# Payload validation API (Core Django)

## Scopo
Centralizzare validazioni/coercizioni dei payload JSON API per ridurre logica duplicata nelle view dominio.

## Contesto
Validator condivisi in:
- `apps/core/api/payload_validators.py`

## Input
- `payload: dict`
- chiave campo (`key`)

## Output
- valore coerente (`int`, `bool`, `date`) oppure `ValueError` su input non valido.

## Regole
- Le view non devono parsare tipi a mano: usare validator core.
- Errori di validazione payload vengono tradotti in risposta `invalid_payload`.

## Dipendenze DB
- Nessuna

## Note di migrazione
- Vendite usa i validator core su `run_lotto_pipeline`.
