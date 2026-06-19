# Brief DB — Normalize + guard simmetrico su `tipo_doc_fiscale_id` delle attività di commessa

> **Tipo documento**: brief operativo **per il team DB** (canale `dev/db-tid`).
> Spiega *cosa* serve e *perché*; **non contiene DDL pronto** — il *come* (nome
> funzione/trigger, firma, changeset, codice errore, pgTAP) è scelta del team DB.
>
> **Data**: 2026-06-19 · **Stato**: 🟢 **IMPLEMENTATO + pgTAP 11/11 VERDE (2026-06-19)** —
> applicato su dev DB; G0 backfill verificato non necessario (0 righe). Restano commit/merge
> e `VALIDATE CONSTRAINT` in produzione. Vedi §4 e §7.
>
> **Origine**: emerso analizzando il fix di discovery
> [brief-db-emittibili-lane-tipo-doc-fiscale.md](brief-db-emittibili-lane-tipo-doc-fiscale.md)
> (§2.2 + §4.1): le righe `APPROVATA + NON_EMESSA` con `tipo_doc_fiscale_id IS NULL`
> vengono **escluse** dalla discovery delle corsie. Quella esclusione è una **difesa
> corretta** ma, se resta l'unica linea, trasforma il problema in **fatturato perso in
> silenzio**. Questo brief chiede la correzione *assoluta* a monte, non il cerotto a valle.

---

## 1. Contesto e problema

Tracciando il modello end-to-end (rif. `gestione-commesse.md`, `fatturazione.md`):

- `vendite.commesse_attivita.tipo_doc_fiscale_id` è **nullable** (FK `config.tipi_doc_fiscale`).
- Il valore viene risolto al push da `config.sorgenti.tipo_doc_fiscale_id`
  (`fn_list_preventivi_da_pushare`, `fn_list_consumi_da_pushare`) e passato a
  `fn_upsert_commessa_attivita(p_tipo_doc_fiscale_id ...)`.
- **`fn_upsert_commessa_attivita` NON normalizza né valida** il parametro: lo scrive
  così com'è, e su `ON CONFLICT` fa `tipo_doc_fiscale_id = EXCLUDED.tipo_doc_fiscale_id`
  (può quindi anche **regredire a NULL** un valore già buono, su un re-push).
- La transizione `BOZZA → APPROVATA` (`fn_approva_commessa_attivita`) **non ha alcun
  guard** su `tipo_doc_fiscale_id`.

### Conseguenza (il bug latente)

Una riga `APPROVATA + NON_EMESSA` con `tipo_doc_fiscale_id IS NULL`:

- è **invisibile** alla discovery delle corsie (`fn_list_emittibili_lane` la esclude per
  design: il lotto richiede `tipo_doc_fiscale_id` NOT NULL);
- **nessun altro processo la ripesca** (la commessa, una volta gestita, non è più scoperta);
- → **fatturato perso in silenzio, senza alcun segnale**.

Oggi i push principali (preventivi/ordini/contratti) ereditano il `tipo_doc` dalla
sorgente, quindi i NULL attuali sono **per lo più legacy/test**. Ma **il modello non lo
garantisce**: basta una `config.sorgenti` con `tipo_doc_fiscale_id` NULL (campo nullable),
un percorso consumi, o un re-push che regredisce il valore, per riprodurlo anche in futuro.

> L'esclusione in discovery (già implementata) è la difesa giusta, ma **non deve essere
> l'unica linea**. Pattern richiesto: **normalize + guard simmetrico**
> ([feedback_normalize_guard_simmetrico]) — spostare il fallimento *dove un operatore può
> agire* (creazione/approvazione), non *a valle dove sparisce*
> ([feedback_no_quick_fix_soluzione_assoluta]).

---

## 2. Cosa serve (risultato atteso)

Due interventi simmetrici, **entrambi lato DB**:

### 2.1 Normalize all'upsert (riempire il buco da un default configurabile)

> **Premessa di dominio (decisione utente, vedi §4.1)**: il `tipo_doc_fiscale` **non ha
> una regola di business che lo deriva**. La sua semantica è **aperta e configurabile per
> azienda** (l'idea originaria front-office/back-office, es. "se da `pratiche` → FO,
> altrimenti BO", è solo un *esempio* possibile, **non** una regola vincolante da
> codificare). Quindi il normalize **non infera** il valore: si limita ad applicare un
> **default configurabile** dove esiste. L'unico requisito ferro è che **non resti vuoto**
> sullo stato emittibile (§2.2).

In `vendite.fn_upsert_commessa_attivita`:

