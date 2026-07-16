# Piano DB — Bottone PDF data-driven via capabilities (`pdf_mode` + `pdf_allow_allegati`, 5 domini vendite)

> **Tipo**: piano di sviluppo (slice DB su `dev/db-tid` + handoff FE) · **Data**: 2026-07-10 · **Owner**: Tid
> **Stato**: ✅ CHIUSO (DB applicato+committato 5 domini + lista Ordini; FE recepito §10) — spostato in `work-done`.
> **Origine**: brief «Bottone PDF data-driven via capabilities» + analisi critica 2026-07-10.
> **Design-of-record**: questo documento (rifinisce il brief: seed verbatim, non la sua tabella
> indicativa; secondo asse `pdf_allow_allegati`; `NOT NULL` senza default).
> **Gate**: la slice FE di consumo parte **dopo** l'applicazione DB
> ([[feedback_be_fe_attende_prerequisiti_db]]).
> **Regola d'oro**: nessuna migrazione/commit senza «procedi» esplicito
> ([[feedback_no_commit_autonomo]]).

---

## 1. Scopo

Portare nel modello la mappa **stato → modalità bottone PDF**, oggi **hardcoded nel FE** per 5
domini (`STATI_*_ANTEPRIMA_PDF` / `STATI_*_CON_DOCUMENTO` / `STATI_*_APPEND_ALLEGATI` in
`frontend/src/vendite/**/constants.js`). La verità va dove sta già `available_actions`: nelle
capabilities `script.fn_available_actions_*`. Così aggiungere/rifasare uno stato non fa più
**degradare silenziosamente** il bottone a `disabled`.

## 2. Analisi critica — sintesi (dettaglio nella conversazione 2026-07-10)

Premessa verificata: le costanti FE sono **liste-di-stati piatte** (nessuna condizione) → mapping
1:1 fattibile; le 5 `fn_available_actions_*` esistono con struttura jsonb uniforme; la colonna è
**giustificata** (non derivabile da `fase`/`terminale`: `EVASO` e `ANNULLATO` sono entrambi
terminali ma ARCHIVE vs NONE).

Rilievi recepiti come **decisioni Tid**:

| # | Rilievo | Decisione |
| --- | --- | --- |
| 1 | La tabella §2.2 del brief **contraddice** le costanti reali (per preventivi `ANNULLATO`/`SCADUTO`/`RIFIUTATO` sono oggi **ARCHIVE**, non NONE) | **Seed verbatim** da ogni `constants.js`; la tabella del brief è solo indicativa |
| 2 | Esiste un **quarto asse** `statiAppendAllegati` che `pdf_mode` non esprime → §3 «costanti eliminate» non raggiunto | **Secondo campo `pdf_allow_allegati boolean`** |
| 3 | `DEFAULT 'NONE'` reintroduce il degrado silenzioso (nuovo stato senza valore → disabled) | **`NOT NULL` senza default** (default transitorio solo per il backfill, poi droppato) |

## 3. Modello — 2 colonne su ciascuna delle 5 `config.stati_doc_*`

Tabelle: `stati_doc_preventivi`, `stati_doc_offerte`, `stati_doc_contratti`,
`stati_doc_ordini`, `stati_doc_ddt`.

```sql
pdf_mode           varchar NOT NULL CHECK (pdf_mode IN ('PREVIEW','ARCHIVE','NONE'))
pdf_allow_allegati boolean NOT NULL
```

- **`pdf_mode`**: `PREVIEW` (bozza, anteprima on-the-fly non persistita) · `ARCHIVE` (PDF già
  generato all'emissione, apre gestione documenti) · `NONE` (nessuna gestione, es. annullati).
- **`pdf_allow_allegati`**: abilita l'append allegati nel dialog archivio (oggi solo offerta
  `EMESSA`); ortogonale a `pdf_mode`.

**Migrazione — `NOT NULL` senza default, ordine-safe** (00_schema gira **prima** di 80_data):
per ogni tabella un changeSet `00_schema/config` che, in un colpo:

1. `ALTER … ADD COLUMN pdf_mode varchar NOT NULL DEFAULT 'NONE' CHECK (…)` (il default
   **transitorio** valorizza le righe esistenti e rende la colonna subito `NOT NULL`);
2. `ALTER … ADD COLUMN pdf_allow_allegati boolean NOT NULL DEFAULT false`;
3. `ALTER … ALTER COLUMN pdf_mode DROP DEFAULT` e idem `pdf_allow_allegati`.

