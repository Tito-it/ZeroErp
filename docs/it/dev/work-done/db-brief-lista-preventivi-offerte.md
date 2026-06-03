# Brief DB — Liste configurabili `vendite.preventivi` + `vendite.offerte` (DB-B, gemelli contratti)

> **Branch**: `dev/db-tid`. **Destinatario**: team DB (eseguito qui).
> **Natura**: brief DB **consolidato e ottimizzato** dei due piani BE/FE gemelli
> [lista-preventivi.md](../work-in-progress/lista-preventivi.md) e [lista-offerte-comm.md](../work-in-progress/lista-offerte-comm.md).
> Unifica il lato DB delle due liste in **un solo lotto** (sono speculari, decisioni
> di principio già ratificate il 2026-06-03).
> **Template DB 1:1**: [refactor-lista-contratti.md](refactor-lista-contratti.md)
> (DEF-8, atterrato 2026-06-02, commit `1cc906377`).
> **Vincolo**: ZeroErp NON in produzione → breaking change ammessi, ma la consegna
> DB resta **non-breaking** verso il BE (vedi §6 sequencing).

---

## ✅ STATO: COMPLETATO — DB ATTERRATO + pgTAP VERDI (2026-06-03)

Lotto DB-B (preventivi + offerte) atterrato su `dev/db-tid` e migrato; test pgTAP
verdi. Archiviato in `work-done`.

| Changeset / artefatto | Cosa |
| --- | --- |
| `20_code/vendite/20260603-05` | vista `vendite.vw_preventivi_lista` (`security_invoker=on`, sorgente `vw_preventivi` per `is_attiva` derivata) |
| `20_code/vendite/20260603-06` | vista `vendite.vw_offerte_commerciali_lista` (self-contained + `is_scaduta` materializzata) |
| `80_data/changelog/20260603-07` | `priorita` dominio preventivi |
| `80_data/changelog/20260603-08` | `priorita` dominio offerte |
| CSV `80_data/sql/ui/*` | append: definizione id=5/6, colonne id 58-78 (prev, 21) / 79-103 (off, 25), preset id=5/6, preset_colonna 13/15 righe |
| pgTAP | `test-lista-preventivi-seed` 14/14 · `test-lista-offerte-seed` 16/16 |

**Trappola risolta in corsa**: prima stesura della vista preventivi leggeva
`p.is_revision_attiva` dalla tabella → `ERRORE: la colonna p.is_revision_attiva
non esiste` (colonna droppata da `20260515-05`). Corretto: sorgente
`vendite.vw_preventivi` + `p.is_attiva` (derivata), no logica duplicata.

**Correzione vs piani WIP**: `tipo_dato='integer'` non esiste nell'ENUM
`ui.tipo_dato` → `rev`/`revisione_numero` seedati come `numeric`.

**Doc manuale aggiornata**: `manual/vw_preventivi_lista.md`,
`manual/vw_offerte_commerciali_lista.md` (nuove) + nota di deprecazione su
`manual/vw_preventivi_list.md` e `manual/vw_offerte_commerciali_list.md`.

**Resta aperto (NON DB)**: BE/FE dei due piani WIP + il **drop differito** delle
viste vecchie (§6 ⚠️ NOTA) dopo la commutazione del backend.

---

## 0. Tesi di ottimizzazione

DB-A (attributo `priorita` + esposizione in `fn_resolve_lista_config`) **è già
atterrato** col refactor contratti (`20260602-13/14`). Resta solo **DB-B × 2**.

Replicare alla cieca il set contratti (5 changeset) per ciascuna lista sarebbe
spreco. L'infrastruttura seed `ui.*` è **condivisa e auto-rieseguibile**:

| Componente | Stato | Conseguenza |
| --- | --- | --- |
| Loader CSV `20260507-06/07/08/09` | `runOnChange:true` + `loadUpdateData` (UPSERT su PK) | **Si appendono righe ai CSV esistenti** — i loader le ricaricano. Zero nuovi loader. È come contratti (righe 36-57 nello stesso `lista_colonna.csv`). |
| Resync sequenze `20260602-17` | `runAlways` | **Nessuna modifica** — riallinea da sé le nuove righe IDENTITY `ui.*`. |
| `fk_index_policy_ui.csv` | invariato | Viste/righe nuove non aggiungono FK. **Nessun tocco.** |

