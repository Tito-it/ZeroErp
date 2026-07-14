# Brief DB — Liste configurabili per le due code resi (da accreditare / da ri-consegnare)

> **Tipo**: mini-brief al team DB · **Target**: `dev/db-tid` · **Data**: 2026-07-14 · **Owner**: Tid
> **Stato**: ✅ CHIUSO (2026-07-15) — seed applicato al DB dev (verificato:
> `ui.lista_definizione` contiene `vendite.resi_da_accreditare`/`_riconsegnare` con 12
> colonne ciascuna); `codice` comunicati e consumati da BE/FE
> ([brief-be-fe-resi-code-configurabili.md](../work-done/brief-be-fe-resi-code-configurabili.md)).
> **Contesto**: le tab "da accreditare" e "da ri-consegnare" della vista Resi
> ([ResiView](../../../../frontend/src/vendite/resi/views/ResiView.vue)) oggi sono
> `DataTable` raw a colonne fisse: non hanno personalizzazione colonne né export, a
> differenza delle altre liste standard. Per allinearle allo standard
> `<ListaConfigurabile>` (come la tab "lista" resi, config `vendite.resi`) servono due
> nuove **liste configurabili** lato config `ui`.
> **Companion**: seed lista `vendite.resi` già realizzato in
> [brief-db-seed-lista-ui-resi.md](../work-done/brief-db-seed-lista-ui-resi.md) (PR #978) — stesso pattern.

---

## 1. Cosa serve (NON come)

> Questo brief descrive **il fabbisogno funzionale**. L'implementazione (nomi tabelle,
> id, formato seed, loader) è competenza e scelta del team DB.

Servono **due liste configurabili** nel catalogo config `ui`, una per ciascuna coda,
entrambe con **sorgente una vista che esiste già** (nessun oggetto DB nuovo da creare):

| Lista (fabbisogno) | Vista sorgente esistente | Grana |
|---|---|---|
| Coda resi "da accreditare" | `vendite.vw_resi_da_accreditare` | riga reso |
| Coda resi "da ri-consegnare" | `vendite.vw_resi_da_riconsegnare` | riga reso |

Per ognuna serve che diventino disponibili a runtime:

