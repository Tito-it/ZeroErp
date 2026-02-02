# fn_group_attivita_fatturabili (Django) — opzionale

## Scopo
Portare in Django la logica di raggruppamento delle attivita fatturabili.

## Contesto
In DB `vendite.fn_group_attivita_fatturabili()` costruisce la chiave di aggregazione riga.
La migrazione è utile solo se le regole cambiano spesso.

## Input
- riga `attivita_fatturabili`

## Output
- chiave di grouping (hash/tuple)

## Regole
- Deterministica e stabile.
- Versionabile: cambi di regole devono essere tracciati.

## Dipendenze DB
- Tabelle `vendite.attivita_fatturabili` e riferimenti a cataloghi/parametri.

## Note di migrazione
- Se rimane in DB, Django deve solo consumare la chiave.