**Artefatti realmente nuovi** (per *entrambe* le liste): **2 viste** + **2 seed
`priorita`** (SQL UPDATE, come `20260602-16`; `priorita` non vive nel CSV) +
**2 file pgTAP**. Più l'**append ai 4 CSV** condivisi.

### Asimmetria di sforzo
- **`vw_preventivi_lista`** = lavoro leggero: la sorgente `vw_preventivi_list`
  esiste già con quasi tutti i campi. Serve solo rinomina canonica + `is_attiva`
  + JOIN emittente + `security_invoker=on`.
- **`vw_offerte_commerciali_lista`** = il vero lavoro DB: vista **self-contained**
  che **materializza** ciò che oggi sta fuori dalla vista — `listino_codice`,
  `listino_versione_codice`, `valuta_codice` (JOIN) e **`is_scaduta`** (computata).
  > **Scoperta da verifica codice (2026-06-03):** `is_scaduta` **non esiste nel
  > backend** (è derivata solo nel FE: `OfferteSearchTable.vue` /
  > `OffertaDrawer.vue`). Spostarla in vista non è un refactor ma il
  > *completamento* del dato — conferma la "soluzione assoluta" §7.1.

---

## 1. Decisioni ratificate (ereditate dai due piani §7, valgono identiche)

1. **Vista → opzione (A)**: viste canoniche `vw_<entita>_lista`
   `security_invoker=on`, nomi **canonici** senza alias
   (`ragione_sociale_completa`, `id_fiscale_univoco_cf_piva`, `ba_codice`).
   `vw_preventivi_list` / `vw_offerte_commerciali_list` **deprecate** (drop
   differito — §6, ⚠️ NOTA).
