# Brief DB — Guard sorgente polimorfa: chiudere il buco, non rattopparlo

> **Stato**: **APPLICATO + TESTATO VERDE** (2026-07-18 sera) — deliverable completo in §6:
> migrations 20260718-15..19 EXECUTED, seed fix, pgTAP tutti verdi (nuovo plan(18) +
> 4 test adattati + regressione). **Decisioni D1..D6 tutte chiuse** (D6 ri-decisa dopo
> il reperto R1: resta staccato, condizione di riaggancio nel manuale
> `attivita_fatturabili`). Restano: rigenerazione doc auto-gen (al prossimo migrate/gen)
> e **commit su «procedi»**.
> **Origine**: scrivendo `vw_stato_sorgente_ddt` è emerso che la chiave giusta era `id::text`
> e non l'uid — e controllando *perché* la riga DDT viva in `commesse_sorgenti` avesse un uuid
> si è scoperto che il guard che avrebbe dovuto impedirlo **non è agganciato a nulla**, e che
> il problema è più largo di una riga.
> **Decisione di metodo (Tid, 2026-07-18)**: *«i buchi vanno chiusi e non con delle toppe»* —
> questo brief esiste per chiuderlo con un lavoro completo: guard giusto, dati bonificati,
> catena di popolamento corretta, doc allineata, test.

---

## 1. I fatti (tutti verificati sul DB vivo, 2026-07-18)

### 1a. Esistono DUE modelli di colonne-sorgente, e il guard ne conosce solo uno

**Modello A — colonne tipizzate alternative** (target di progetto del guard; il suo manuale
dice *«Esempio tipico: `vendite.attivita_fatturabili`»*):

| colonna | tipo | uso |
|---|---|---|
| `sorgente_riga` | BIGINT | **è la chiave** quando `key_selector='id'` |
| `sorgente_uid` | UUID | **è la chiave** quando `key_selector='uid'` |

Dato vivo che lo conferma: in `attivita_fatturabili` la riga con sorgente COMMESSA
(`key_selector='id'`) ha `sorgente_riga` valorizzata. Il guard
`script.trgfn_guard_sorgente_polimorfa`, così com'è scritto, valida esattamente questo
modello: `selector='id'` → legge `NEW.sorgente_riga`; `selector='uid'` → legge
`NEW.sorgente_uid` (uuid).

**Modello B — chiave unica testuale** (tabelle di collegamento polimorfe:
`pratiche.pratiche_sorgenti`, `vendite.commesse_sorgenti`):

| colonna | tipo | uso |
|---|---|---|
| `sorgente_uid` | TEXT | **la chiave**, nel formato dettato da `key_selector`: `id::text` per i tipi `id`, uuid-testo per i tipi `uid` |
| `sorgente_riga` | BIGINT | ⚠️ **NON è una chiave documento**: è *«ID di una riga specifica della sorgente (es. riga preventivo)»* (manuale `pratiche_sorgenti`) — grana di riga del link, semantica diversa |

È la convenzione documentata in `config/manual/sorgenti.md` §Convenzione chiave sorgente,
quella su cui sono costruite le `vw_stato_sorgente_*` (sei rami dal 2026-07-18).

**⚠️ Conseguenza per `sorgente_riga`: NON va cancellata.** Ha due scopi legittimi e diversi:
chiave-id nel modello A, riferimento di riga nel modello B (es. `fn_link_commessa_sorgente`
la accetta come `p_sorgente_riga` per il link a grana riga). La colonna resta; ciò che va
sistemato è il guard che la interpreta male fuori dal suo modello. *(Verificato su richiesta
Tid, che sospettava uno scopo specifico: confermato dalla doc.)*

### 1b. Il guard non è agganciato a NESSUNA tabella

```sql
SELECT ... FROM pg_trigger t JOIN pg_proc p ON p.oid=t.tgfoid
 WHERE p.proname LIKE '%sorgente_polimorfa%' AND NOT t.tgisinternal;
-- (0 righe)
```

Né a `pratiche_sorgenti`, né a `commesse_sorgenti`, né ad `attivita_fatturabili` (il suo
target di progetto). La funzione esiste, la doc del manuale sorgenti la dà per **«Guard
attivo»** — è falso oggi. E attaccarlo com'è alle tabelle del modello B sarebbe peggio che
non averlo: pretenderebbe `sorgente_riga` (che lì è sempre NULL e significa altro) e
fallirebbe ogni INSERT legittimo. Ecco perché nessuno l'ha mai attaccato: **il guard non
rispecchia il modello davvero in uso** dalle tabelle di collegamento.

