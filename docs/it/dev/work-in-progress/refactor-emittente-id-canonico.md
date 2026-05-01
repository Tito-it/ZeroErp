# Identificazione `emittenti_fiscali`: PK vs `soggetto_ruolo_id` — analisi e decisione

> **Status**: 📋 ANALISI CONCLUSA — refactor big-bang **NON da fare**.
> **Decisione**: pattern duale e' una scelta architetturale corretta, va documentata e supportata. Risolvere a livello tattico solo l'incoerenza dei filtri scope (preventivi rev2 §9).
> **Origine**: brief preventivi rev2 (sessione 2026-05-01) §4.1 + sessione di approfondimento 2026-05-02.
> **Owner**: DB
> **Branch**: `dev/db-tid`

---

## 1. Domanda iniziale

Il brief preventivi rev2 §9 segnalava un mismatch tra:

* `vw_preventivi_list.emittente_fiscale_id` (PK reale di `anagrafiche.emittenti_fiscali`)
* `script.fn_get_emittenti_scope_sr_ids` (ritorna array di `soggetto_ruolo_id`)

usato come filtro scope in `preventivi_repository.py:81-87`. Il filtro confronta PK con SR-id → strutturalmente errato (in dev "funziona per caso" su ID coincidenti).

L'ipotesi iniziale era: **dualita' di identificatori = errore architetturale**, da risolvere con refactor big-bang verso PK canonico ovunque.

## 2. Verifica empirica del pattern (sessione 2026-05-02)

Investigazione su tutto il codebase ha portato a una conclusione **opposta** all'ipotesi iniziale.

### 2.1 Tutte le tabelle ruolo seguono lo stesso pattern strutturale

Quattro tabelle, identica struttura:

| Tabella ruolo | PK propria | Denorm SR |
| --- | --- | --- |
| `anagrafiche.emittenti_fiscali` | `id` | `soggetto_ruolo_id` |
| `anagrafiche.resellers` | `id` | `soggetto_ruolo_id` |
| `anagrafiche.clienti` | `id` | `soggetto_ruolo_id` |
| `anagrafiche.fornitori` | `id` | `soggetto_ruolo_id` |

### 2.2 Tutte le tabelle dei documenti referenziano via SR id, non PK

Inventario delle FK nei documenti vendite/acquisti:

| Da → A | Colonna | Tipo |
| --- | --- | --- |
| `vendite.fatture` → emittente | `emittente_soggetto_ruolo_id` | SR id |
| `vendite.fatture` → reseller | `reseller_soggetto_ruolo_id` | SR id |
| `vendite.ordini` → cliente | `soggetto_ruolo_id` | SR id |
| `vendite.commesse` → emittente | `emittente_soggetto_ruolo_id` | SR id |
| `vendite.listini` → emittente | `emittente_soggetto_ruolo_id` | SR id |
| `vendite.listini_associazioni` → emittente | `emittente_soggetto_ruolo_id` | SR id |
| `vendite.fatture_arrotondamenti_scope` → emittente | `emittente_soggetto_ruolo_id` | SR id |
| `vendite.fatturazione_lotti` → emittente | `emittente_soggetto_ruolo_id` | SR id |
| `vendite.registri_fatturazione` → emittente | `emittente_soggetto_ruolo_id` | SR id |
| `anagrafiche.emittenti_fiscali_billing_account` → emittente | `emittente_soggetto_ruolo_id` | SR id |

Il pattern `_soggetto_ruolo_id` e' **sistemico in tutto il dominio "ruolo come parte contrattuale"**.

### 2.3 Le tabelle che usano PK lo fanno con motivazione semantica diversa

Inventario delle FK che usano PK reale:

| Tabella | Colonna | Motivazione |
| --- | --- | --- |
| `config.user_emittenti_fiscali` | `emittente_fiscale_id` (PK) | scope utente — riferisce l'entita' EF per i suoi attributi business (attivo, default) |
| `config.parameter_overrides` | `emittente_fiscale_id` (PK) | override parametri legati all'entita' EF |
| `vw_preventivi_list` | `emittente_fiscale_id` (PK, dal `20260407-03`) | filtro scope, riferisce l'entita' EF |
| `vendite.preventivi` | `emittente_fiscale_id` (PK, da rev2) | snapshot user-derived: l'operatore ha l'EF nello scope |

