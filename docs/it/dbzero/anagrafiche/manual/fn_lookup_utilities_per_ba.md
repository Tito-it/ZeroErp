# fn_lookup_utilities_per_ba

### Scopo

Combo "**utility per billing account**" introdotta dal refactor del 2026‑04‑08 (sezione 3 del [WIP](/dev/work-in-progress/refactor-operatore-emittenti)). Restituisce le utility selezionabili per un BA, vincolate al **doppio ruolo**:

1. il ruolo del soggetto del BA (cliente, fornitore, gestore, ecc.) → presente in `config.utilities_tipi_ruolo`
2. il ruolo `EF` dell'emittente fiscale collegato al BA → presente in `config.utilities_tipi_ruolo`

Le righe sono **decorate** con i parametri di override di `anagrafiche.emittenti_fiscali_utilities` quando esistono per la coppia (emittente, utility) — politica ibrida: utility ammesse senza override **rimangono visibili** (l'app applicherà i default di sistema).

## Schema

`anagrafiche` (specifica del dominio fatturazione, riusa `fn_get_emittente_fiscale_pk`).

## Firma

```sql
anagrafiche.fn_lookup_utilities_per_ba(
    p_billing_account_id      anagrafiche.billing_account.id%TYPE,
    p_ruolo_codice_soggetto   text
)
RETURNS TABLE (
    utility_id                     bigint,
    codice                         text,
    descrizione                    text,
    is_personalizzata_per_ef       boolean,
    minimo_soglia_min              numeric,
    minimo_soglia_max              numeric,
    arrotondamento_importi_dec     smallint,
    metodo_arrotondamento_importi  text
)
```

## Parametri

| Parametro                 | Tipo                 | Obbligatorio | Descrizione                                                              |
| ------------------------- | -------------------- | :----------: | ------------------------------------------------------------------------ |
| `p_billing_account_id`    | `billing_account.id` |      Si      | Identificativo del BA. Deve essere `> 0`.                                |
| `p_ruolo_codice_soggetto` | `text`               |      Si      | Codice del ruolo del soggetto del BA: `'CL'`, `'FO'`, `'GE'`, `'RS'`, ... |

## Logica

1. **Guard input**: parametri obbligatori, errore `E_PARAMETRO_INVALIDO` altrimenti.
2. **Risoluzione emittente del BA** tramite [`anagrafiche.fn_get_emittente_fiscale_pk`](/dbzero/anagrafiche/funzioni/fn_get_emittente_fiscale_pk):
   - mapping specifico in `emittenti_fiscali_billing_account` →
   - fallback default globale (riga `is_default = true`).
   - Solleva `E_EMITTENTE_DEFAULT_MISSING` se nessun emittente è risolvibile.
3. Conversione PK → `soggetto_ruolo_id` per il join con la matrice utility.
4. Query principale:
   - `JOIN config.utilities u`
   - `JOIN config.utilities_tipi_ruolo utr_sogg` (ruolo soggetto, attivo, periodo di validità corrente)
   - `JOIN config.utilities_tipi_ruolo utr_ef` (ruolo `EF`, attivo, periodo di validità corrente)
   - `LEFT JOIN anagrafiche.emittenti_fiscali_utilities efu` (override parametri per emittente, attivo)
5. Output ordinato per `u.codice`.

## Politica ibrida

| Caso                                                                                  | Visibilità                  | `is_personalizzata_per_ef` | Parametri override |
| ------------------------------------------------------------------------------------- | --------------------------- | :------------------------: | ------------------ |
| Utility ammessa per ruolo soggetto **e** ruolo EF, **con** riga in `efu`              | ✅ visibile                 | `true`                     | popolati           |
| Utility ammessa per ruolo soggetto **e** ruolo EF, **senza** riga in `efu`            | ✅ visibile                 | `false`                    | NULL (default app) |
| Utility ammessa solo per ruolo soggetto, non per ruolo EF (o viceversa)               | ❌ esclusa                  | —                          | —                  |

## Caratteristiche

* **STABLE**: solo lettura.
* **Filtro periodo validità**: solo righe attive con `valido_dal/valido_al` correnti.
* **Riusa `fn_get_emittente_fiscale_pk`** (filtra `ef.attivo`) per coerenza con la pipeline fatturazione.

## Dipendenze

* [`anagrafiche.fn_get_emittente_fiscale_pk`](/dbzero/anagrafiche/funzioni/fn_get_emittente_fiscale_pk)
* `anagrafiche.emittenti_fiscali`
* `anagrafiche.emittenti_fiscali_utilities` — override parametri per emittente
* `anagrafiche.emittenti_fiscali_billing_account` — risoluzione mapping (via `fn_get_emittente_fiscale_pk`)
* `config.utilities`
* `config.utilities_tipi_ruolo`
* `config.tipi_ruoli` — lookup `codice = 'EF'` e `codice = p_ruolo_codice_soggetto`

## Chi la chiama

* Backend Python: `LookupRepository.list_utilities_per_billing_account(ba_id, ruolo_codice)` (vedi [refactor WIP §5.2](/dev/work-in-progress/refactor-operatore-emittenti)).
* Endpoint `GET /api/v1/anagrafiche/billing-account/{id}/utilities/?ruolo=CL`.
* Frontend: drawer `ClienteDrawer.vue`, `FornitoreDrawer.vue`, `ClientiSearchTable.vue` (vedi WIP §3.5).

## Esempio

```sql
-- Utility selezionabili per un BA cliente
SELECT *
  FROM anagrafiche.fn_lookup_utilities_per_ba(123, 'CL');

-- Utility selezionabili per un BA fornitore
SELECT *
  FROM anagrafiche.fn_lookup_utilities_per_ba(456, 'FO');
```