### 1c. `commesse_sorgenti` viola la convenzione del modello B — e nessuno se n'è accorto

Censimento vivo (2026-07-18):

| tabella | tipo | `key_selector` | righe | formato `sorgente_uid` vivo | risolve in `vw_stato_sorgente`? |
|---|---|---|---|---|---|
| pratiche_sorgenti | PREVENTIVO | uid | 45 | uuid | ✅ 45/45 |
| pratiche_sorgenti | ORDINE_VENDITA | id | 20 | **numerico** (giusto) | ✅ 20/20 |
| pratiche_sorgenti | COMMESSA | id | 19 | **numerico** (giusto) | ⛔ 0/19 — manca il ramo COMMESSA, vedi §5 |
| commesse_sorgenti | PREVENTIVO | uid | 47 | uuid | ✅ 47/47 |
| commesse_sorgenti | ORDINE_VENDITA | id | 20 | **uuid** (SBAGLIATO) | ⛔ 0/20 |
| commesse_sorgenti | CONTRATTO | id | 2 | **uuid** (SBAGLIATO) | ⛔ 0/2 |
| commesse_sorgenti | DDT_VENDITA | id | 1 | **uuid** (SBAGLIATO) | ⛔ 0/1 |

`pratiche_sorgenti` rispetta la convenzione (popolata dal service pratiche).
`commesse_sorgenti` no: la catena **lister → orchestratore push BE → `fn_link_commessa_sorgente`**
inserisce l'**uid** anche per i tipi a chiave `id` — i lister (`fn_list_ordini_da_pushare`,
`fn_list_ddt_da_pushare`, …) emettono `sorgente_uid = <doc>.uid::text` e la fn lo stocca
com'è, senza normalizzare.

**Perché è rimasto invisibile**: l'unico consumatore odierno di `script.vw_stato_sorgente` è
`backend/apps/pratiche/db/pratiche_repository.py` (proiezione stato pratiche), che legge solo
`pratiche_sorgenti` — dove la convenzione è rispettata. Le righe sbagliate di
`commesse_sorgenti` non le interroga ancora nessuno: il bug è **latente**, non innocuo. Il
giorno in cui commesse vorrà la proiezione di stato delle sue sorgenti (o il lineage
incrocerà i link commessa), quelle righe risulteranno «non risolte» in silenzio.

**⚠️ Aggiornamento censimento (2026-07-18, sera)**: ri-eseguito, le 23 righe in forma uuid
**non ci sono più** (0 righe; causa della sparizione non indagata — probabile pulizia/reset
dei dati di test in giornata). Censita anche `attivita_fatturabili` (modello A): 1 riga viva
con sorgente a `key_selector='id'`, 0 sospette (`sorgente_riga` NULL o 0). Conseguenza:
**la fase di bonifica dati è annullata** (ex §2b). ⚠️ Ma il rubinetto è ancora aperto: ogni
push odierno può riscrivere righe in forma uuid — ripetere il censimento immediatamente
prima di applicare il fix e, se ricomparse, usare il one-shot manuale in Appendice A
(dati di test → correzione manuale, non migration: regola Workflow Safety di AGENTS.md).

### 1d. Nota di contesto: i tre usi di "sorgente_uid" NON vanno confusi

| dove | tipo | contenuto | meccanismo |
|---|---|---|---|
| `pratiche_sorgenti` / `commesse_sorgenti` | TEXT | chiave secondo `key_selector` | polimorfo (questo brief) |
| `ddt.sorgente_uid`, `resi.sorgente_uid` | UUID | uid del documento padre | colonna tipizzata diretta — FUORI da questo brief |
| `commesse_attivita.sorgente_uid` | TEXT | hash md5(segment_key) (caveat C1) | interno commesse — FUORI da questo brief |

### 1e. Reperti emersi IN SVILUPPO (2026-07-18 sera) — cambiano D6 e il seed

