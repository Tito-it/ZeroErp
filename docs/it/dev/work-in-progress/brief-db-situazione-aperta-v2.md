# Brief DB — Situazione aperta v2: serbatoio pre-commessa (viste ridotte agli aperti-non-chiusi)

> **Tipo**: brief DB (spec per il team DB, ramo `dev/db-tid`) · **Data**: 2026-07-08 · **Owner**: Tid
> **Design-of-record**: [brief-design-fatturazione-due-lenti.md](brief-design-fatturazione-due-lenti.md)
> §6-ter (decisioni DL-14..18, 2026-07-08). **Contesto**: la Situazione aperta v1
> (`20260707-03..06`, PR #938) è mergiata e validata in-app; alla validazione Tid ne ha
> ridefinito la semantica. Questo brief modifica **solo le 2 viste** `vw_dash_aperto_*`.
> Non in produzione: breaking change ammessi, nessuna fase di compatibilità.

---

## 0. Scopo in una riga

La Situazione aperta diventa il **serbatoio pre-commessa**: mostrare **solo** i documenti
**aperti e non conclusi** (`is_aperto AND fase <> 'CHIUSO'`), eliminando il concetto
**"transitato"** — che in una vista senza asse temporale totalizza *dalla notte dei tempi*
documenti già passati avanti o conclusi, informazione non azionabile. Le viste si
**restringono nel perimetro** e si **snelliscono nelle colonne** (via tutto il transitato).

## 1. Contesto (cosa esiste già — non ricrearlo)

Verificato sul DB vivo (doc auto-gen, 2026-07-08):

- `vendite.vw_dash_aperto_documenti` (v1): union `WHERE area <> 'COMMESSE' AND NOT
  is_abortito`, **tutte le fasi**, espone `is_transitato`, `is_aperto` (derivata),
  `valore_transitato`, `unita_transitate`.
- `vendite.vw_dash_aperto_riepilogo` (v1): `GROUP BY area, fase` con `n_documenti`,
  `n_aperti` (FILTER `is_aperto`), `valore_totale`, `valore_transitato`.
- La union **sorgente** `vw_dash_fatturazione_documenti` **NON va toccata**: continua a
  esporre `is_transitato`/`valore_transitato`/`motivo_fermo` (la Lente 2 Backlog ci vive
  sopra via `vw_dash_backlog_documenti`). Le viste `aperto` sono le **uniche** a cambiare
  → blast radius minimo.
- `data_riferimento` è già nella union (data documento; `valido_dal` per i contratti):
  basta al filtro "oltre N giorni" (che è **BE-side**, vedi §4 — nessun oggetto DB nuovo).
- `security_invoker = on` su entrambe le viste: **da preservare** (attenzione al gotcha
  `CREATE OR REPLACE` che azzera le reloptions — vedi il rework §5 del brief v1;
  ricreare con `WITH (security_invoker = on)`).

## 2. Deliverable

### SA2-1 — `vw_dash_aperto_documenti` ristretta e snellita

Perimetro nuovo (**entrambi** i predicati — DL-15):

```sql
WHERE area <> 'COMMESSE'
  AND NOT is_abortito
  AND (is_transitato IS DISTINCT FROM true)   -- solo aperti (giudizio sospeso contratti = aperto)
  AND fase <> 'CHIUSO'                         -- solo non conclusi
```

Razionale dei due filtri insieme (nessuno dei due basta da solo):
- `is_aperto` da solo lascia i **chiusi-non-transitati** → li toglie `fase<>CHIUSO`.
  Esempio corretto: **preventivo EVASO con riga residua** (`esito=POSITIVO` → *non*
  abortito, `is_transitato=false` → *non* transitato, ma `fase=CHIUSO`). ⚠️ **Correzione
  (verifica DB 2026-07-08)**: l'esempio *offerta SUPERATA* del testo originale **non è
  valido** — SUPERATA ha `esito=NEGATIVO` (seed `stati_doc_offerte`), quindi `is_abortito=true`
  ed è **già escluso da `NOT is_abortito`**, non da `fase<>CHIUSO`. Nel seed attuale *tutte*
  le fasi CHIUSO delle OFFERTE (RIFIUTATA/SUPERATA/ANNULLATA) sono NEGATIVO=abortite; il
  chiuso-non-transitato-non-abortito arriva dai terminali **POSITIVI** (es. preventivo EVASO).
- `fase<>CHIUSO` da solo lascia i **transitati-non-chiusi** (es. preventivo ACCETTATO già
  completamente smistato, resta IN_CORSO) → li toglie `is_aperto`.

Colonne da **rimuovere** (tutte costanti/prive di senso nel nuovo perimetro): `is_transitato`,
`is_aperto` (derivata — ora sempre true), `valore_transitato`, `unita_transitate`. `is_transitato`
resta usato **solo nel WHERE** (dalla union), non più esposto. Colonne che **restano**: `area,
documento_id, documento_uid, codice, emittente_fiscale_id, emittente_soggetto_ruolo_id,
cliente_display, fase, stato_codice_interno, stato_codice, valore_totale, unita_totali,
motivo_fermo, data_riferimento`. (`motivo_fermo` resta come hint informativo di riga; il team
valuti se droppabile — nella v2 il taglio primario è la fase, ma non fa danno tenerlo.)

### SA2-2 — `vw_dash_aperto_riepilogo` snellita

`GROUP BY area, fase` su `n_documenti` (ora = tutti aperti) e `valore_totale`. **Rimuovere**
`n_aperti` (ridondante: coincide con `n_documenti`) e `valore_transitato`. Le fasi presenti
saranno solo APERTO / IN_ATTESA / IN_CORSO (CHIUSO escluso a monte dalla dettaglio); non tutte
le aree hanno tutte le fasi (es. ORDINI/CONTRATTI senza IN_ATTESA) — il completamento a griglia
è a carico del BE come oggi.

### SA2-3 — pgTAP aggiornato

`test-vw-dash-aperto-v1.sql` → v2 (plan 10 → **14**): il perimetro esclude ora CHIUSO e i
transitati. Casi asseriti:
- (a) **transitato-non-chiuso** — invece di una fixture "transito completo" (costosa:
  `is_transitato` è derivata da *tutte* le righe transitate) si usa un **INVARIANTE data-level**
  (fallback, deciso con l'owner 2026-07-08): join stock↔union → *nessuna* riga dello stock ha
  `is_transitato=true` **né** `fase='CHIUSO'` (copre a+b, seed-agnostico).
- (b) **chiuso-non-transitato** — fixture **preventivo EVASO con riga residua** (non "offerta
  superata": vedi correzione §2): presente in union con `fase=CHIUSO`, `NOT is_abortito`,
  `is_transitato<>true`, **assente** dallo stock (tolto *solo* da `fase<>CHIUSO`).
- (c) contratto ATTIVO → **presente** (IN_CORSO); commessa/abortito → **assenti**.
- **Strutturali**: colonne transitato assenti da `vw_dash_aperto_documenti`
  (`is_transitato/is_aperto/valore_transitato/unita_transitate`) e da `_riepilogo`
  (`n_aperti/valore_transitato`) via `information_schema.columns`.
- Scope RLS invariato (FORCE + GUC come v1); `fase` mai NULL conservato. Regressione Lente 2
  Backlog: **zero** (viste backlog non toccate).

### SA2-4 — `security_invoker`, ordine DROP+CREATE, indici

- ⚠️ **Vincolo tecnico (verifica DB 2026-07-08): NON è un `CREATE OR REPLACE`.** Le v2
  **rimuovono** colonne; PostgreSQL su `CREATE OR REPLACE VIEW` consente solo di *aggiungere*
  colonne in coda. Serve **`DROP VIEW` esplicito**. E poiché `vw_dash_aperto_riepilogo` dipende
  da `vw_dash_aperto_documenti`, l'ordine è obbligato (niente CASCADE — fail-fast):
  1. `DROP VIEW vw_dash_aperto_riepilogo` → 2. `DROP VIEW vw_dash_aperto_documenti` →
  3. `CREATE VIEW vw_dash_aperto_documenti` → 4. `CREATE VIEW vw_dash_aperto_riepilogo`.
  Realizzato in 2 changeset: `20260708-03` (drop riepilogo + drop/create documenti) e
  `20260708-04` (create riepilogo).
- Ricreare entrambe le viste **`WITH (security_invoker = on)`** (il DROP azzera le reloptions).
  Rete di sicurezza: `test-vw-dash-security-invoker.sql` (guard dinamico su tutta la famiglia
  `vw_dash_*`) fallisce da solo se il `WITH` viene dimenticato.
- Indici: il filtro "oltre N giorni" è BE-side su `data_riferimento` (già nella union); nessun
  indice nuovo richiesto per il pilota. Verificare a volumi reali se serve un indice a
  espressione sulla data-documento delle tabelle sorgente (non pilot-blocking).

## 3. Invarianti / criteri d'accettazione (pgTAP)

1. **Solo aperti-non-chiusi**: ogni riga ha `fase IN ('APERTO','IN_ATTESA','IN_CORSO')` e
   `is_transitato IS DISTINCT FROM true` sulla union sorgente.
2. **Transitato-non-chiuso escluso** (accettato+smistato IN_CORSO) — caso (a) sopra.
3. **Chiuso-non-transitato escluso** (preventivo EVASO con riga residua — *non* offerta
   superata, vedi correzione §2) — caso (b) sopra.
4. **Contratti**: ATTIVO presente (IN_CORSO), CESSATO assente, ANNULLATO assente (abortito).
5. **Colonne transitato assenti** dalla dettaglio; `n_aperti`/`valore_transitato` assenti dal
   riepilogo.
6. **Riepilogo = dettaglio**: `n_documenti`/`valore_totale` per (area,fase) coerenti con
   l'aggregazione della dettaglio.
7. **Misura**: `valore_totale` valorizzato per PREVENTIVI/ORDINI, `NULL` per OFFERTE/CONTRATTI.
8. **Scope emittente**: `security_invoker=on` su entrambe (assert su `pg_class.reloptions`,
   come il guard del brief v1); FORCE RLS + GUC → emittente altrui invisibile.
9. **Regressione zero** su `vw_dash_backlog_*` e sulla union `vw_dash_fatturazione_documenti`.

## 4. Fuori scope (BE/FE, dopo il DB) — vedi [brief-be-fe-situazione-aperta-v2.md](brief-be-fe-situazione-aperta-v2.md)

- Filtro **"aperti da oltre N giorni"**: puramente **BE-side** (WHERE `data_riferimento <=
  current_date - N`), **solo sul drill-down** (le card restano la fotografia completa — DL-17).
  Nessun oggetto DB, nessuna colonna nuova.
- Rimozione del parametro/toggle `solo_aperti` (endpoint + FE).
- Donut per fase, `DASH_APERTO_FASI` a 3 fasi, TypedDict snelliti, i18n.

---

## 5. Piano di sviluppo (checklist — si spunta mano a mano)

> Ramo `dev/db-tid`. Numerazione globale per data confermata (2026-07-08: `-01/-02` occupati →
> v2 usa `-03/-04`). Nessun commit/applicazione DB senza "procedi" esplicito dell'owner.

- [x] **D1 — `20260708-03-recreate-vw-dash-aperto-documenti-v2`** *(scritto 2026-07-08)*
      DROP riepilogo + DROP documenti + CREATE documenti v2 (4 predicati, `WITH (security_invoker=on)`,
      via colonne transitato); `runOnChange:false`, preCond union esiste.
- [x] **D2 — `20260708-04-recreate-vw-dash-aperto-riepilogo-v2`** *(scritto 2026-07-08)*
      CREATE riepilogo v2 (`n_documenti`, `valore_totale`; via `n_aperti`/`valore_transitato`);
      `WITH (security_invoker=on)`, preCond documenti esiste.
- [x] **D3 — rework pgTAP `test-vw-dash-aperto-v1.sql`** *(scritto 2026-07-08)*
      plan 10 → 14: strutturali colonne rimosse, caso (b) EVASO, invariante fallback caso (a),
      contratto/commessa/abortito, riepilogo=dettaglio, fase mai NULL, scope RLS FORCE.
- [x] **D5 — manuali `vw_dash_aperto_{documenti,riepilogo}.md`** *(aggiornati 2026-07-08)*
      perimetro v2, colonne rimosse, nota DROP+CREATE. (Auto-gen `views/*.md`: la rigenera Tid.)
- [x] **Applicazione DB** (owner/Tid, 2026-07-08): `-03`→`-04` applicate; pgTAP
      `test-vw-dash-aperto-v1.sql` **verde**.
- [x] **Non-regressione** (2026-07-08): suite `vw_dash_*` **verde** (union/backlog non toccate).
- [ ] **Rigen doc auto-gen** dbzero (Tid) sulle 2 viste.
- [ ] **Chiusura**: spostare questo brief in `work-done`; sbloccare il gate BE/FE
      (`brief-be-fe-situazione-aperta-v2.md`, `feedback_be_fe_attende_prerequisiti_db`).

---

*A chiusura: aggiornare la doc manuale `vw_dash_aperto_{documenti,riepilogo}.md` (perimetro
v2, colonne rimosse) e spostare questo brief in `work-done` a viste applicate + pgTAP verdi.*
