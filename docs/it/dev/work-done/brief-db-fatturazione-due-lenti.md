# Brief DB — Fatturazione a due lenti: substrato dati (timestamp §7, lookup classi, viste Lente 1 e Lente 2)

> **Per**: team DB (`dev/db-tid`). · **Da**: design-of-record
> [brief-design-fatturazione-due-lenti.md](../work-in-progress/brief-design-fatturazione-due-lenti.md) (decisioni
> DL-1..8, Tid 2026-07-04). · **Data**: 2026-07-06 · **Stato**: 🟢 **DB APPLICATO +
> pgTAP VERDI (2026-07-06)** — migrations `20260706-01..15` **EXECUTED** sul DB di
> sviluppo (lookup+seed, data_riferimento su resolver/union, 3 viste Lente 1, 2 viste
> backlog, indice AF, **fix V-1 `security_invoker=on` sulle 7 `vw_dash_fatturazione_*`**
> — verificato: reloptions `{security_invoker=on}` su tutte); pgTAP
> `test-vw-dash-competenza-v1.sql` (plan 15) e `test-vw-dash-backlog-v1.sql` (plan 14)
> **verdi** (eseguiti da Tid). Doc manuale scritta; doc auto-gen da rigenerare (lato
> Tid). Committato e mergiato (PR #929; Fasi 1-2 BE/FE mergiate con PR #932). **CHIUSO** — spostato in work-done 2026-07-07.
> **Perimetro**: SOLO DB. Copre in un unico piano i tre deliverable DB del disegno a due
> lenti: (A) validazione del timestamp di transito (§7 del design, deciso DL-5),
> (B) lookup `motivo_fermo → classe` (DL-6), (C) viste per Lente 1 Competenza e
> Lente 2 Backlog (DL-2/7/8). BE (endpoint) e FE restano su `dev/backend-tid`, fasi 1-2
> del design.
> **Correlato**: [brief-design-dashboard-fatturazione.md](brief-design-dashboard-fatturazione.md)
> (famiglia `vw_dash_fatturazione_*` esistente, congelata) ·
> [analisi-dash-pre-fatturazione.md](analisi-dash-pre-fatturazione.md) ·
> viste `vendite.vw_dash_fatturazione_{preventivi,ordini,offerte,contratti,commesse,documenti,mensile}` ·
> tabelle `vendite.attivita_fatturabili`, `vendite.commesse_attivita`, `vendite.fatture`,
> `vendite.fatturazione_lotti(_fatture|_task_runs)`, `vendite.fatture_log`.

---

## 0. Esito dell'analisi critica (2026-07-06) — cosa cambia rispetto al design

L'analisi sul DB vivo (doc auto-gen + migration + backend) **conferma l'impianto** del
design e chiude i punti che il design lasciava da validare. Sintesi delle scoperte che
questo brief incorpora:

1. **DL-5 VALIDATO** — `attivita_fatturabili.data_insert` è un timestamp di emissione
   affidabile: nessun campo nuovo, nessuna colonna `data_emissione` di fallback (§2).
   Un solo rischio strutturale latente (C1, §2.3) da documentare + test-sentinella.
2. **`motivo_fermo` oggi non ha alcun livello dati**: i 10 codici sono stringhe hardcoded
   nei `CASE WHEN` dei 5 resolver, nessuna tabella vocabolario esiste (verificato su
   `config` e `vendite`). La lookup DL-6 è quindi una tabella **nuova** (§3) e serve una
   regola anti-drift viste↔lookup (fail-visible, §3.3).
3. **L'anzianità della Lente 2 oggi non è calcolabile**: la union
   `vw_dash_fatturazione_documenti` non espone alcuna data documento (solo
   `competenza_mese`, già troncata al mese). Serve una colonna additiva
   `data_riferimento` sui 5 resolver + union (§5.1) — compatibile col congelamento,
   che riguarda il *prodotto* 5-card (layout + aggregata mensile), non il substrato
   condiviso che per design sopravvive (§6 del design).
4. **"Riusa il resolver Commesse" va letto come riuso dei predicati, non della vista**:
   il resolver esistente ha grana commessa×mese; la Lente 1 richiede grana **attività**
   con stadi a valle (AF → riga fattura → stato). Nuova famiglia `vw_dash_competenza_*`
   che riusa predicato computabile (`20260703-61`), predicato EMESSA e scope GUC (§4).
5. **⚠️ Scoperta non prevista dal design**: le `vw_dash_fatturazione_*` NON impostano
   `security_invoker = on` (a differenza dello standard liste, es.
   `vw_preventivi_lista`). Il claim "RLS gratis" del brief pre-fatturazione (§5) va
   verificato sul DB: senza invoker la RLS delle 4 aree si valuta come owner della vista
   (potenziale bypass per operatori ristretti). Le viste NUOVE nascono `security_invoker
   = on`; per la famiglia congelata → verifica V-1 (§10).

## 1. Perimetro e non-obiettivi

**In scope (solo DB):** tabella lookup + seed; colonna additiva sui 5 resolver + union;
5 viste nuove (3 Lente 1, 2 Lente 2); 1 indice; pgTAP; doc manuale.

**Fuori scope:**

* Endpoint BE e FE (fasi 1-2 del design, `dev/backend-tid`).
* Dismissione della dashboard 5-card (`vw_dash_fatturazione_mensile` compresa): è la
  Fase 3 del design, **non si droppa nulla qui**. La famiglia esistente resta viva e
  invariata (unica eccezione: colonna additiva in coda, punto §5.1).
* Push ricorrente contratti, valore € offerte/contratti (v2 del design).
* Modifiche a `fn_emit_attivita_fatturabili_da_commessa` (il caso C1 §2.3 si documenta,
  non si corregge qui — è pre-esistente e fuori dal perimetro read-only del cruscotto).

## 2. (A) Validazione timestamp di transito — ✅ `data_insert` affidabile, nessun oggetto nuovo

### 2.1 Verdetto

**Confermata la decisione DL-5**: `vendite.attivita_fatturabili.data_insert` è la data di
emissione dell'attività. `date_trunc('month', af.data_insert) > af.competenza_mese` ⇒
**recuperato in ritardo**. Nessuna colonna nuova, nessun backfill.

### 2.2 Fatti verificati (doc auto-gen + migration + backend, 2026-07-06)

* La riga AF nasce **una sola volta**, all'emissione: `fn_emit_attivita_fatturabili_da_commessa`
  processa solo attività `stato_emissione = 'NON_EMESSA'` e inserisce con `data_insert`
  da DEFAULT `now()`; UNIQUE `uq_attivita_fatturabili_commessa_attivita
  (commessa_attivita_id)` garantisce 1 AF per attività.
* **Nessun DELETE in produzione** su `attivita_fatturabili` (soli DELETE nei fixture
  pgTAP). Il guard `trgfn_attivita_fatturabili_guard_fatturato` blocca UPDATE/DELETE di
  righe fatturate salvo bypass manutentivo.
* **Reset lotto / reset fattura draft** (`fn_reset_lotto_draft`,
  `fn_reset_lotto_fattura_draft` → `fn_cleanup_fatture_by_ids`): la riga AF **sopravvive**
  — solo UPDATE che azzera `fattura_riga_id`/`fatturato`/lock; `data_insert` invariata;
  l'attività resta `EMESSA` (nessuna ri-emissione possibile: `fn_emit` salta le EMESSA,
  `fn_upsert_commessa_attivita` solleva `E_COMMESSA_ATTIVITA_GIA_EMESSA`).