**R1 — il trigger su `attivita_fatturabili` era stato DROPPATO APPOSTA.** La premessa
del §1b («nessuno l'ha mai attaccato») è falsa: il trigger fu agganciato con
`20251026-02` e **rimosso deliberatamente** con `20260225-45`, motivazione a verbale:
*«nel flusso commessa-only `sorgente_tipo_id` è sempre COMMESSA e la FK
`commessa_attivita_id` copre già la validazione»*. **Conseguenza: D6 è RIAPERTA** —
la decisione «sì all'aggancio» era stata presa su premessa sbagliata. Lo sviluppo
NON riaggancia: la funzione (rinominata `_tipizzata`) resta disponibile e documentata
come non attiva; anche il drop del DEFAULT 0 su `sorgente_riga` (prerequisito
dell'aggancio) è rinviato alla ri-decisione. Da chiudere con Tid.

**R2 — `config.sorgenti`: COMMESSA puntava alla tabella SBAGLIATA.** Il seed dava a
COMMESSA (id 13) `target_table = vendite.commesse_attivita` (il marker di pipeline,
scope PIPELINE_MARKER), ma tutti i consumatori del meccanismo di collegamento usano
l'id della **commessa**: il BE scrive `str(commessa_id)` (preventivi_service →
`upsert_pratica_sorgente`), la convenzione del manuale dice «per la commessa →
id::text», il futuro ramo COMMESSA di `vw_stato_sorgente` risolverà contro
`vendite.commesse`. Col guard attivo, la validazione di esistenza sarebbe andata
contro la tabella sbagliata. **Fix applicato nel seed** (`sorgenti.csv`:
`target_table → vendite.commesse`, ripescato dal loader runOnChange): verificato che
NESSUNA funzione DB né il meccanismo di idempotenza di `commesse_attivita`
(sorgente_uid = hash md5, non risolvibile per costruzione) consulta quel
`target_table`; l'unico lettore BE (`resolve_lineage_node_uid`) è chiamato solo per
i tipi documento del lineage.

---

## 2. Cosa si fa — i quattro pezzi del lavoro completo (2b decaduto)

> Ordine pensato per non rompere mai nulla in mezzo: prima la fn scrive canonico (2a),
> poi il guard blinda la forma canonica (2c). Niente fase dati (censimento pulito, §1c);
> unico vincolo: ri-censire subito prima dell'applicazione (Appendice A se serve pulizia).

### 2a. `fn_link_commessa_sorgente` normalizza la chiave (il rubinetto)

La fn legge `config.sorgenti.key_selector` del tipo che riceve e **normalizza**:
- `key_selector='id'` + valore uuid → risolve l'uuid contro `target_table` e stocca `id::text`;
- `key_selector='id'` + valore numerico → stocca com'è;
- `key_selector='uid'` → stocca l'uuid com'è;
- `key_selector='uid'` + valore NON in formato uuid → errore parlante (no pass-through di
  spazzatura che il guard 2c respingerebbe poi con un 22P02 grezzo);
- `key_selector='id'` + valore uuid ma `target_table` SENZA colonna `uid` (caso reale:
  COMMESSA → `vendite.commesse` non ha `uid`) → errore parlante, non crash del SQL dinamico;
- valore non risolvibile → errore parlante (nuovi codici: append CSV —
  [[feedback_messaggi_errore_no_new_loader]]).

Così i chiamanti esistenti (orchestratore push BE, che passa l'uid) **continuano a
funzionare senza modifiche BE** e da subito scrivono canonico. Difesa in profondità: la fn
normalizza, il guard (2c) valida.

> Alternativa scartata: cambiare i lister perché emettano `id::text` come `sorgente_uid`.
> Toccherebbe il contratto dei lister (il BE usa quel campo anche per display/log e la
> chiave di push singolo), con più superficie di rottura e zero benefici rispetto alla
> normalizzazione nel punto unico di scrittura.

### 2b. ~~Backfill `commesse_sorgenti`~~ — ANNULLATO (censimento pulito)

Il ri-censimento del 2026-07-18 sera ha trovato **0 righe** in forma sbagliata (§1c): la
migration `80_data`, il flag `meta.backfill_warning` e la gestione dei duplicati UNIQUE
non servono più. Se prima dell'applicazione ricompaiono righe sbagliate (il rubinetto è
aperto fino alla 2a), si usa il **one-shot manuale in Appendice A** — dati di test,
niente fix software (Workflow Safety AGENTS.md). Cade così anche la finestra di
idempotenza che un backfill posticipato avrebbe aperto: il lookup della fn sulla chiave
normalizzata non troverebbe le righe legacy in forma uuid e la stessa sorgente potrebbe
essere linkata due volte (anche a due commesse diverse) — motivo per cui l'eventuale
pulizia manuale va fatta PRIMA o insieme al rilascio di 2a, mai dopo.

### 2c. Il guard giusto — due funzioni sorelle, agganciate davvero (D3+D6 chiuse)

**Modello A** — il guard attuale è corretto e si **rinomina** con nome parlante
(`script.trgfn_guard_sorgente_polimorfa_tipizzata`, migration 20260718-16): è l'unico
momento in cui rinominare è gratis — 0 trigger attaccati, solo doc da aggiornare.

> ⚠️ **Aggancio ad `attivita_fatturabili` NON eseguito**: il reperto R1 (§1e) ha
> rivelato che il trigger fu rimosso deliberatamente (20260225-45, «ridondante con FK
> `commessa_attivita_id` nel flusso commessa-only») — D6 è riaperta e va ri-decisa.
> Se si ri-deciderà per l'aggancio, i prerequisiti restano quelli individuati:
> drop del DEFAULT 0 su `sorgente_riga` (id mai valido: col guard produrrebbe
> `E_SORG_NOT_FOUND` «a vuoto» invece del parlante `E_SORG_KEY_MISSING`), verifica dei
> writer (censimento 2026-07-18: 1 riga viva, conforme), grep pgTAP esteso al modello A
> ([[feedback_guard_breaks_existing_tests]]: ~20 file toccano `attivita_fatturabili`).

**Modello B** — funzione sorella **nuova** (es. `trgfn_guard_sorgente_polimorfa_testuale`):
valida `sorgente_uid` TEXT secondo `key_selector` (`id` → `WHERE id = uid::bigint` con
guardia sul formato; `uid` → `WHERE uid = uid::uuid`). Da **agganciare a
`pratiche_sorgenti` e `commesse_sorgenti`** (INSERT + UPDATE OF colonne sorgente).
Naming trigger: convenzione `trg_<tabella>_a10_guard_sorgente_ins_upd`.

> D3 chiusa: due funzioni sorelle, nomi parlanti — sono due semantiche diverse, meglio
> dirlo con due nomi che con un `TG_ARGV`. La verifica di `sorgente_riga` come riga
> esistente della sorgente (ex opzione qui) è la D4, rinviata a fase 2: vedi §3.

### 2d. Doc allineata (quella che oggi mente)

- `config/manual/sorgenti.md` §Convenzione: «Guard attivo» → stato reale post-fix (quali
  trigger, su quali tabelle, quale variante).
- Manuale `trgfn_guard_sorgente_polimorfa`: documentare i DUE modelli e quale variante
  protegge cosa; oggi descrive solo il modello A ma la sezione «Quando si attiva» lascia
  intendere copertura generale.
- Manuale `pratiche_sorgenti` / doc `commesse_sorgenti`: esplicitare il formato di
  `sorgente_uid` e il significato (non-chiave) di `sorgente_riga`.

### 2e. pgTAP

- Modello B: INSERT canonico passa (id-testo per tipi `id`, uuid per tipi `uid`); INSERT
  con chiave inesistente → errore; fn con uuid per tipo `id` su `commesse_sorgenti` →
  normalizzato (si legge indietro `id::text`); fn con valore non-uuid per tipo `uid` →
  errore parlante; fn con uuid per tipo `id` a target senza colonna `uid` → errore
  parlante.
- Modello A: INSERT `attivita_fatturabili` con `sorgente_riga` inesistente → errore;
  INSERT senza `sorgente_riga` (post drop DEFAULT 0) → errore chiave mancante.
- Censimento finale: la query del §1c torna 100% risolte — **escludendo il tipo COMMESSA**
  (le 19 righe a chiave giusta non risolvono per ramo mancante, §5, non per chiave:
  senza esclusione il check sembrerebbe fallito).
- Regressione: `test-proiezione-stato-sorgente` (pratiche) e i pgTAP del push commesse
  restano verdi — il guard non deve rompere i flussi vivi
  ([[feedback_guard_breaks_existing_tests]]: grep pgTAP prima di attaccare trigger).

---

## 3. Decisioni — TUTTE CHIUSE (Tid, 2026-07-18)

| # | Domanda | Decisione | Stato |
|---|---|---|---|
| D1 | `sorgente_riga`: si tiene? | **SÌ, si tiene** — doppio scopo documentato (§1a). Solo chiarire la doc | ✅ |
| D2 | Normalizzazione nella fn vs correzione dei lister | **fn normalizza** (§2a), lister e BE intatti | ✅ |
| D3 | Guard: due funzioni o una parametrizzata | **due funzioni sorelle**, nomi parlanti; rinominare l'attuale ORA (0 trigger attaccati = gratis) | ✅ |
| D4 | La variante B verifica anche `sorgente_riga` come riga esistente della sorgente? | **RINVIATA a fase 2** — il costo NON è basso: `config.sorgenti` censisce la `target_table` del documento, non la tabella righe; se si farà, via colonna `target_righe_table` in config, MAI mappa hardcoded nel guard | ✅ |
| D5 | Righe backfill non risolvibili / duplicati UNIQUE | **DECADUTA** — niente backfill (censimento pulito §1c); eventuale pulizia = one-shot manuale Appendice A | ✅ |
| D6 | Si aggancia anche ad `attivita_fatturabili` (modello A) nello stesso giro? | ~~SÌ~~ → **NO, resta staccato** (Tid, 2026-07-18 sera, dopo il reperto R1 §1e: il drop 20260225-45 era deliberato — FK `commessa_attivita_id` copre il flusso commessa-only; in più `sorgente_riga=0` è sentinella del normalize, incompatibile col guard com'è). Condizione di riaggancio e prerequisiti registrati in **doc permanente**, non qui: manuale `attivita_fatturabili` §Validazione polimorfa della sorgente | ✅ |

## 4. Fuori scope (dichiarato)

- Le colonne tipizzate dirette (`ddt.sorgente_uid`, `resi.sorgente_uid`) e il loro guard
  (hanno FK/guard propri di dominio).
- `commesse_attivita.sorgente_uid` (hash md5, caveat C1) — meccanismo interno commesse.
- Il ramo COMMESSA di `vw_stato_sorgente` (19 righe di `pratiche_sorgenti` oggi non
  risolvono perché **manca il ramo**, non per chiave sbagliata) → §5.

## 5. Reperto collaterale (registrato, non in questo brief)

Le 19 righe COMMESSA di `pratiche_sorgenti` sono a chiave **giusta** (`id::text`) ma non
risolvono: `script.vw_stato_sorgente` non ha (ancora) il ramo commessa. Dopo il 6b della
slice fatturazione i rami sono sei; il settimo (COMMESSA, catalogo `config.stati_commessa`)
è il naturale completamento. Piccolo, indipendente, stessa forma dei gemelli: candidarlo
alla prima slice utile.

---

## 6. Deliverable (SCRITTO 2026-07-18 sera — da applicare e testare)

**Migrations** (numerazione globale del giorno, dopo la slice DDT/resi che arriva a 14):

| File | Cosa fa |
|---|---|
| `20_code/vendite/20260718-15-update-fn-link-commessa-sorgente-normalizza-chiave` | §2a: la fn normalizza la chiave (uuid→id::text per tipi `id`), errori 546/547 |
| `20_code/script/20260718-16-rename-trgfn-guard-sorgente-polimorfa-tipizzata` | D3: rinomina guard modello A (+ DROP vecchio nome); NON aggancia (R1) |
| `20_code/script/20260718-17-create-trgfn-guard-sorgente-polimorfa-testuale` | §2c: guard modello B (formato + esistenza secondo `key_selector`) |
| `20_code/pratiche/20260718-18-add-trg-pratiche-sorgenti-guard-sorgente` | aggancio guard a `pratiche_sorgenti` (INSERT + UPDATE OF colonne sorgente) |
| `20_code/vendite/20260718-19-add-trg-commesse-sorgenti-guard-sorgente` | aggancio guard a `commesse_sorgenti` (idem) |

**Seed/CSV** (ripescati dai loader runOnChange, nessun changelog dedicato):

- `80_data/sql/config/messaggi_errore.csv`: +`E_SORG_FORMATO` (546),
  +`E_SORG_NORM_NON_RISOLTA` (547);
- `80_data/sql/config/sorgenti.csv`: COMMESSA `target_table` →
  `vendite.commesse` (reperto R2, §1e).

**pgTAP**:

- NUOVO `db/pgtap/script/test-guard-sorgente-polimorfa-testuale-v1.sql` —
  plan(18): oggetti in posto, guard su INSERT diretto (canonico/formato/esistenza),
  normalizzazione fn_link (pass-through, traduzione, 3 rami d'errore), censimento
  finale di convenzione su entrambe le tabelle;
- ADATTATI (chiavi sintetiche → sorgenti reali, [[feedback_guard_breaks_existing_tests]]):
  `vendite/test-fn-link-commessa-sorgente-multi-sorgente-v1.sql` (4 commesse-sorgente
  reali al posto degli 'A-xxx' PREVENTIVO),
  `vendite/test-commesse-schema-v1.sql` ('SRC-ROOT-*' → id di commesse del test),
  `vendite/test-drop-uq-commesse-attivita-src-uid-partial-v1.sql` (uuid sintetico →
  commessa del fixture; l'insert `commesse_attivita` resta com'era: non guardato),
  `pratiche/test-pratiche-sorgenti-flusso.sql` ('prev-A1-001'/'comm-A-001' → 6
  commesse reali TPS_* con cleanup).

**Doc**: manuali `trgfn_guard_sorgente_polimorfa_{tipizzata,testuale}` (nuovi),
vecchio manuale ridotto a redirect, `config/manual/sorgenti.md` (§Convenzione: guard
vero + nota COMMESSA), guida `guide/sorgente-polimorfa.md` (§2/§5), manuali
`pratiche_sorgenti`, `commesse_sorgenti`, `fn_link_commessa_sorgente`.

**Passi restanti** (aggiornato 2026-07-18 sera): migrate ESEGUITO e pgTAP TUTTI VERDI
(nuovo test + 4 adattati; in corsa sistemati: schema commesse stale in 2 test —
`stato_commessa`→`stato_commessa_id` — e visibilità per command-id nei readback 12/16
del nuovo test, ora pattern a due passi). D6 decisa: resta staccato. Restano:
(1) rigenerazione doc auto-gen; (2) commit su «procedi».

---

## Appendice A — One-shot manuale di pulizia (solo se il censimento torna sporco)

Da eseguire **a mano** sul DB di sviluppo PRIMA (o insieme) al rilascio di 2a — mai dopo
(vedi finestra di idempotenza in §2b). Dati di test → correzione manuale, non migration
(Workflow Safety AGENTS.md).

```sql
-- 1. Censimento (2026-07-18 sera: 0 righe)
SELECT cs.id, s.codice_interno, cs.sorgente_uid, cs.commessa_id, cs.ruolo_link
  FROM vendite.commesse_sorgenti cs
  JOIN config.sorgenti s ON s.id = cs.sorgente_tipo_id
 WHERE s.key_selector = 'id'
   AND cs.sorgente_uid ~* '^[0-9a-f]{8}-[0-9a-f]{4}-';

-- 2. Riscrittura uuid -> id::text (ripetere per CONTRATTO -> vendite.contratti
--    e DDT_VENDITA -> vendite.ddt)
UPDATE vendite.commesse_sorgenti cs
   SET sorgente_uid = o.id::text
  FROM config.sorgenti s, vendite.ordini o
 WHERE s.id = cs.sorgente_tipo_id AND s.codice_interno = 'ORDINE_VENDITA'
   AND cs.sorgente_uid ~* '^[0-9a-f]{8}-[0-9a-f]{4}-'
   AND o.uid = cs.sorgente_uid::uuid;

-- 3. Residui (uuid che non risolvono piu'): DELETE diretto. Attenzione: se la riga
--    era ROOT la commessa resta senza ROOT (il prossimo link la rimpiazza — ok su
--    dati di test).
```

E per il modello A (`attivita_fatturabili`), censimento pre-aggancio guard
(2026-07-18 sera: tot 1, sospette 0):

```sql
SELECT count(*) AS tot,
       count(*) FILTER (WHERE af.sorgente_riga IS NULL OR af.sorgente_riga = 0) AS sospette
  FROM vendite.attivita_fatturabili af
  JOIN config.sorgenti s ON s.id = af.sorgente_tipo_id
 WHERE s.key_selector = 'id';
```

---

*Redatto 2026-07-18 (sessione slice fatturazione DDT/resi, step 6b); decisioni chiuse,
censimenti ripetuti (puliti) e SVILUPPO COMPLETATO lo stesso giorno in serata (§6).
Prima di applicare: ripetere i censimenti (§1c / Appendice A) — il rubinetto resta
aperto finché la 20260718-15 non è applicata. Aperti: applicazione+test (Tid),
decisione D6/R1.*