Esito finale: colonne `NOT NULL` **senza default** → ogni futuro `INSERT` di stato **deve**
dichiarare i due valori (definizione-stato e comportamento-PDF non possono divergere). Il
`DROP DEFAULT` non azzera le righe esistenti (mantengono il valore transitorio), che il seed §4
poi corregge. Il lock-columns su `stati_doc_*` blocca solo `codice_interno` → le UPDATE del seed
passano.

> Un changeSet per file, `logicalFilePath`, numerazione **globale per data**
> ([[feedback_liquibase_numerazione_globale_per_data]]); `runOnChange:false` nello stato finale.

## 4. Seed — verbatim dalle costanti FE (80_data, CSV)

I 5 loader stati sono `runOnChange:true` + `loadUpdateData` → **aggiungere le 2 colonne a ciascun
CSV `80_data/sql/config/stati_doc_*.csv`** e alla lista colonne del loader; il changeSet
`runOnChange` ri-applica ([[feedback_seed_80_data_csv]], [[feedback_messaggi_errore_no_new_loader]]).
Valori trascritti **1:1** dalle costanti vive (default implicito per gli stati non elencati:
`NONE` / `false`):

| Dominio | `pdf_mode=PREVIEW` | `pdf_mode=ARCHIVE` | `pdf_allow_allegati=true` |
| --- | --- | --- | --- |
| **ordini** | `DRAFT` | `CONFERMATO, EVASO, ALLOCATO, SPEDITO, CONSEGNATO, FATTURATO` | — |
| **ddt** | `DRAFT` | `EMESSO, SPEDITO, CONSEGNATO, RESO` | — |
| **offerte** | `BOZZA` | `EMESSA, ACCETTATA, RIFIUTATA, SUPERATA, ANNULLATA` | `EMESSA` |
| **preventivi** | `DRAFT` | `EMESSO, ACCETTATO, EVASO, RIFIUTATO, SCADUTO, ANNULLATO` | — |
| **contratti** | `DRAFT` | `ATTIVO, CESSATO` | — |

