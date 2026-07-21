# Brief DB — Correzione hardcode su colonna `codice` → `codice_interno` (16 oggetti)

> **Per**: team DB (`dev/db-tid`). · **Da**: backend agent. · **Priorità**: 🔴 alta (bug
> logici latenti). · **Data**: 2026-06-28.
> **Origine**: `analisi-hardcoded-codice.md` §3a. Classe DIVERSA dal brief naming
> (`brief-naming-stato-codice-interno.md`, che corregge gli *alias* `codice_interno AS *_codice`).
> Qui la logica **legge/filtra per `codice` (mutabile)** dove deve usare `codice_interno`.

---

## 1. Cosa fare (regola unica)

In ogni occorrenza sotto, sostituire il confronto **`<alias>.codice` → `<alias>.codice_interno`**
(lasciando invariato il literale). Tutte le tabelle coinvolte sono dual-column: hanno già
`codice_interno` (NOT NULL, UNIQUE, lockata da `trgfn_lock_columns`).

**⚠️ Pre-check obbligatorio prima di applicare**: verificare che, per ogni tabella/literale,
il valore esista identico in `codice_interno`. Atteso sì (i valori `DRAFT/ATTIVO/PREVENTIVO/…`
sono i `codice_interno` per convenzione, cfr. brief naming §1), ma confermare con:

```sql
-- esempio per config.sorgenti
SELECT codice, codice_interno FROM config.sorgenti
 WHERE codice IN ('PREVENTIVO','ORDINE_VENDITA','DDT_VENDITA','CONTRATTO','COMMESSA','ATTIVITA_CONSUMI');
-- atteso: codice = codice_interno per ogni riga. Se differiscono, usare il valore di codice_interno.
```

ZeroERP non è in produzione → modifica diretta delle definizioni vive (`CREATE OR REPLACE`
per fn/trigger/jsonb; per le viste con sola modifica di espressione `WHERE/JOIN` basta
`CREATE OR REPLACE VIEW`). Nessun cambio di firma o di colonne → niente cascade.

## 2. Oggetti da correggere

> Path = `docs/it/dbzero/...` (SQL vivo autogen). Riga indicativa sullo snapshot 2026-06-28.

### config.sorgenti (8 occorrenze — `s.codice` → `s.codice_interno`)

| Oggetto | Riga | Snippet attuale |
| --- | --- | --- |
| `vendite/funzioni/fn_list_preventivi_da_pushare` | 80 | `FROM config.sorgenti s WHERE s.codice = 'PREVENTIVO' AND s.attivo IS TRUE` |
| `vendite/funzioni/fn_list_ordini_da_pushare` | 32 | `... WHERE s.codice = 'ORDINE_VENDITA' ...` |
| `vendite/funzioni/fn_list_contratti_da_pushare` | 32 | `... WHERE s.codice = 'CONTRATTO' ...` |
| `vendite/funzioni/fn_list_ddt_da_pushare` | 31 | `... WHERE s.codice = 'DDT_VENDITA' ...` |
| `vendite/funzioni/fn_list_consumi_da_pushare` | 34 | `... WHERE s.codice = 'ATTIVITA_CONSUMI' ...` |
| `vendite/funzioni/fn_emit_attivita_fatturabili_da_commessa` | 71 | `... WHERE s.codice = 'COMMESSA' ...` |
| `vendite/funzioni/trgfn_documenti_sync_canali` | 47-50 | `CASE WHEN s.codice = 'PREVENTIVO'/'ORDINE_VENDITA'/'DDT_VENDITA'/'CONTRATTO' THEN s.id END` (4 rami) |
| `vendite/funzioni/fn_set_documento_canale_stato` | 67 | `... WHERE s.codice = v_canale ...` (qui `v_canale` è un *_codice mutabile in ingresso: confrontare con `codice_interno`; verificare che il chiamante passi il codice_interno del canale — vedi §3) |
| `vendite/views/vw_preventivi_pratiche` | 23 | `JOIN config.sorgenti s ON ((s.codice)::text = 'PREVENTIVO'::text AND s.attivo IS TRUE)` |

### config.stati_doc_* (stati documento)