1. **Fallback da default configurabile** (sede decisa: **(b) `config.sorgenti`**, §4.1):
   quando `p_tipo_doc_fiscale_id IS NULL`, risolverlo **dentro `fn_upsert`** da
   `config.sorgenti.tipo_doc_fiscale_id` della sorgente (`sorgente_tipo_id`), se valorizzato.
   Risoluzione **una sola volta**, DB-side, prima dell'INSERT — single source of truth.
   Il param esplicito mantiene la priorità; il default è solo fallback e può essere assente.
2. **Non regredire** un valore già buono: su `ON CONFLICT` usare
   `COALESCE(EXCLUDED.tipo_doc_fiscale_id, ca.tipo_doc_fiscale_id)` invece di
   `= EXCLUDED.tipo_doc_fiscale_id`, così un re-push che risolve NULL non sovrascrive un
   valore precedentemente risolto.

> Nota: la risoluzione resta un **fallback** (param esplicito ha priorità), idempotente, e
> **opzionale** (il default può legittimamente non esistere: un'azienda può non usare il
> `tipo_doc`). Se nessun default è configurato, il valore resta NULL e subentra il guard
> (§2.2): è lì che il sistema impone la valorizzazione **dove serve davvero**, cioè solo
> sulle righe che devono diventare emittibili.

### 2.2 Guard simmetrico fail-fast (vietare lo stato cattivo)

**Invariante di riga** da imporre:

> una riga in stato `(stato_approvazione='APPROVATA' AND stato_emissione='NON_EMESSA')`
> **deve** avere `tipo_doc_fiscale_id IS NOT NULL`.

Caratteristiche richieste:

- **È un invariante di RIGA, non di batch.** Va imposto indipendentemente dal path di
  scrittura (INSERT diretto in APPROVATA, UPDATE di approvazione, update manuale). Per
  questo la sede naturale è un **trigger `_a10_` BEFORE INSERT/UPDATE** su
  `commesse_attivita`, **non** un controllo interno alla sola `fn_approva_commessa_attivita`
  (coprirebbe un solo percorso). `BEFORE` (non AFTER) perché coesiste col CHECK backstop:
  in PostgreSQL i CHECK si valutano dopo i BEFORE trigger ma prima degli AFTER, quindi un
  guard AFTER verrebbe sempre preempato dall'errore non parlante del CHECK (verificato al
  pgTAP). Coerente con `trgfn_commesse_guard_transizione` (BEFORE `_a10_`).
- **Errore custom parlante** con codice **registrato** in `config.messaggi_errore`
  (no `E_GENERICO`), via `script.fn_log_and_raise_error`. Proposta nome:
  `E_COMMESSA_ATTIVITA_TIPO_DOC_OBBLIGATORIO` — numero assegnato dal team (zona libera ~483+).
- **Si incatena** col guard esistente `E_COMMESSA_NESSUNA_RIGA_APPROVATA` (473): una
  commessa con sole righe a `tipo_doc` NULL non porterà righe ad APPROVATA → fallirà già
  il 473 al passaggio a `PRONTA_FATTURAZIONE`. I due guard sono complementari, non
  ridondanti.

#### ⚠️ Errore da evitare (semantica sbagliata)

Un guard del tipo «la commessa ha *almeno una* riga con `tipo_doc` valorizzato» è
**l'opposto del fail-fast**: lascerebbe passare le righe NULL purché una sorella sia
valorizzata. L'invariante è **per-riga**: *ogni* riga che raggiunge `(APPROVATA, NON_EMESSA)`
deve avere il `tipo_doc`.

---

## 3. Onestà sul punto di emersione (non promettere troppo)

L'approvazione è **automatica** nel push (`_rendi_commessa_emittibile`, best-effort con
trapping per-commessa). Quindi il fail-fast del guard **non** appare a un operatore
interattivo che corregge sul momento: si manifesta come **errore loggato** in
`vendite.commesse_push_log` / `event_log` (con `correlation_id`). È comunque nettamente
meglio del silenzio:

- lo **stato cattivo** (riga emittibile non emittibile) **non si forma**;
- il problema è **osservabile** al momento giusto e **bloccante**, non a valle dove sparisce.

Il loop "operatore corregge" si chiude quindi con **osservabilità** (alert/dashboard su
push falliti per questo codice), non con la sola UI. Va dichiarato nel piano BE.

---

## 4. Decisioni prese (2026-06-19)

1. **Catena di risoluzione `tipo_doc` — nessuna derivazione di business; default opzionale
   in `config.sorgenti`.**
   Il `tipo_doc` **non si deriva** da una regola fissa (no "utility default", no
   FO/BO/`pratiche` cablati: sono solo esempi d'uso, la semantica è scelta dall'azienda).
   Catena: **`param esplicito → default da config.sorgenti (se presente) → NULL → guard §2.2`**.
   **Sede del default: opzione (b)** — la colonna **esistente**
   `config.sorgenti.tipo_doc_fiscale_id`; risoluzione **DB-side dentro `fn_upsert`** (§2.1).
   Default **opzionale**: un'azienda può non usare il `tipo_doc` finché non deve emettere.