- **personalizzazione colonne** (mostra/nascondi, ordine, larghezza) come le altre liste;
- **export** CSV/XLSX che rispetti colonne visibili/ordine/permessi dell'utente
  (l'export BE è generico sulla config lista: una volta esistente la config, funziona).

Le due viste sono già `security_invoker=on` ed espongono `emittente_fiscale_id` per lo
scope emittente applicativo: **nessuna modifica alle viste** è richiesta da questo brief.

## 2. Colonne che ciascuna lista deve poter esporre

Le colonne richieste corrispondono a quelle oggi mostrate a video (più eventuali opzionali,
opt-in via personalizzazione). I nomi tra parentesi sono le colonne **già presenti nella
vista sorgente** (verificabili nella doc auto-gen delle viste): il team DB le mappi come
ritiene, rispettando i ruoli indicati.

### 2a. Coda "da accreditare" (sorgente `vw_resi_da_accreditare`)

| Ruolo | Colonna sorgente | Note |
|---|---|---|
| **Identificatore** (sempre visibile) | `reso_numero` | numero del reso |
| Informazione | `data` | data reso |
| Informazione | `destinatario_denominazione` | ragione sociale destinatario |
| Informazione | `descrizione` | articolo/descrizione riga |
| Informazione | `ddt_numero` | DDT di origine |
| Informazione | `qta_operativa` | quantità resa (unità operativa) |
| Informazione | `motivo` | motivo del reso |
| Opzionali (opt-in) | `ba_codice`, `quantita` | codice account, quantità base |
| **Azione** (non esportabile) | — | colonna azioni di riga (apri reso) |

### 2b. Coda "da ri-consegnare" (sorgente `vw_resi_da_riconsegnare`)

| Ruolo | Colonna sorgente | Note |
|---|---|---|
| **Identificatore** (sempre visibile) | `reso_numero` | numero del reso |
| Informazione | `data` | data reso |
| Informazione | `destinatario_denominazione` | ragione sociale destinatario |
| Informazione | `descrizione` | articolo/descrizione riga |
| Informazione | `ddt_numero` | DDT di origine |
| Informazione | `qta_resa` | quantità resa |
| Informazione | `qta_riconsegnata` | quantità già ri-consegnata |
| Informazione | `qta_residua` | copertura residua |
| Informazione | `stato_riconsegna` | stato derivato (DA_RICONSEGNARE / PARZIALE / COMPLETATA); reso a video come Tag lato FE |
| **Azione** (non esportabile) | — | colonna azioni di riga (apri reso) |

> Nota: `vw_resi_da_riconsegnare` **non** espone `ba_codice` (asimmetria reale con la coda
> accrediti, non una dimenticanza).

## 3. Vincoli / requisiti funzionali

1. **Riferimento applicativo per `codice`, non per id**: il FE/BE useranno il `codice` lista
   (tipo `vendite.resi_da_accreditare` / `vendite.resi_da_riconsegnare`, o come il team DB
   preferisce nominarli — basta comunicarli). Gli id numerici sono liberi al momento dell'apply.
2. **Ordinabilità**: le colonne di ciascuna lista devono essere ordinabili server-side
   (lo standard `ListaConfigurabile` ordina lato BE; il supporto `order_by/order_dir` sugli
   endpoint coda è oggetto del brief BE companion).
3. **Ricercabilità**: le colonne testuali "destinatario / DDT / articolo" andrebbero marcate
   ricercabili full-text (search ILIKE), coerentemente con la lista resi principale — **se e
   solo se** il BE espone la search sulle code (vedi brief BE). Se il BE non la espone in
   questa iterazione, marcarle non-ricercabili.
4. **Chiavi i18n** delle etichette colonna: le aggiunge il **FE** nel proprio blocco
   `vendite.resi.*` — nessuna azione DB.
5. Nessun preset dedicato: visibilità di default gestita dal runtime (parità lista resi).

## 4. Cosa comunicare indietro al BE/FE

- I due **`codice` lista** effettivi assegnati.
- Conferma delle colonne esportabili/ordinabili/ricercabili come sopra (o eventuali scostamenti).

---

## 6. Piano DB (realizzato lato file — 2026-07-14)

> Sezione aggiunta in sede di realizzazione. Traccia le scelte concrete e lo stato.
> Segue lo **stesso pattern** del companion (append ai 2 CSV `ui` runOnChange, nessun
> nuovo loader, nessun changeSet manuale, nessun oggetto DB — vedi
> [[feedback_messaggi_errore_no_new_loader]] e [[feedback_seed_80_data_csv]]).

### 6a. Analisi critica (pre-scrittura)

- **Viste verificate** contro doc auto-gen ([vw_resi_da_accreditare](../../dbzero/vendite/views/vw_resi_da_accreditare.md),
  [vw_resi_da_riconsegnare](../../dbzero/vendite/views/vw_resi_da_riconsegnare.md)):
  esistono, `security_invoker=on`, espongono `emittente_fiscale_id`. Tutti i
  `campo_sorgente` richiesti in §2 **esistono** nella proiezione reale.
- **Grana RIGA** (differenza sostanziale con tutte le liste esistenti, doc-grana): PK di
  vista = `resi_riga_id`; `reso_numero` **si ripete** su più righe → non è chiave di riga.
  Il consumatore FE attuale ([ResiCodaTable.vue](../../../../frontend/src/vendite/resi/components/ResiCodaTable.vue))
  usa `data-key="resi_riga_id"` (rowKey/paginazione stabile) e apre il reso via
  `reso_id` (target azione, **diverso** dal PK di riga). Entrambe le chiavi devono
  arrivare nel payload pur non essendo colonne visibili → **seedate come colonne
  tecniche nascoste** (pattern `stato_codice_interno`: `attivo=t`, tutti gli altri flag `f`).
- **Emittente non seedabile** su queste liste: le viste espongono solo
  `emittente_fiscale_id`, non `emittente_fiscale_descrizione` (che la lista resi
  principale prende da `vw_resi_lista`). Coerente col fatto che §2 non la chiede.
- **Ordina/Ricerca**: seedate come le altre liste (`ordinabile=t` sulle visibili,
  `ricercabile_full=t` su destinatario/articolo/DDT + `ba_codice` su accreditare). È una
  **promessa verso il BE**: gli endpoint coda (`list_da_accreditare`/`list_da_riconsegnare`
  in `resi_repository.py`) devono onorare `order_by/order_dir` e search, o degradare —
  oggetto del brief BE companion.

### 6b. `codice` lista assegnati

- `vendite.resi_da_accreditare` (definizione **id 10**, sorgente `vw_resi_da_accreditare`)
- `vendite.resi_da_riconsegnare` (definizione **id 11**, sorgente `vw_resi_da_riconsegnare`)

### 6c. Colonne seedate

- **Lista 10 (accreditare)** — colonne id **161-172**: `reso_numero` (identificatore),
  `data`, `destinatario_denominazione` (ric), `descrizione` (ric), `ddt_numero` (ric),
  `qta_operativa` (numeric), `motivo`, `ba_codice` (ric), `quantita` (numeric),
  **`reso_id`** (nascosta), **`resi_riga_id`** (nascosta), `azioni`.
- **Lista 11 (ri-consegnare)** — colonne id **173-184**: `reso_numero` (identificatore),
  `data`, `destinatario_denominazione` (ric), `descrizione` (ric), `ddt_numero` (ric),
  `qta_resa`, `qta_riconsegnata`, `qta_residua` (numeric), `stato_riconsegna` (string →
  Tag FE), **`reso_id`** (nascosta), **`resi_riga_id`** (nascosta), `azioni`.

Le colonne nascoste `reso_id`/`resi_riga_id`: `filtrabile/ordinabile/esportabile/ricercabile/sensibile = f`,
`attivo = t`, `esportabile = f` (non finiscono nell'export). i18n key vuota.

### 6d. Handoff a BE/FE (§4)

- Codici: `vendite.resi_da_accreditare`, `vendite.resi_da_riconsegnare`.
- FE: passare `dataKey="resi_riga_id"` a `<ListaConfigurabile>`; target azione "apri reso"
  = `reso_id`. Chiavi i18n `vendite.resi_da_accreditare.col_*` / `vendite.resi_da_riconsegnare.col_*`.
- BE: onorare `order_by/order_dir` + search sulle code (altrimenti rivedere i flag
  `ordinabile`/`ricercabile_full` di questo seed).

## 5. Avanzamento

| # | Step | Stato |
|---|---|---|
| 1 | Lista config coda "da accreditare" (sorgente `vw_resi_da_accreditare`) | ✅ CSV: def id 10 + colonne 161-172 |
| 2 | Lista config coda "da ri-consegnare" (sorgente `vw_resi_da_riconsegnare`) | ✅ CSV: def id 11 + colonne 173-184 |
| 3 | Apply + comunicazione `codice` lista al BE/FE | ✅ loader `ui` applicato sul DB dev, verificato runtime (config risolve); BE/FE consumano i `codice` |