Fonti (da rileggere all'attuazione, sono la single source):
`frontend/src/vendite/ordini/constants.js`, `…/ddt/constants.js`, `…/offerte/constants.js`,
`frontend/src/vendite/constants.js` (preventivi + contratti). Tutto ciò che non compare → `NONE`.

> ⚠️ **Stati «orfani» dal FE — decidere consapevolmente, NON copiare il bug.** Alcuni stati
> non sono in **nessuna** lista FE perché aggiunti dopo (es. `stati_doc_ordini.PARZIALMENTE_EVASO`,
> introdotto dalla slice DDT/orfano-push): «verbatim» li manderebbe a `NONE` (bottone disabled) —
> che è **proprio il degrado silenzioso** che questa slice combatte. Assegnarli al valore
> **corretto** e documentarlo: `PARZIALMENTE_EVASO → ARCHIVE` (post-conferma, il PDF esiste),
> coerente con `CONFERMATO`/`EVASO`. Fare la stessa verifica su ogni tabella (confronto
> `config.stati_doc_* ↔ liste FE` = elenco degli orfani da classificare a mano).

## 5. Capabilities — blocco `pdf` nelle 5 fn (20_code)

Estendere `script.fn_available_actions_{preventivo,offerta,contratto,ordine,ddt}` con, letti
dallo stato corrente (JOIN già presente in ognuna):

```json
"pdf": { "mode": "PREVIEW|ARCHIVE|NONE", "allow_allegati": true|false }
```

Pura proiezione config→capability, zero logica aggiuntiva (stesso stile di `can_edit_testata`).

> ⚠️ **Ribasare sulle versioni correnti** (regola DDL-da-doc-autogen): `fn_available_actions_ordine`
> è stata appena modificata (`20260710-02`, decoupling push) e `fn_available_actions_ddt` è nuova
> (`20260709`). Copiare il corpo dalla doc auto-gen `dbzero`, **non** da YAML stale, per non
> regredire le revisioni intermedie ([[feedback_no_hand_edit_autogen_docs]] per la lettura).

## 6. pgTAP

- **Pilota DDT** (`test-…-ddt-pdf-capability.sql`): il blob espone `pdf.mode` coerente col seed
  per `DRAFT`→PREVIEW, `EMESSO`→ARCHIVE, `ANNULLATO`→NONE; `pdf.allow_allegati=false`.
- **Smoke sugli altri 4**: un caso ARCHIVE + un caso NONE ciascuno; per **offerte** un caso
  `allow_allegati=true` (EMESSA) — il seed è la superficie di rischio, va coperto su tutti.
- **Guard modello**: `INSERT` di uno stato senza `pdf_mode` → errore `NOT NULL` (blinda il §3).

## 7. Handoff FE (slice a valle — GATE: DB applicato)

`EntityPdfButton` riceve `pdf.mode` / `pdf.allow_allegati` dal detail (già contiene il blob
capabilities in tutti i drawer della famiglia). **Eliminare** dai 5 `constants.js` le 3 famiglie
`STATI_*_{ANTEPRIMA_PDF, CON_DOCUMENTO, APPEND_ALLEGATI}` e i loro passaggi come prop
(`stati-preview` / `stati-con-documento` / `stati-append-allegati`). Progetto non in produzione →
switch big-bang, nessun dual-path ([[project_no_produzione_solo_sviluppo]]). Nota naming: il FE usa
il valore modalità `'scarica'` per l'archivio → mappare `ARCHIVE → 'scarica'`.

## 8. Rischi / note

- **Fedeltà seed**: unico rischio reale. Trascrivere dalle costanti vive (§4), non dalla tabella
  indicativa del brief; classificare gli stati orfani (§4 warning).
- **Idempotenza**: CSV `loadUpdateData` per `id` → ri-applicazione sicura.
- **Nessun impatto RLS/guard**: colonne di presentazione-lifecycle su lookup di dominio `config`.

## 9. Stato avanzamento

- [x] Analisi critica + decisioni (2 colonne, NOT NULL no-default, seed verbatim)
- [x] Fase A — 5 changeSet `00_schema/config` `20260711-01..05` (ADD NOT NULL DEFAULT transitorio + DROP DEFAULT + CHECK)
- [x] Fase B — 5 CSV `80_data` aggiornati (verbatim + orfano `PARZIALMENTE_EVASO`→ARCHIVE) + **2 colonne pdf aggiunte alla lista colonne dei loader esistenti** (`runOnChange`, ri-applicano): `20250917-01` (preventivi), `20260524-04` (offerte), `20260520-08` (contratti), `20250912-02` (ordini), `20250915-01` (ddt)
- [x] Fase C — 5 fn `20_code/script` `20260711-07..11` (blocco `pdf {mode, allow_allegati}`, ribasate su versioni correnti incl. decoupling ordine)
- [x] Fase D — pgTAP: `config/test-stati-doc-pdf-mode-v1.sql` (plan 22: NOT NULL + no-default + CHECK + guard §3 + seed ×5) e `script/test-fn-available-actions-pdf-v1.sql` (plan 5: pilota DDT DRAFT→PREVIEW / EMESSO→ARCHIVE)
- [x] Applicazione DB Tid + pgTAP verdi — **✅ applicato e committato** (5 domini) + brief lista Ordini eseguito ([[brief-db-pdf-mode-lista-ordini]], `vw_ordini_lista.pdf_mode`)
- [x] Slice FE (handoff §7) — **✅ realizzata** (vedi §10)

### Consuntivo scrittura (2026-07-11)

Deliverable DB scritti su `dev/db-tid`, **non applicati né committati**. ChangeSet `20260711-01..05`
(schema) + `20260711-07..11` (fn) + 5 CSV editati + **5 loader stati esistenti estesi** (colonne pdf)
+ 2 pgTAP. Note di attuazione:

- **Loader esistenti, non nuovi**: i loader `stati_doc_*` sono `runOnChange:true` + `validCheckSums:ANY`
  → si **modificano sul posto** aggiungendo le 2 colonne pdf alla lista (è il meccanismo previsto,
  non una violazione del "no-edit changelog mergiati", che vale per i changeSet a checksum-sequenza).
  Modificare CSV **e** lista colonne cambia il checksum → il loader ri-esegue e carica i valori pdf.
  (Il primo tentativo aveva creato un loader parallelo `20260711-06`: rimosso, era ridondante.)
- **Ordinamento**: `00_schema` (ADD colonne) gira prima di `80_data` (seed) → le colonne esistono
  quando i loader caricano.
- **Scostamento cosciente dal verbatim**: `stati_doc_ordini.PARZIALMENTE_EVASO` (orfano dalle liste
  FE) è seedato `ARCHIVE`, non `NONE` (piano §4 warning). Da rivalutare se emergono altri orfani.
- **Verifica boolean**: `pdf_allow_allegati` seedato con `t`/`f` (stile `attivo`) + `type: BOOLEAN`
  nel loader.
- **Doc auto-gen dbzero**: la rigenera Tid dopo l'applicazione (le 5 fn + 5 tabelle cambiano).

### Revisione 2026-07-16 — normalizzazione `ANNULLATO → ARCHIVE` (supera il verbatim)

Origine: [[brief-db-pdf-mode-contratti-annullato-archive]] (regressione FE — rimosse le aree
inline "Documenti generati" dai drawer Preventivi/Contratti: un annullato con PDF generati
perdeva l'accesso all'archivio).

**Il brief chiedeva il solo flip contratti** sul presupposto "asimmetria contratti-vs-preventivi
= svista". L'analisi ha mostrato che il presupposto era errato: `NONE` sull'annullato era un
**pattern su 3 domini** (contratti, ordini, DDT) contro 2 (preventivi, offerte) — nessuno dei
due deciso nel merito, entrambi **verbatim** dalle costanti FE (§2 rilievo #1). Fare il solo
contratti avrebbe lasciato la stessa regressione latente su ordini/DDT.

**Decisione Tid**: regola unica su tutti e 5 i domini — *annullare non cancella la storia,
l'archivio PDF di un documento annullato resta consultabile* (già vero per preventivi/offerte).
`contratti/ordini/ddt.ANNULLATO`: `NONE → ARCHIVE`, `pdf_allow_allegati` invariato (`f`).
Scostamento cosciente dal verbatim, come già fatto per `PARZIALMENTE_EVASO` (§4 warning:
«decidere consapevolmente, NON copiare il bug»).

> ⚠️ **Conseguenza sulla giustificazione della colonna (§2).** Il razionale «la colonna è
> giustificata perché non derivabile da `fase`/`terminale` (`EVASO` e `ANNULLATO` entrambi
> terminali ma ARCHIVE vs NONE)» poggiava **esattamente** su queste 3 celle: erano le uniche
> non-derivabili del modello (preventivi e offerte erano già 100% derivabili). Dopo la
> normalizzazione `pdf_mode ≡ (fase = 'APERTO' ? PREVIEW : ARCHIVE)` su tutti e 5 i domini,
> e `NONE` non è più usato da nessuno stato (resta valido nel CHECK).
> **Non ritirata**: resta come asse di **policy/configurazione** (parametrizzazione consapevole
> ≠ logica duplicata) — è la tesi originale del piano: data-driven, nessun degrado silenzioso,
> un nuovo stato può dichiarare un comportamento PDF diverso senza toccare il codice.
> Da **rivalutare** se resta derivabile a lungo: in tal caso la colonna diventerebbe
> duplicazione di `fase` e andrebbe ritirata (impatto: 5 tabelle, 5 `fn_available_actions_*`,
> pgTAP plan 22, consumatori FE). Decisione rinviata al 2° segnale.

Deliverable: 3 CSV (`stati_doc_{contratti,ordini,ddt}.csv`) — nessun loader nuovo, nessun
changeSet (loader `runOnChange` esistenti ri-applicano). pgTAP `test-stati-doc-pdf-mode-v1.sql`
test **17/19/22** aggiornati a `ARCHIVE`; il **21** non è più etichettato «quirk». `plan(22)`
invariato.

## 10. Consuntivo FE (2026-07-11) — ✅ REALIZZATO

Recepimento FE della capability su `dev/backend-tid` (**non committato**). Build Vite verde,
eslint pulito. **Zero modifiche BE**: il blob `pdf` è spread `**capabilities` nei 5 service e
`pdf_mode` viaggia in lista via `SELECT v.*` + `DictField()`.

- **`EntityPdfButton`** (BB `documenti/components`): da `statoCodice` + 3 array `STATI_*` a
  un'unica prop `pdf` = `{mode, allow_allegati}`; enum **`PDF_MODE`** centralizzato in
  `documenti/constants.js` (single source dei literal, consumato anche dalla lista).
- **5 drawer** (Ordini/Ddt/Offerta/Contratto/Preventivi): `:pdf="detail.pdf"`, rimossi
  `:stato-codice`/`:stati-*` e import.
- **Lista Ordini** (`OrdiniSearchTable`): `row.pdf_mode === PDF_MODE.ARCHIVE` (colonna
  `vw_ordini_lista.pdf_mode`, brief lista [[brief-db-pdf-mode-lista-ordini]] eseguito).
- **5 `constants.js`**: eliminate tutte le famiglie `STATI_*_{ANTEPRIMA_PDF, CON_DOCUMENTO,
  APPEND_ALLEGATI}` → nessuna mappa stato→PDF hardcoded residua.
- **Cambio comportamento cosciente**: in lista Ordini `PARZIALMENTE_EVASO` ora ha PDF abilitato
  (`pdf_mode=ARCHIVE`); prima era escluso → disabled.