2. **`config.sorgenti.tipo_doc_fiscale_id NOT NULL`? — NO.**
   Il default è **opzionale**: forzarlo NOT NULL romperebbe la semantica "override
   opzionale" e imporrebbe un valore anche dove l'azienda non lo usa. La garanzia di
   valorizzazione va all'**output** della risoluzione (invariante di riga §2.2), **dove
   serve** (riga emittibile), non su un input della catena. La colonna resta **nullable**.

3. **Sede del guard — trigger `_a10_` BEFORE + CHECK backstop.**
   - **Trigger `_a10_` BEFORE INSERT/UPDATE** (primario): errore parlante + codice
     registrato. Limitare l'UPDATE con
     `UPDATE OF stato_approvazione, stato_emissione, tipo_doc_fiscale_id`.
     **BEFORE, non AFTER**: il CHECK (sotto) si valuta dopo i BEFORE trigger ma prima
     degli AFTER, quindi un guard AFTER verrebbe sempre preempato dall'errore non parlante
     del CHECK (emerso al pgTAP, test 9/11).
   - **CHECK constraint** `CHECK (NOT (stato_approvazione='APPROVATA' AND
     stato_emissione='NON_EMESSA') OR tipo_doc_fiscale_id IS NOT NULL)` come **difesa in
     profondità** (backstop su ogni path se il trigger è disabilitato; errore non parlante
     SQLSTATE 23514).
   - Nuovo codice errore registrato in `config.messaggi_errore`
     (`E_COMMESSA_ATTIVITA_TIPO_DOC_OBBLIGATORIO`, id 497), via
     `script.fn_log_and_raise_error`.

4. **Re-push: no-regressione (ON CONFLICT).**
   In `fn_upsert_commessa_attivita`, su `ON CONFLICT DO UPDATE` usare
   **`tipo_doc_fiscale_id = COALESCE(EXCLUDED.tipo_doc_fiscale_id, ca.tipo_doc_fiscale_id)`**
   invece di `= EXCLUDED.tipo_doc_fiscale_id`: un re-push con valore in arrivo NULL **non
   regredisce** un tipo_doc già risolto; un cambio a un valore non-NULL resta consentito.

5. **Backfill — VERIFICATO non necessario (2026-06-19).** Censimento eseguito su entrambe
   le tabelle: **0 righe** da bonificare.
   - `vendite.commesse_attivita` con `tipo_doc` NULL su righe `APPROVATA + NON_EMESSA`: **0**.
   - `vendite.attivita_fatturabili` con `tipo_doc` NULL e `fatturato = false` (righe già
     pullate, non fatturate, invisibili al select del lotto): **0**.

   Nessun dato legacy/test da valorizzare. Il CHECK `chk_commesse_attivita_tipo_doc_emittibile`
   può quindi essere reso `VALIDATE` in sicurezza (nessuna riga violante).

---

## 5. Criteri di accettazione

- Riga `(APPROVATA, NON_EMESSA)` con `tipo_doc_fiscale_id NULL` → **rifiutata** con codice
  parlante registrato (sia su INSERT diretto sia su UPDATE di approvazione).