| Oggetto | Riga | Tabella | Snippet |
| --- | --- | --- | --- |
| `vendite/funzioni/fn_cambia_stato_preventivo` | 79 | `stati_doc_preventivi` | `... WHERE codice = p_nuovo_stato ...` (+ verificare i literali `DRAFT/EMESSO/ANNULLATO` nel corpo) |
| `vendite/funzioni/fn_crea_revisione_preventivo` | 94, 110 | `stati_doc_preventivi` | `... sdp2.codice = 'DRAFT'` (94) e `WHERE codice = 'DRAFT'` (110) |
| `vendite/funzioni/fn_list_preventivi_da_pushare` | 92 | `stati_doc_preventivi` | `... WHERE s.codice = 'ACCETTATO' ...` |
| `vendite/funzioni/fn_list_ordini_da_pushare` | 44 | `stati_doc_ordini` | `... WHERE s.codice = 'CONFERMATO' ...` |
| `vendite/funzioni/fn_list_contratti_da_pushare` | 44 | `stati_doc_contratti` | `... WHERE s.codice = 'ATTIVO' ...` |
| `vendite/funzioni/fn_list_ddt_da_pushare` | 107 | `stati_doc_ddt` | `... sdd.codice IN ('SPEDITO', 'CONSEGNATO')` |

### config.tipi_ruoli

| Oggetto | Riga | Snippet |
| --- | --- | --- |
| `anagrafiche/funzioni/fn_lookup_utilities_per_ba` | 93 | `JOIN config.tipi_ruoli tr_ef ON tr_ef.id = utr_ef.tipo_ruolo_id AND tr_ef.codice = 'EF'` |

## 3. Note / attenzioni

- **`fn_cambia_stato_preventivo`** è lo state-machine entrypoint: dentro confronta sia il
  parametro in ingresso (`p_nuovo_stato`) sia literali. Verificare TUTTO il corpo della fn,
  non solo la riga 79. Il parametro `p_nuovo_stato` dovrebbe già viaggiare come
  `codice_interno` dal BE; se così, il confronto va contro `codice_interno`.
- **`fn_set_documento_canale_stato`** (riga 67): `v_canale` proviene da un canale_codice.
  Confermare con il BE/chiamante che il valore passato sia il `codice_interno` del canale;
  altrimenti l'allineamento va fatto a monte. Segnalare se serve coordinamento.
- **`trgfn_documenti_sync_canali`**: 4 rami CASE, correggerli tutti.
- Riproduzione fedele del resto del corpo (alcune fn sono lunghe, es. `fn_list_*` con
  `RETURNS TABLE`): usare il SQL autogen come sorgente, mantenere firma/colonne invariate.

## 4. Verifica post-modifica

- pgTAP / test DB verdi.
- Smoke pipeline push→fatturazione (collegato a `a-test-push-commesse-fatturazione.md`):
  la creazione lotto / risoluzione sorgente-stato deve continuare a funzionare.
- **Test anti-regressione** (consigliato): rinominare temporaneamente in un DB di prova un
  `codice` (es. `config.sorgenti` PREVENTIVO→PREV) e verificare che la pipeline **non** si
  rompa (oggi si romperebbe). Poi ripristinare.
- Guardrail: questa classe NON è intercettata dal guardrail naming esistente
  (`check_naming_stato_codice.sql`, che cerca solo alias). Valutare un secondo check
  catalog-based che segnali `\.codice\s*(=|IN)\s*'...'` su tabelle dual-column (escludendo
  i lookup generici). Opzionale, non bloccante per questo brief.

## 5. Fuori scope (NON in questo brief)

- I **5 punti Backend Python** (`analisi-hardcoded-codice.md` §3b) → a carico backend agent.
- I **`CANDIDATE_ADD_CI`** (§4: `profili_accesso` SUPER_ADMIN, `email_account` SISTEMA,
  `categorie_clienti` STANDARD) → richiedono decisione (aggiungere `codice_interno` vs lock);
  brief separato dopo la scelta di Tid.
- Mislabel **alias** → già coperto da `brief-naming-stato-codice-interno.md` (sweep completo).

---

*Brief DB hardcode `codice`→`codice_interno` — 16 oggetti (8× config.sorgenti, 6× stati_doc_*,
1× tipi_ruoli). Riferimento: `analisi-hardcoded-codice.md` §3a.*