2. **Utility → `utility_codice`** nel preset; `utility_descrizione` extra opt-in.
3. **`rev` / `revisione_numero` NON ordinabili** (`ordinabile=f`, = oggi).
4. **`ba_codice`** nome canonico (eccezione legittima al "no alias `ba_*`",
   brief contratti §0-bis #4).
5. **[offerte] Listino composito** `codice · v{versione}` via slot FE — versione
   = colonna tecnica nascosta in vista.
6. **[offerte] Badge «scaduta»** preservato: colonna tecnica `is_scaduta` in
   vista; il gating per stato (`STATI_OFFERTA_SEGNALA_SCADENZA`) resta FE.

### Correzioni rispetto ai piani WIP (vincolanti per il seed)
- **`tipo_dato='integer'` NON ESISTE**: l'ENUM `ui.tipo_dato` è
  `{string,numeric,date,datetime,boolean,enum}`. `rev` e `revisione_numero` →
  **`numeric`** (non `integer`); `is_scaduta` → `boolean`. Un seed con `integer`
  fallirebbe il cast ENUM.
- **`stato_codice_interno`** è il nome canonico tecnico in queste due viste (come
  già `vw_preventivi_list`/`vw_offerte_commerciali_list`), non `stato_codice` come
  in contratti. Ogni catalogo dichiara il proprio `campo_sorgente`.

---

## 2. Lotto changeset (numerazione globale per data; oggi 2026-06-03, ultimo NN=`04`)

| File | Fase | Cosa |
| --- | --- | --- |
| `20260603-05-create-vw-preventivi-lista-mctit.yaml` | `20_code/vendite` | vista canonica preventivi (`security_invoker=on`) |
| `20260603-06-create-vw-offerte-commerciali-lista-mctit.yaml` | `20_code/vendite` | vista canonica offerte self-contained (+ `is_scaduta`) |
| `20260603-07-seed-ui-lista-colonna-priorita-preventivi-mctit.yaml` | `80_data/changelog` | `priorita` dominio preventivi |
| `20260603-08-seed-ui-lista-colonna-priorita-offerte-mctit.yaml` | `80_data/changelog` | `priorita` dominio offerte |
| append `lista_definizione.csv` | `80_data/sql/ui` | id=5 `vendite.preventivi`, id=6 `vendite.offerte` |
| append `lista_colonna.csv` | `80_data/sql/ui` | id 58-78 (preventivi, 21 col), id 79-103 (offerte, 25 col) |
| append `lista_preset.csv` | `80_data/sql/ui` | id=5 `preventivi_default`, id=6 `offerte_default` |
| append `lista_preset_colonna.csv` | `80_data/sql/ui` | preset 5 (13 righe), preset 6 (15 righe) |
| `db/pgtap/ui/test-lista-preventivi-seed.sql` | pgtap | seed preventivi |
| `db/pgtap/ui/test-lista-offerte-seed.sql` | pgtap | seed offerte |

(viste **prima** dei seed `lista_definizione` — vincolo trigger
`trgfn_ui_lista_definizione_a10_valida_vista_sql`; `priorita` seed **dopo** il
loader `lista_colonna` — `includeAll` ordina per nome file `20260603-07/08` >
`20260507-07`.)

### Mappa id catalogo
- **Preventivi (lista_id=5)** — preset visibili (12 incl. azioni): `numero`(58),
  `rev`(59), `data`(60), `ragione_sociale_completa`(61), `ba_codice`(62),
  `id_fiscale`(63), `utility_codice`(64), `istanza_utility_codice`(65),
  `totale_documento`(66), `validita_al`(67), `stato`(68), `azioni`(69). Tecnica
  nascosta: `stato_codice_interno`(70). Extra opt-in: `utility_descrizione`(71),
  `validita_dal`(72), `totale_imponibile`(73), `totale_iva`(74), `valuta`(75),
  `emittente_fiscale_codice`(76), `competenza_mese`(77), `data_insert`(78).
- **Offerte (lista_id=6)** — preset visibili (12 incl. azioni): `codice`(79),
  `revisione_numero`(80), `ragione_sociale_completa`(81), `ba_codice`(82),
  `id_fiscale`(83), `utility_codice`(84), `listino_codice`(85), `validita_dal`(86),
  `validita_al`(87), `data_emissione`(88), `stato`(89), `azioni`(90). Tecniche
  nascoste: `stato_codice_interno`(91), `is_scaduta`(92),
  `listino_versione_codice`(93). Extra opt-in: `utility_descrizione`(94),
  `istanza_utility_codice`(95), `tipo_variazione_globale`(96),
  `valore_variazione_globale`(97), `valuta`(98), `emittente_fiscale_codice`(99),
  `data_accettazione`(100), `data_rifiuto`(101), `data_annullamento`(102),
  `data_insert`(103).

---

## 3. Viste — campi e logica

### 3.1 `vendite.vw_preventivi_lista`
Riscrittura canonica gemella di `vw_preventivi_list`. **Sorgente:
`vendite.vw_preventivi`** (NON la tabella): la colonna `is_revision_attiva` è
stata **droppata** (`20260515-05`) e `is_attiva` è **derivata** in `vw_preventivi`
(`20260515-03`); si riusa quella derivazione (no logica duplicata), come fa la
`vw_preventivi_list` corrente (`FROM vendite.vw_preventivi p`, `p.is_attiva`).
Modifiche vs list view: nomi canonici (`ragione_sociale_completa`,
`id_fiscale_univoco_cf_piva`, `ba_codice`), JOIN `emittenti_fiscali` per
`emittente_fiscale_codice`, `security_invoker=on`. Tutto il resto 1:1 (soggetto
via `istanze_utilities`, `stato_*`, importi, validità, `competenza_mese`, audit).
> ⚠️ **Trappola risolta**: la prima stesura leggeva `p.is_revision_attiva` dalla
> tabella → Liquibase `ERRORE: la colonna p.is_revision_attiva non esiste`.
> Correzione: sorgente `vw_preventivi` + `p.is_attiva`.

### 3.2 `vendite.vw_offerte_commerciali_lista`
Self-contained, da `vw_offerte_commerciali_list` (`20260528-01`) + assorbe i JOIN
del repository. Aggiunge: `ragione_sociale_completa`/`id_fiscale_univoco_cf_piva`/
`ba_codice` canonici, `listino_codice` (JOIN `vendite.listini`),
`listino_versione_codice` (JOIN `vendite.listini_versioni.codice_versione`),
`valuta_codice` (JOIN `config.valute` via `o.valuta_id`), `emittente_fiscale_codice`
(JOIN `emittenti_fiscali`), **`is_scaduta`** = `validita_al IS NOT NULL AND
validita_al < CURRENT_DATE`. Preserva `is_attiva`/`has_next_revisione`/
`revisione_padre_id` 1:1.

---

## 4. Test pgTAP (gemelli `test-lista-contratti-seed.sql`)
Per ciascuna lista: vista espone i nomi canonici; `security_invoker=on`;
`lista_definizione` attiva con `vista_sql` corretta; numero colonne attive nel
catalogo (preventivi 21, offerte 25); ogni `campo_sorgente` esiste nella vista
(anti-typo, gemello trigger B2); preset `*_default` `is_default=true`,
`pagina_dimensione=25`, `ambito=sistema`; 12 colonne visibili nel preset;
`numero`/`codice` `fissata=true`; `priorita` di dominio applicata; nessuna colonna
`sensibile=true`; colonne tecniche presenti (`stato_codice_interno`; offerte anche
`is_scaduta`, `listino_versione_codice`).

---

## 5. A valle (NON in scope DB — attende consegna, memoria `feedback_be_fe_attende_prerequisiti_db`)
BE: repository su viste canoniche (rename breaking), whitelist order, endpoint
export. FE: migrazione a `<ListaConfigurabile>`. Dettaglio nei due piani WIP §5-§6.

---

## 6. Sequencing + ⚠️ NOTA drop differito viste vecchie (DA NON DIMENTICARE)

1. **Lotto DB** (§2): viste canoniche → seed definizione/colonna/preset/
   preset_colonna (CSV) → seed `priorita` → pgTAP verde.
2. Consegna su `dev/db-tid`. **Sblocca** BE/FE.
3. **BE commuta** i consumer sulle viste canoniche:
   - `vw_preventivi_list` → letta da `preventivi_repository.list_preventivi`
     **e `list_revisioni`** (`preventivi_repository.py:571`). Entrambi vanno
     spostati su `vw_preventivi_lista`. (`permissions_resolver.py` la cita solo
     nei commenti — nessun consumer reale.)
   - `vw_offerte_commerciali_list` → letta da `offerte_repository.list_offerte`
     (rimuove gli alias + i LEFT JOIN `listini`/`offerte_commerciali`/`valute`,
     ora in vista).

> ### ⚠️ NOTA — DROP DIFFERITO DELLE VISTE VECCHIE (cleanup post-BE)
> Le viste **`vendite.vw_preventivi_list`** e
> **`vendite.vw_offerte_commerciali_list`** NON vengono droppate in questo lotto
> (scelta Tid 2026-06-03: consegna DB non-breaking). Restano vive finché il BE non
> ha commutato tutti i consumer sopra. **Una volta che il BE è atterrato** (PR
> repository preventivi+offerte sulle viste canoniche), creare un changeset di
> cleanup dedicato:
>
> ```
> 2026MMDD-NN-drop-vw-preventivi-list-deprecata-mctit.yaml      (20_code/vendite)
> 2026MMDD-NN-drop-vw-offerte-commerciali-list-deprecata-mctit.yaml
> ```
> con `DROP VIEW IF EXISTS ...` + rollback che le ricrea (o riferimento al file
> originale). **Prima del drop**: `grep -rn "vw_preventivi_list\b\|vw_offerte_commerciali_list\b" backend/`
> deve restituire **solo commenti** (zero query attive). Tracciato anche nella
> tabella stato §10 dei due piani WIP.

4. **FE** migra i componenti; build verde.
5. **Cleanup**: drop viste deprecate (vedi NOTA) → chiusura famiglia liste vendite.

---

## 7. Stato famiglia liste vendite DEF-8

| Lista | DB | BE/FE | Doc |
| --- | --- | --- | --- |
| `vendite.contratti` | ✅ | ✅ (`1cc906377`) | [refactor-lista-contratti.md](refactor-lista-contratti.md) |
| `vendite.preventivi` | ✅ atterrato 2026-06-03 (questo brief) | ⏳ attende DB | [lista-preventivi.md](../work-in-progress/lista-preventivi.md) |
| `vendite.offerte` | ✅ atterrato 2026-06-03 (questo brief) | ⏳ attende DB | [lista-offerte-comm.md](../work-in-progress/lista-offerte-comm.md) |
| — viste vecchie | ⏳ drop differito post-BE (§6 NOTA) | — | — |