- Riga in altri stati (`BOZZA`, oppure `EMESSA`/`ANNULLATA`) con `tipo_doc` NULL →
  **ammessa** (l'invariante vincola solo lo stato emittibile).
- `fn_upsert_commessa_attivita` con `p_tipo_doc_fiscale_id NULL` e sorgente con
  `tipo_doc_fiscale_id` valorizzato → riga scritta con il valore risolto dalla sorgente.
- Re-push che risolve NULL su una riga con `tipo_doc` già valorizzato → valore **conservato**
  (no regressione a NULL).
- Commessa con sole righe `tipo_doc` NULL → non raggiunge `PRONTA_FATTURAZIONE`
  (fallisce 473), coerente.
- `fn_list_emittibili_lane` e la pull **invariate** (questo brief agisce a monte).

### pgTAP — fixture da verificare (rischio "guard rompe test esistenti")

Prima di introdurre il trigger, fare grep e aggiornare le fixture che inseriscono righe
`commesse_attivita` in stato APPROVATA (potrebbero usare `tipo_doc` NULL):

- `db/pgtap/vendite/test-attivita-guardrail-commessa-v1.sql`
- `db/pgtap/vendite/test-fn-batch-upsert-commessa-attivita-v1.sql`
- `db/pgtap/vendite/test-commesse-schema-v1.sql`
- `db/pgtap/vendite/test-fn-emit-attivita-propaga-audit-pricing-v1.sql`
- `db/pgtap/vendite/test-commesse-core-functions-v1.sql`
- `db/pgtap/vendite/test-fn-list-emittibili-lane.sql` — **adeguato**: la riga di fixture
  `tipo_doc` NULL era inserita in stato `APPROVATA` (per testare l'esclusione nella lane) e
  veniva rifiutata dal guard; portata in `BOZZA` (NULL lecito, riga comunque esclusa dalla
  lane). Sfuggito alla lista iniziale perché creato nello stesso commit del brief.

Nuovi test: riga APPROVATA+NULL rifiutata; riga BOZZA+NULL ammessa; normalize da sorgente;
no-regressione su re-push; catena col 473.

---

## 6. Fuori scope (BE — dopo questo brief)

- Logging/alerting dei push falliti per `E_COMMESSA_ATTIVITA_TIPO_DOC_OBBLIGATORIO`
  (riepilogo per-commessa in `commesse_push_log` / `event_log`; eventuale voce dashboard
  "righe approvabili con tipo_doc mancante").
- Nessuna modifica alla pull né a `fn_list_emittibili_lane` (restano a valle, corrette).

---

## 7. Piano DB (deliverable) — STATO

> Ordine di applicazione: **G0 (bonifica dati) → G1/G2 (codice+guard) → G3 (pgTAP) → G4
> (doc)**. Numerazione globale per data: `20260619-01/02` già usati (lane), questa serie
> parte da `-03`. **Tutti SCRITTI + APPLICATI su dev DB il 2026-06-19, pgTAP 11/11 verde.**
> Restano: commit/merge (`dev/db-tid → Tito-dev → main`) e, in produzione, il `VALIDATE
> CONSTRAINT` (sicuro: G0 ha verificato 0 righe violanti).

| # | Deliverable | Path | Stato |
| --- | --- | --- | --- |
| G0 | **Bonifica dati**: censimento righe `tipo_doc` NULL emittibili su `commesse_attivita` + `attivita_fatturabili` (§4.5) | query diagnostiche lato Tid | ✅ **VERIFICATO — 0 righe** (no-op, 2026-06-19) |
| G1 | Update `vendite.fn_upsert_commessa_attivita`: normalize da `config.sorgenti` quando param NULL (§2.1.1) + `COALESCE` no-regressione su `ON CONFLICT` (§2.1.2 / §4.4). Firma `%TYPE` preservata. | `20_code/vendite/20260619-03-update-fn-upsert-commessa-attivita-normalize-tipo-doc-mctit.yaml` | ✅ SCRITTO |
| G2a | Codice errore `E_COMMESSA_ATTIVITA_TIPO_DOC_OBBLIGATORIO` **id 497** in `config.messaggi_errore` | `80_data/sql/config/messaggi_errore.csv` + `80_data/changelog/20260619-04-upsert-messaggi-errore-tipo-doc-emittibile-mctit.yaml` | ✅ SCRITTO |
| G2b | `trgfn_commesse_attivita_guard_tipo_doc_emittibile` + trigger `_a10_` **BEFORE** INSERT OR UPDATE OF `(stato_approvazione, stato_emissione, tipo_doc_fiscale_id)` (invariante riga §2.2; BEFORE perché il CHECK preempterebbe un AFTER) | `20_code/vendite/20260619-05-create-trgfn-commesse-attivita-guard-tipo-doc-emittibile-mctit.yaml` | ✅ SCRITTO |
| G2c | CHECK backstop `chk_commesse_attivita_tipo_doc_emittibile` **NOT VALID** (difesa in profondità, §4.3) | `00_schema/vendite/20260619-06-add-chk-commesse-attivita-tipo-doc-emittibile-mctit.yaml` | ✅ SCRITTO |
| G3 | pgTAP (11 test): APPROVATA+NULL rifiutata, BOZZA+NULL ammessa, normalize da sorgente, no-regressione re-push, approvazione lecita; + **fix fixture** `test-fn-emit-attivita-propaga-audit-pricing-v1` (creava APPROVATA+NON_EMESSA senza tipo_doc) | `db/pgtap/vendite/test-guard-tipo-doc-emittibile-v1.sql` | ✅ **VERDE 11/11** (2026-06-19) |
| G4 | Doc manuale companion: `fn_upsert_commessa_attivita.md` aggiornato + `trgfn_commesse_attivita_guard_tipo_doc_emittibile.md` nuovo. Le auto-gen `funzioni/*.md` si rigenerano da DB (`gen_db_docs.py`). | `docs/it/dbzero/vendite/manual/…` | ✅ SCRITTO |
