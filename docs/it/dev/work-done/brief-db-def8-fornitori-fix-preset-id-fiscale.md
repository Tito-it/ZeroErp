# Brief DB — DEF-8 fornitori: fix preset, colonna visibile da `codice_fiscale` a `id_fiscale`

> **Tipo**: fix seed (1 UPDATE su `ui.lista_preset_colonna`).
> **Branch**: `dev/db-tid`.
> **Autore brief**: backend agent (Tid, sessione 2026-05-24).
> **Origine**: smoke post-applicazione di
> [brief-db-def8-fornitori-catalogo.md](brief-db-def8-fornitori-catalogo.md).
> Errore del backend agent: la tabella "Step 5 — lista_preset_colonna"
> nel brief originale non era stata aggiornata coerentemente con la tabella
> "Step 3 — lista_colonna" dopo la decisione di rinominare la colonna
> unificata da `codice_fiscale` a `id_fiscale`.

## Diagnosi

Catalogo applicato correttamente (15 colonne, `id_fiscale` con
`campo_sorgente='id_fiscale_univoco_cf_piva'`), ma il preset di sistema
`fornitori_default` ha come terza colonna visibile `codice_fiscale`
(CF puro), non `id_fiscale` (versione unificata CF/PIVA).

Risultato: la lista fornitori mostra la colonna "Codice fiscale" vuota
per quasi tutti i fornitori azienda (che hanno solo P.IVA, non CF
separato). Comportamento opposto a quello voluto.

Verifica live:

```sql
SELECT lc.codice AS colonna, lpc.visibile
  FROM ui.lista_preset_colonna lpc
  JOIN ui.lista_colonna lc ON lc.id = lpc.colonna_id
  JOIN ui.lista_preset lp ON lp.id = lpc.preset_id
  JOIN ui.lista_definizione ld ON ld.id = lp.lista_id
 WHERE ld.codice='anagrafiche.fornitori' AND lpc.ordine = 30;
-- attuale: codice_fiscale | t   <- ERRATO
-- atteso: id_fiscale     | t
```

## Modifica richiesta

Sostituire nel preset `fornitori_default` il riferimento alla colonna
`codice_fiscale` con quello alla colonna `id_fiscale` (mantenendo
ordine=30, larghezza=160, visibile=true, fissata=false).

Equivalente SQL (UPDATE puntuale, no INSERT/DELETE):

```sql
UPDATE ui.lista_preset_colonna lpc
   SET colonna_id = (
         SELECT lc.id
           FROM ui.lista_colonna lc
           JOIN ui.lista_definizione ld ON ld.id = lc.lista_id
          WHERE ld.codice = 'anagrafiche.fornitori'
            AND lc.codice = 'id_fiscale'
       )
 WHERE lpc.preset_id = (
         SELECT lp.id FROM ui.lista_preset lp
         JOIN ui.lista_definizione ld ON ld.id = lp.lista_id
         WHERE ld.codice = 'anagrafiche.fornitori'
           AND lp.codice = 'fornitori_default'
       )
   AND lpc.colonna_id = (
         SELECT lc.id
           FROM ui.lista_colonna lc
           JOIN ui.lista_definizione ld ON ld.id = lc.lista_id
          WHERE ld.codice = 'anagrafiche.fornitori'
            AND lc.codice = 'codice_fiscale'
       );
```

In alternativa, se il seed CSV `80_data/sql/ui/lista_preset_colonna.csv`
permette UPSERT su (preset_id, colonna_id), aggiornare la riga
corrispondente sostituendo `colonna_codice` da `codice_fiscale` a
`id_fiscale`.

## Effetto post-fix

`fn_resolve_lista_config('anagrafiche.fornitori', <user>, NULL)` ritorna
nella terza colonna `id_fiscale` con `campo_sorgente='id_fiscale_univoco_cf_piva'`.
Il FE `<ListaConfigurabile>` legge `data[campo_sorgente]` -> mostra il
valore unificato CF/PIVA (P.IVA per fornitori azienda, CF per persone
fisiche, quale dei due e' valorizzato).

`codice_fiscale` resta nel catalogo come colonna extra opt-in (l'utente
che vuole vedere il CF puro separato puo' attivarlo da Personalizza
Colonne).

## Smoke post-fix

```sql
-- Conta colonne risolte: deve restare 15 totali (no add/remove, solo swap)
SELECT jsonb_array_length(
  ui.fn_resolve_lista_config('anagrafiche.fornitori', 1, NULL) -> 'colonne'
) AS n_colonne;
-- atteso: 15 (7 visibili nel preset + 8 extra merge nascoste)

-- Terza colonna visibile = id_fiscale
SELECT (ui.fn_resolve_lista_config('anagrafiche.fornitori', 1, NULL)
        -> 'colonne' -> 2 ->> 'codice') AS terza_colonna;
-- atteso: id_fiscale
```

UI: refresh lista fornitori → la colonna "Id. Fiscale" mostra il valore
unificato (es. P.IVA per azienda) invece di restare vuota.

## Riferimenti

- Brief originale: [brief-db-def8-fornitori-catalogo.md](brief-db-def8-fornitori-catalogo.md)
  (gia' aggiornato per coerenza documentale).
- Pattern gemello soggetti: [brief-db-def8-soggetti-fix-id-fiscale.md](brief-db-def8-soggetti-fix-id-fiscale.md)
  (stesso errore di seed sul `campo_sorgente`, simmetrico).