Tutte tabelle che parlano dell'**entita' EF** in quanto tale, non del "soggetto in quel ruolo durante il contratto".

## 3. La duplicita' e' intenzionale e necessaria

Il pattern duale corrisponde a **due semantiche diverse** che non si possono unificare senza perdita:

### 3.1 Riferimento via SR id (`<ruolo>_soggetto_ruolo_id`)

Significa: "il **soggetto** X nel **ruolo** Y, con la sua validita' temporale".

**Quando e' la scelta giusta**:

* Documenti contrattuali (fatture, ordini, contratti, commesse, listini) che devono ricordare l'identita' del partecipante "all'istante del contratto"
* Snapshot legali (es. la fattura emessa stampa la ragione sociale dell'emittente vigente al momento)
* Query che fanno JOIN diretto a `soggetti_ruoli` per ragione sociale, codice fiscale, indirizzi (un solo hop)
* Pattern uniforme cross-ruolo: emittente, reseller, cliente, fornitore — tutti referenziati allo stesso modo

### 3.2 Riferimento via PK (`<ruolo>_<entita>_id`, es. `emittente_fiscale_id`)

Significa: "l'**entita** EF X con i suoi attributi business (attivo, is_default, matricola, scope)".

**Quando e' la scelta giusta**:

* Tabelle di scope/permessi che selezionano l'EF per i suoi attributi (`attivo`, `is_default`, `matricola`)
* Override parametrici che dipendono da chi e' l'EF in quanto entita'
* Snapshot user-derived dove l'operatore "appartiene" a un EF (l'entita', non un suo SR storico)
* Filtri che devono essere stabili rispetto a cambi di SR (es. rinnovo del ruolo crea nuovo SR ma non cambia l'entita' EF)

### 3.3 Il vero "bug" del brief preventivi rev2 §9

Non e' la dualita' — e' l'aver **confrontato un campo PK con un array SR**:

* `vw_preventivi_list.emittente_fiscale_id` espone PK (corretto: la lista parla dell'entita')
* `script.fn_get_emittenti_scope_sr_ids(user_id)` ritorna array SR
* Il filtro `WHERE p.emittente_fiscale_id = ANY(fn_sr_ids(user_id))` e' **type-mismatch semantico**

La risoluzione corretta: aggiungere `fn_get_emittenti_scope_pk_ids` come fn parallela per i contesti PK. Mantenere `_sr_ids` per i contesti SR id. Documentare entrambe.

## 4. Conseguenze: NO refactor big-bang

Un refactor "PK ovunque" romperebbe:

1. **L'uniformita' cross-ruolo**: emittente diventerebbe PK, reseller/cliente/fornitore resterebbero SR → asimmetria, sviluppatori confusi.
2. **La snapshot semantics dei documenti**: fatture/ordini/contratti perderebbero il riferimento "soggetto in ruolo nel periodo Z" — sostituito da "entita' atemporale".
3. **JOIN piu' costose**: ogni query che oggi usa SR id e fa una JOIN su `soggetti_ruoli` dovrebbe fare due JOIN (`emittenti_fiscali` → `soggetti_ruoli` → `soggetti`).
4. **Per coerenza, andrebbero refattorate anche `resellers`, `clienti`, `fornitori`** — cambio strutturale enorme che non risolve niente perche' il pattern SR id e' la scelta giusta in quei contesti.
5. **Lavoro inutile**: il problema concreto (mismatch nel filtro scope) si risolve aggiungendo una fn, non riscrivendo 12 tabelle e 50 funzioni.

## 5. Soluzione adottata — 3 azioni

### 5.1 Documentare il pattern duale (priorita' assoluta)

Aggiungere alla guida [`docs/it/guide/soggetti-e-ruoli-anagrafici.md`](../../guide/soggetti-e-ruoli-anagrafici.md) una sezione canonica "Identificazione: PK reale vs `soggetto_ruolo_id`" che:

* Spiega le due semantiche (entita' vs ruolo-temporale)
* Riporta tabelle decisionali "quando usare l'uno vs l'altro"
* Cita esempi concreti dal codebase
* Vieta esplicitamente refactor "uniformanti"

Cosi' il prossimo sviluppatore (umano o AI) non ripete l'errore di pensare "qui c'e' una dualita' da eliminare".

### 5.2 Implementare `script.fn_get_emittenti_scope_pk_ids`

Nuova fn parallela a `_sr_ids`, per i contesti che filtrano su PK.

**Design (Opzione B = single source of truth per i guard)**:

* `fn_get_emittenti_scope_pk_ids(p_auth_user_id integer) RETURNS bigint[]` — fn **canonica**: implementa tutti i guard (no identita' OPERATORE → `'{}'`; super admin → NULL; altrimenti whitelist PK).
* `fn_get_emittenti_scope_sr_ids(p_auth_user_id integer)` — refactored come **wrapper thin** su `_pk_ids` con mappatura PK→SR.

Vantaggi:

* Single source of truth per la logica scope (zero drift)
* `_sr_ids` esistente migra in modo retrocompatibile (firma identica, semantica identica)
* Nuovi caller PK usano `_pk_ids` direttamente
* Performance: `_sr_ids` fa un join in piu' rispetto a oggi, ma trascurabile (chiamato 1 volta per request)

### 5.3 Verifiche pre-implementazione (gia' completate in sessione)

* Source di `fn_get_emittenti_scope_sr_ids` letto: confermato che **non filtra `ef.attivo`** (vedi [migration 20260419-15](../../../db/changelog/migrations_v2/20_code/script/20260419-15-update-fn-get-emittenti-scope-sr-ids-mctit.yaml)). Motivazione: per costruzione un EF in `user_emittenti_fiscali` e' sempre attivo (trigger `dbops.trgfn_child_requires_active_parent` blocca INSERT/UPDATE su EF non attivo + `dbops.trgfn_prevent_deactivate_if_children` blocca disattivazione). Quindi `_pk_ids` non deve aggiungere il filtro: per parita'.
* Helper `script.fn_has_identita_attiva` e `script.fn_is_super_admin` gia' esistenti — riusati senza modifiche.

## 6. Lavoro DB da fare (questo brief)

Tutto in una PR su `dev/db-tid`.

### 6.1 Migration

| File | Scopo |
| --- | --- |
| `20_code/script/<DATA>-XX-create-fn-get-emittenti-scope-pk-ids-mctit.yaml` | CREATE OR REPLACE `fn_get_emittenti_scope_pk_ids` (canonica) |
| `20_code/script/<DATA>-XX-update-fn-get-emittenti-scope-sr-ids-as-wrapper-mctit.yaml` | CREATE OR REPLACE `fn_get_emittenti_scope_sr_ids` come wrapper su `_pk_ids` (`runOnChange:true`) |

### 6.2 Test pgTAP

`db/pgtap/script/test-fn-get-emittenti-scope-pk-ids.sql` con:

* Test 1: `auth_user_id` NULL/<= 0 → guard
* Test 2: utente senza identita' OPERATORE → `'{}'`
* Test 3: super admin → NULL
* Test 4: utente con whitelist non vuota → array di PK reali
* Test 5: utente senza whitelist (whitelist NULL post-aggregato) → NULL
* **Test 6 PARITY** (cross-fn): per ogni utente di test, `cardinality(_sr_ids) = cardinality(_pk_ids)` (eccetto valori NULL passthrough)
* **Test 7 mapping correttezza**: per ogni utente con whitelist, `_pk_ids` matcha `array_agg(ef.id WHERE ef.soggetto_ruolo_id = ANY(_sr_ids))`

### 6.3 Documentazione

| File | Scopo |
| --- | --- |
| `docs/it/dbzero/script/manual/fn_get_emittenti_scope_pk_ids.md` | Manual nuova fn |
| `docs/it/dbzero/script/manual/fn_get_emittenti_scope_sr_ids.md` | Manual aggiornato (segnalare wrapper) |
| `docs/it/guide/soggetti-e-ruoli-anagrafici.md` | Nuova sezione "Identificazione: PK reale vs `soggetto_ruolo_id`" |
| `docs/it/dev/work-in-progress/risposta-db-brief-preventivi-rev2.md` | §4.1 aggiornato: punto risolto, link a questo doc |

### 6.4 Tabella decisionale (da includere in guida)

| Filtri su... | Tipo colonna | Usa fn... |
| --- | --- | --- |
| `<doc>.<ruolo>_soggetto_ruolo_id` (fatture, ordini, commesse, listini, BA scope, search universale, lista clienti) | SR id | `fn_get_emittenti_scope_sr_ids` |
| `<config>.<ruolo>_fiscale_id` (vw_preventivi_list, parameter_overrides, user_emittenti_fiscali, preventivi rev2) | PK reale | `fn_get_emittenti_scope_pk_ids` |
| Riferimento "entita' EF" con suoi attributi business | PK reale | `fn_get_emittenti_scope_pk_ids` |

## 7. Lavoro Backend (gestito da BE, qui solo elenco)

Per completezza, il BE deve poi:

1. Aggiungere `PermissionResolver.get_emittenti_pk_ids` simmetrico a `get_emittenti_sr_ids` (wrapper sulla nuova fn)
2. Sostituire i filtri PK-vs-SR in [`preventivi_repository.py:81-87`](../../../backend/apps/vendite/db/preventivi_repository.py#L81-L87) e [`vendite_repository.py:39-41`](../../../backend/apps/vendite/db/vendite_repository.py#L39-L41) con `_pk_ids`
3. Verificare che gli altri caller di `_sr_ids` siano filtri SR id (i.e. `efba.emittente_soggetto_ruolo_id`, `vendite.fatture.emittente_soggetto_ruolo_id`, ecc.) — se si', restano invariati

DB lato non ha altre azioni dopo l'implementazione di questo brief.

## 8. Cosa NON va fatto

Per evitare ambiguita' a chi legge in futuro:

* ❌ Non rinominare `emittente_soggetto_ruolo_id` in `emittente_fiscale_id` nelle tabelle documenti — il pattern SR id e' intenzionale.
* ❌ Non rinominare `fn_get_emittenti_scope_sr_ids` — ha caller che si aspettano SR id.
* ❌ Non droppare `anagrafiche.fn_get_emittente_fiscale_id` (che nonostante il nome ritorna SR id) — ha 36 caller in fn vendite che lo usano correttamente per join SR. Il nome e' fuorviante ma la logica e' corretta. Eventuale rinomina futura va valutata in un brief separato come pulizia cosmetica, non architetturale.
* ❌ Non refactorare `clienti`/`fornitori`/`resellers` per simmetria con emittenti_fiscali — cambierebbe il pattern uniforme senza beneficio.
* ❌ Non aggiungere il filtro `ef.attivo` in `_pk_ids` o `_sr_ids` — gia' garantito dai trigger di constraint su `user_emittenti_fiscali`/`emittenti_fiscali`.

## 9. Memoria progetto da aggiornare

`feedback_emittente_pk_vs_soggetto_ruolo` — **NON rimuovere**, ma **aggiornare** con questa decisione: la dualita' e' intenzionale, la documentazione (sezione nuova in `soggetti-e-ruoli-anagrafici.md`) e la tabella decisionale sono la single source of truth per i futuri sviluppatori.

## 10. Tracking

* Brief sessione 2026-05-01: [risposta-db-brief-preventivi-rev2.md](risposta-db-brief-preventivi-rev2.md) §4.1 → questo doc come risoluzione
* Sessione di analisi: 2026-05-02 (verifica empirica pattern SR id)
* Memoria: `feedback_emittente_pk_vs_soggetto_ruolo` aggiornata con la decisione

---

*Documento creato dal DB agent il 2026-05-02 a conclusione dell'analisi del pattern.*
*Implementazione (§6) in corso nella stessa PR.*
