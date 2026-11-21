# Addendum brief DB — `chk_oce_comp_origine` manca `LISTINO_BUNDLE`

> **Branch**: `dev/db-tid`. **Stato**: bug runtime, INSERT componente
> eccezione composita rifiutato.
> **Errore**: `viola il vincolo di controllo "chk_oce_comp_origine"` con
> `origine_prezzo = 'LISTINO_BUNDLE'`, sollevato da
> `fn_offerta_eccezione_componenti_init` (INSERT del componente con prezzo
> risolto dal resolver bundle-aware).

---

## Gap

Il CHECK `chk_oce_comp_origine` su
`vendite.offerte_commerciali_eccezioni_componenti` (migration
`20260526-22`) ammette:

```
PROMO, CONTRATTO_OVERRIDE, CONTRATTO_LISTINO, CATEGORIA, MANUALE
```

Manca `LISTINO_BUNDLE`. Il commento del DDL dice "stesso CHECK di
contratti" ma e' stato copiato dalla versione **pre-bundle**: i
contratti hanno aggiunto `LISTINO_BUNDLE` con la migration `20260513-21`
(`chk_contrighe_comp_origine`), quando e' stato introdotto lo STADIO
BUNDLE del resolver.

`fn_resolve_prezzo_listino_v2(..., p_articolo_padre_contesto)` ritorna
`origine = 'LISTINO_BUNDLE'` per i componenti il cui prezzo viene da
`vendite.listini_righe_componenti`. La fn init scrive quell'origine →
viola il CHECK offerte.

## Fix richiesto

Migration nuova `00_schema` (numero progressivo, non modificare la
`20260526-22` gia' pushata): DROP + ADD del CHECK allineato a contratti.

```sql
ALTER TABLE vendite.offerte_commerciali_eccezioni_componenti
    DROP CONSTRAINT IF EXISTS chk_oce_comp_origine;
ALTER TABLE vendite.offerte_commerciali_eccezioni_componenti
    ADD CONSTRAINT chk_oce_comp_origine
    CHECK (origine_prezzo IN (
        'PROMO', 'CONTRATTO_OVERRIDE', 'CONTRATTO_LISTINO',
        'CATEGORIA', 'MANUALE', 'LISTINO_BUNDLE'
    ));
```

Speculare a `20260513-21` sui contratti.

## Lato BE/FE

Nessuna modifica: il valore `LISTINO_BUNDLE` e' gia' gestito dal modello
(la colonna `origine_prezzo` e' solo decorata nelle proiezioni). Dopo il
merge il flusso CREATE eccezione composita completa l'INSERT figli e il
trigger ricalcola il prezzo padre.

---

*Addendum DB — allineamento CHECK origine componenti offerta a contratti
(STADIO BUNDLE). Tempo stimato: 5 minuti. Pronto per `dev/db-tid`.*