* **Nessun percorso** riporta `stato_emissione` indietro (`EMESSA → NON_EMESSA`) né
  scrive `ANNULLATA`; `RIFIUTATA` è sull'asse approvazione e oggi non ha writer
  (già noto da `20260703-61`).
* `data_insert` non è mai toccata in UPDATE (`trgfn_audit_data_user_generic` scrive solo
  `user_insert` su INSERT e `data_update/user_update`).
* **Fonti alternative scartate** (conferma §7 design): `commesse_attivita_log` è tabella
  senza writer (zero INSERT nel repo); `storico.attivita_fatturabili` parte da
  UPDATE/DELETE (non cattura l'INSERT); `commesse_attivita.data_update` approssima
  l'emissione ma è sovrascrivibile da qualunque update successivo.

### 2.3 Caveat C1 (unico caso strutturale, latente) + sentinella

Il ramo UPDATE di idempotenza di `fn_emit` cerca la riga AF per
`(sorgente_tipo_id = COMMESSA, sorgente_uid = hash(segment_key))` **senza filtrare per
commessa**: una collisione di `segment_key` tra attività diverse ri-punterebbe la riga AF
esistente (con il suo `data_insert` originale) alla nuova attività. Oggi nessun percorso
di produzione lo genera. Direzione dell'errore: `data_insert` può solo risultare **più
vecchia**, mai posticipata ⇒ il flag "in ritardo" può al più **sotto-stimare**, mai dare
falsi positivi. Mitigazione in questo brief: caveat nel manuale + **test-sentinella pgTAP**
(§7): dopo un ciclo emissione → aggancio fattura → reset, `data_insert` è invariata.

## 3. (B) Lookup classi di azionabilità — `config.motivi_fermo` (DL-6)

### 3.1 Collocazione e DDL

Schema **`config`** (casa dei vocabolari di riferimento: `stati_doc_*`, `sorgenti`, …).
Tabella tecnica, pattern `stati_doc_fiscale`:

```sql
CREATE TABLE config.motivi_fermo (
    id              INTEGER GENERATED BY DEFAULT AS IDENTITY,
    codice_interno  VARCHAR NOT NULL,   -- chiave logica immutabile = i codici emessi dalle viste
    codice          VARCHAR NOT NULL,   -- etichetta mutabile a video (linee-guida §6c)
    descrizione     VARCHAR,
    classe          VARCHAR NOT NULL,   -- classe di azionabilità (DL-6/7)
    azione          VARCHAR,            -- hint operativo ("smista le righe", "pusha in commessa", …)
    ordine          SMALLINT,
    attivo          BOOLEAN NOT NULL DEFAULT true,
    meta            JSONB   NOT NULL DEFAULT '{}',
    -- audit standard + tx_id
    CONSTRAINT pk_motivi_fermo PRIMARY KEY (id),
    CONSTRAINT uq_motivi_fermo_codice_interno UNIQUE (codice_interno),
    CONSTRAINT chk_motivi_fermo_classe CHECK
        (classe IN ('FISIOLOGICO','RECUPERABILE','ANOMALIA','SOLLECITO_CLIENTE'))
);
```

Le 4 classi sono il **contratto semantico** del design (3.a 🟢 / 3.b 🟠 / 3.c 🔴 / 3.d 🔵):
CHECK, non seconda lookup — non sono configurabili dall'utente, sono il modello.

### 3.2 Seed (CSV in `80_data`, mappatura DL-6/7 — vocabolario verificato 10/10 sulle viste vive)

| codice_interno | classe | azione |
|---|---|---|
| `DOC_BOZZA` | FISIOLOGICO | — (in lavorazione interna) |
| `CANONE_NON_GENERATO` | FISIOLOGICO | — (manca il push ricorrente) |
| `SENZA_FIGLIO` | FISIOLOGICO | — (conversione a scelta) |
| `IN_ATTESA_ACCETTAZIONE` | SOLLECITO_CLIENTE | sollecita il cliente |
| `RIGA_RESIDUA` | RECUPERABILE | smista le righe |
| `PUSH_NON_ESEGUITO` | RECUPERABILE | pusha in commessa |
| `PUSH_PARZIALE` | RECUPERABILE | completa il push |
| `ATTIVITA_NON_APPROVATA` | RECUPERABILE | approva l'attività |
| `ATTIVITA_NON_EMESSA` | RECUPERABILE | emetti l'attività |
| `FIGLIO_ABORTITO` | ANOMALIA | rivedi l'offerta |

Seed **solo CSV** (`80_data/sql/config/motivi_fermo.csv`, `loadUpdateData` con
`nullValue`, preCondition `tableExists`, modello `20260605-11-seed-transizioni-stati-ordini`).
Eventuali codici futuri = **append al CSV** (mai nuovo loader).

### 3.3 Regola anti-drift (fail-visible)

Le viste emettono i codici come letterali: nessuna FK possibile. Doppia rete:

1. **In vista** (`vw_dash_backlog_documenti`): `LEFT JOIN config.motivi_fermo` +
   `classe = COALESCE(mf.classe, 'ANOMALIA')` — un motivo non mappato **compare come
   anomalia** 🔴, non sparisce in silenzio (un INNER JOIN o un filtro lo perderebbe).
2. **In pgTAP**: assert che l'insieme dei `motivo_fermo` emessi da
   `vw_dash_fatturazione_documenti` ⊆ `config.motivi_fermo.codice_interno` e che ogni
   riga seed abbia classe valida (§7).

## 4. (C1) Lente 1 Competenza — famiglia `vendite.vw_dash_competenza_*` (3 viste)

Tutti e 4 i blocchi DL-8 predisposti da subito (concentrico). Grana **attività** — è la
grana della competenza vera; la spina è quella del §4 del design:
`commesse_attivita → attivita_fatturabili → fatture_righe → stato fattura`.

### 4.1 `vw_dash_competenza_attivita` (drill-down, blocchi 1+2+3+3a)

1 riga per `commessa_attivita` **computabile** (predicato `20260703-61`:
`stato_emissione <> 'ANNULLATA' AND (stato_approvazione <> 'RIFIUTATA' OR stato_emissione
= 'EMESSA')`) di commessa **viva** (`stati_commessa.codice_interno <> 'ANNULLATA'`).
LEFT JOIN `attivita_fatturabili` (1:1 su `commessa_attivita_id`) → `fatture_righe` →
`fatture` → `config.stati_doc_fiscale`.

| Colonna | Contenuto |
|---|---|
| `competenza_mese` | `ca.competenza_mese` (vera, NOT NULL) |
| `commessa_id/commessa_codice/commessa_attivita_id` | chiavi drill-down |
| `emittente_soggetto_ruolo_id`, `cliente_display` | come resolver commesse (BA → SR → soggetti, LEFT) |
| `articolo_id`, `data_attivita`, `quantita` | contesto riga |
| `stadio` | `DA_APPROVARE` (BOZZA) · `DA_EMETTERE` (APPROVATA, NON_EMESSA) · `EMESSA_NON_FATTURATA` (EMESSA, `af.fattura_riga_id IS NULL`) · `FATTURATA` |
| `stato_approvazione`, `stato_emissione` | assi grezzi |
| `valore` | `prezzo_snapshot × quantita` (misura unica del funnel, DB-6) |
| `data_emissione` | `af.data_insert` (NULL se non emessa) |
| `emessa_in_ritardo` | `date_trunc('month', af.data_insert)::date > ca.competenza_mese` (NULL se non emessa) |
| `is_sospesa`, `posticipa_al` | flag AF (contesto blocco 2) |
| `fattura_id`, `fattura_riga_id`, `fattura_numero/anno/serie` | aggancio blocco 3 |
| `stato_fattura_codice_interno`, `stato_fattura_codice` | breakdown 3a (NULL-safe: fattura senza stato → NULL) |
| `valore_fatturato` | `fr.imponibile_riga` (riconciliazione, DB-6) |
| `fattura_critical` | `f.critical` (ponte col blocco 4) |

### 4.2 `vw_dash_competenza_mensile` (aggregata, formato lungo)

Gli stati fattura sono dati (`config.stati_doc_fiscale`), non colonne: aggregata in
**formato lungo**, il BE pivota. Grana: `competenza_mese × stadio ×
stato_fattura_codice_interno` (NULL per stadi non fatturati):
`n_attivita`, `valore_tot`, `valore_fatturato_tot`, `n_in_ritardo`, `valore_in_ritardo`.
Il contratto regge tutti i blocchi 1→3a senza modifiche future (concentrico DL-8).

### 4.3 `vw_dash_competenza_errori` (blocco 4)

Union di due popolazioni di "errore vivo", con regola di competenza esplicita:

* **`TASK_ERRORE`** — `fatturazione_lotti_task_runs` con `task_stato = 'ERRORE'` e
  `attivo IS TRUE`, non superato da un run successivo `COMPLETATO` sulla stessa chiave
  `(lotto_id, stato_doc_fiscale_id, task_code)`. Competenza = `fatturazione_lotti.competenza_mese`
  (NOT NULL).
* **`FATTURA_CRITICA`** — `fatture.critical IS TRUE` (mantenuto dai trigger di sync da
  `fatture_log`). Competenza (DB-7, in ordine): mese del lotto via
  `fatturazione_lotti_fatture` → mesi distinti delle AF collegate (una riga per mese) →
  fallback `date_trunc('month', f.data)`.

Colonne: `tipo_evento, competenza_mese, lotto_id, lotto_codice, stato_lotto, fattura_id,
fattura_numero/anno/serie, error_code, messaggio, data_evento, emittente_soggetto_ruolo_id`.

### 4.4 Scope emittente (DB-8)

`commesse`/`attivita_fatturabili`/`fatture`/`fatturazione_lotti` sono fuori RLS operatori
⇒ le 3 viste applicano **dentro** lo stesso scope GUC del resolver commesse
(`CROSS JOIN LATERAL script.fn_get_emittenti_scope_sr_ids(app.current_user_id)`,
fail-closed: senza GUC ⇒ 0 righe — caveat documentato nel manuale, GUC impostata nei
pgTAP). Tutte le viste nuove: `WITH (security_invoker = on)`.

## 5. (C2) Lente 2 Backlog — anzianità + classe (2 viste + colonna additiva)

### 5.1 Colonna `data_riferimento` sui 5 resolver + union (prerequisito anzianità)

La union oggi non espone alcuna data documento. Si **appende in coda** (dopo
`cliente_display`, contratto colonne compatibile) `data_riferimento date` con semantica
per area ("fermo da…", v1 proxy come da §5 design):

| Area | `data_riferimento` |
|---|---|
| PREVENTIVI | `p.data` |
| ORDINI | `o.data` |
| OFFERTE | `COALESCE(data_emissione, validita_dal, data_insert::date)` (stessa catena del proxy mese) |
| CONTRATTI | mese esploso (= `competenza_mese` della riga) |
| COMMESSE | `ca.competenza_mese` (chiave del GROUP BY) |

6 nuovi file migration (5 resolver + union), **mai** modifica dei file `20260703-*` già
pushati. La `vw_dash_fatturazione_mensile` non cambia (aggrega colonne nominate).

### 5.2 `vw_dash_backlog_documenti`

```sql
SELECT d.area, d.competenza_mese, d.documento_id, d.documento_uid, d.codice,
       d.cliente_display, d.emittente_fiscale_id, d.emittente_soggetto_ruolo_id,
       d.valore_totale - d.valore_transitato   AS valore_fermo,      -- NULL per aree a conteggi
       d.unita_totali  - d.unita_transitate    AS unita_ferme,
       d.motivo_fermo,
       COALESCE(mf.classe, 'ANOMALIA')         AS classe,            -- fail-visible §3.3
       mf.azione,
       d.data_riferimento,
       (CURRENT_DATE - d.data_riferimento)     AS anzianita_giorni,
       d.stato_codice_interno, d.stato_codice, d.fase
FROM   vendite.vw_dash_fatturazione_documenti d
LEFT   JOIN config.motivi_fermo mf ON mf.codice_interno = d.motivo_fermo AND mf.attivo
WHERE  d.motivo_fermo IS NOT NULL
AND    COALESCE(mf.classe, 'ANOMALIA') <> 'FISIOLOGICO';
```

Conseguenze automatiche (DL-7, nessun caso speciale per area): contratti spariscono
(tutto 🟢 finché manca il push ricorrente), offerte entrano solo con `FIGLIO_ABORTITO` 🔴
e `IN_ATTESA_ACCETTAZIONE` 🔵, il 🔵 resta filtrabile per il filtro "sollecito cliente".
Ordinamento per anzianità: lato BE (le viste non garantiscono ORDER).

### 5.3 `vw_dash_backlog_riepilogo`

Contatori di testata (`🟠 n · 🔵 n · 🔴 n`): GROUP BY `classe, area` →
`n_documenti, valore_fermo_tot, anzianita_max_giorni`. Il 🟢 è già escluso a monte.

## 6. Indici e performance

* `ix_attivita_fatturabili_competenza_mese` su `(competenza_mese)` — oggi esiste solo
  `(billing_account_id, competenza_mese)`, inutilizzabile per le scansioni per mese della
  Lente 1. File in `90_end`, `IF NOT EXISTS` (pattern `20260703-58`).
* Nessun altro indice preventivo: v1 = viste normali (volumi attuali), `EXPLAIN` su dati
  reali come da linea già decisa per la famiglia esistente; l'aggregata mensile è
  materializzabile in futuro senza cambiare contratto.

## 7. pgTAP (2 file nuovi, `db/pgtap/vendite/`)

`test-vw-dash-competenza-v1.sql`:

1. Esistenza 3 viste + lookup; GUC operatore impostata (memoria: fixture con
   `emittente_fiscale_id` esplicito, `competenza_al` NOT NULL, CF fissi).
2. Funnel: attività BOZZA→`DA_APPROVARE`, APPROVATA→`DA_EMETTERE`, emessa senza
   fattura→`EMESSA_NON_FATTURATA`, fatturata→`FATTURATA` con
   `stato_fattura_codice_interno` e `valore_fatturato`.
3. Ritardo: attività con competenza mese M e emissione (AF `data_insert`) forzata a M+2
   → `emessa_in_ritardo = true`; emissione nel mese → `false`.
4. **Sentinella C1/reset** (§2.3): emetti → aggancia riga fattura → cleanup/reset →
   `data_insert` AF invariata, stadio torna `EMESSA_NON_FATTURATA`.
5. Void: attività ANNULLATA/RIFIUTATA fuori da attività e mensile (riuso predicato -61).
6. Errori: task run `ERRORE` attivo → riga `TASK_ERRORE` col mese del lotto; fattura
   `critical` → riga `FATTURA_CRITICA`; run `ERRORE` superato da `COMPLETATO` assente.
7. Scope: commessa di emittente fuori whitelist assente da tutte e 3 le viste.

`test-vw-dash-backlog-v1.sql`:

1. **Coerenza vocabolario**: motivi emessi dalla union ⊆ lookup; 10 righe seed con
   classe valida.
2. Classificazione: `RIGA_RESIDUA`→🟠 presente; `DOC_BOZZA`/`SENZA_FIGLIO`/
   `CANONE_NON_GENERATO`→🟢 assenti (contratti: zero righe backlog);
   `FIGLIO_ABORTITO`→🔴; `IN_ATTESA_ACCETTAZIONE`→🔵.
3. Fail-visible: motivo fittizio non mappato (fixture con UPDATE su copia? no — si
   simula rimuovendo temporaneamente una riga lookup nel test) → classe `ANOMALIA`,
   riga NON persa.
4. Anzianità: `data_riferimento` valorizzata per ogni area presente; `anzianita_giorni`
   coerente.
5. Riepilogo: contatori per classe = somma dei documenti del dettaglio.

## 8. Documentazione

* Manuale nuove viste: `docs/it/dbzero/vendite/manual/vw_dash_competenza_{attivita,mensile,errori}.md`
  e `vw_dash_backlog_{documenti,riepilogo}.md` (standard: scopo/contesto/regole; caveat
  GUC fail-closed e caveat C1 nel manuale di `vw_dash_competenza_attivita`).
* Manuale lookup: `docs/it/dbzero/config/manual/motivi_fermo.md` (vocabolario = whitelist,
  regola "nuovo codice ⇒ append CSV + mappatura classe **prima** di emetterlo da una vista").
* Doc auto-gen: rigenerare dopo l'applicazione (viste + tabella). Guida utente = Fase 4
  del design (non qui).

## 9. Piano migration (sequenza `20260706-NN`, un changeSet per file, `logicalFilePath` sempre)

| NN | Cartella | File (`-mctit.yaml`) | Contenuto |
|---|---|---|---|
| 01 | `00_schema/config` | `create-config-motivi-fermo` | tabella §3.1 (CHECK classe, UNIQUE codice_interno, audit) |
| 02 | `80_data` | `seed-config-motivi-fermo` | CSV 10 righe §3.2, preCondition `tableExists`, `loadUpdateData` |
| 03-07 | `20_code/vendite` | `update-vw-dash-fatturazione-<area>-data-riferimento` ×5 | append `data_riferimento` §5.1 |
| 08 | `20_code/vendite` | `update-vw-dash-fatturazione-documenti-data-riferimento` | union + colonna in coda |
| 09 | `20_code/vendite` | `create-vw-dash-competenza-attivita` | §4.1 (invoker on, scope GUC) |
| 10 | `20_code/vendite` | `create-vw-dash-competenza-mensile` | §4.2 |
| 11 | `20_code/vendite` | `create-vw-dash-competenza-errori` | §4.3 |
| 12 | `20_code/vendite` | `create-vw-dash-backlog-documenti` | §5.2 |
| 13 | `20_code/vendite` | `create-vw-dash-backlog-riepilogo` | §5.3 |
| 14 | `90_end` | `create-ix-attivita-fatturabili-competenza-mese` | §6, `IF NOT EXISTS` |

Ordine di sviluppo consigliato (a step, ognuno applicabile+testabile da solo):
**Step 1** = 01-02 (lookup + seed; indipendente, sblocca la decodifica classi lato FE);
**Step 2** = 09-11 + 14 (Lente 1, sblocca la Fase 1 BE del design);
**Step 3** = 03-08 + 12-13 (colonna anzianità sui resolver/union, poi viste backlog che
ne dipendono; sblocca la Fase 2 BE). `runOnChange: false` ovunque nello stato finale;
preConditions `viewExists`/`tableExists` tra fasi.

## 10. Verifiche contestuali (da fare in applicazione)

* **V-1 — `security_invoker` famiglia congelata**: ✅ **VERIFICATA (2026-07-06) — buco
  CONFERMATO.** Le 7 viste `vw_dash_fatturazione_*` hanno reloptions vuote (owner
  context) e sono owned da `titodb`, che è anche owner di
  preventivi/ordini/offerte_commerciali/contratti con RLS `enabled=true, forced=false`:
  l'owner è esente dalla RLS non-forced ⇒ **lo scope emittente era bypassato** sulle 4
  aree documentali per qualunque chiamante (incluso `zeroerp_app`); solo il resolver
  COMMESSE era scopato (GUC, `20260703-60`). Fix: **`20260706-15`**
  (`ALTER VIEW … SET (security_invoker = on)` sulle 7 viste, rollback con RESET) —
  ✅ **APPLICATO da Tid (2026-07-06)**, verificato: reloptions `{security_invoker=on}`
  su tutte e 7. Con la union in invoker, anche il backlog (§5.2) eredita ora la RLS
  emittente corretta sulle 4 aree documentali.
* **V-2 — EXPLAIN su dati reali** delle 3 viste Lente 1 (soglia di guardia, come da
  linea famiglia esistente). ⬜ rinviata a volumi reali (coerente con la famiglia
  esistente).

## 11. Decisioni proposte (da confermare con Tid prima dell'applicazione)

| # | Decisione | Proposta | Note |
|---|---|---|---|
| DB-1 | Timestamp §7 | `data_insert`, nessun campo nuovo; caveat C1 doc + sentinella | ✅ validato, chiude DL-5 |
| DB-2 | Lookup | `config.motivi_fermo`, classi in CHECK (4 valori) | DL-6 «DB-first» |
| DB-3 | Anti-drift | fail-visible: non mappato ⇒ `ANOMALIA`, mai perso | §3.3 |
| DB-4 | Anzianità | `data_riferimento` additiva su resolver+union | tocca famiglia congelata, additivo |
| DB-5 | Lente 1 | nuova famiglia grana attività, riuso predicati non viste | §4 |
| DB-6 | Misura | `prezzo_snapshot×quantita` su tutti gli stadi (funnel omogeneo) + `valore_fatturato` (`imponibile_riga`) come riconciliazione | ✅ deciso (Tid 2026-07-06): il FE mostra **sempre `imponibile_riga`** come "fatturato"; `valore` teorico resta misura del funnel per gli stadi non fatturati |
| DB-7 | Competenza errori | lotto → mesi AF → mese data fattura | §4.3 |
| DB-8 | Scope | GUC fail-closed in-vista + `security_invoker=on` su tutto il nuovo | + esito V-1 |

## 12. Criteri di accettazione

1. Attività di competenza M attraversa i 4 stadi e la mensile riflette ogni passaggio
   (formato lungo coerente col dettaglio); void mai contate (parità col predicato -61).
2. Un'attività di competenza M emessa a M+2 risulta `emessa_in_ritardo`; dopo un reset
   lotto la sua `data_insert` (e quindi il flag) non cambia.
3. Backlog = solo non-verde: contratti assenti, offerte solo 🔴/🔵, `anzianita_giorni`
   calcolabile per ogni riga; contatori riepilogo = somma dettaglio; motivo non mappato
   visibile come `ANOMALIA`.
4. Un task run in `ERRORE` e una fattura `critical` compaiono nel blocco errori con la
   competenza giusta; spariscono quando risolti (run `COMPLETATO` / `critical=false`).
5. Operatore con whitelist emittente A non vede righe di emittente B in nessuna delle 5
   viste nuove; senza GUC ⇒ 0 righe (fail-closed) e pgTAP lo dimostra.
6. Famiglia `vw_dash_fatturazione_*` invariata nel contratto verso BE esistente
   (colonna nuova solo in coda; `plan(28)` esistente resta verde).
