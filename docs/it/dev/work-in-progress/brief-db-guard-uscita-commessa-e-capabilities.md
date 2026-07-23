# Brief DB — Guard di uscita commessa, arco mancante e capabilities con motivo

> **Tipo**: brief operativo per il **team DB** · **Target**: `dev/db-tid` · **Data**:
> 2026-07-23 · **Owner**: Tid · **Stato**: ☑ **SVILUPPATO — da applicare/testare**
> (2026-07-24) · **Priorità**: 🟠 ALTA
> (perdita **irreversibile** di righe fatturabili e sotto-riporto della dashboard
> di competenza: nessuna via applicativa di recupero — vedi §0).
>
> **Perimetro**: DB (guard, matrice, capabilities, testata) **+ una riga di BE**
> (§6.1, obbligatoria e contestuale: senza, la difesa applicativa del cambio
> stato si apre). **FE: zero modifiche** — il contratto `enabled`/`reasons` è già
> supportato dal mapper condiviso (§6.2).
>
> **Origine**: richiesta del team BE (step E-DB-1..4) a corredo di
> [brief-be-fe-processi-fatturazione.md](brief-be-fe-processi-fatturazione.md),
> più l'analisi critica del 2026-07-23 che ne ha riformulato due punti (§1).
>
> **Contesto**: non siamo in produzione ([[project_no_produzione_solo_sviluppo]])
> → guard restrittivi da subito, nessuna compatibilità da mantenere.

---

## 0. Il fatto strutturale che governa tutto il brief

`CHIUSA` e `ANNULLATA` sono **stati terminali irreversibili**. Verificato sul
seed vivo ([transizioni_stati_commessa.csv](../../../../db/changelog/migrations_v2/80_data/sql/vendite/transizioni_stati_commessa.csv),
11 righe):

```text
1 BOZZA         → 2 APERTA (auto) · 4 PRONTA (auto) · 6 ANNULLATA (manuale)
2 APERTA        → 3 IN_ESEC (auto) · 4 PRONTA (auto) · 6 ANNULLATA
3 IN_ESECUZIONE → 4 PRONTA (auto) ·                    6 ANNULLATA
4 PRONTA_FATT   → 3 IN_ESEC (riapri) · 5 CHIUSA (chiudi) · 6 ANNULLATA
5 CHIUSA        → ∅     ← nessuna transizione uscente
6 ANNULLATA     → ∅     ← nessuna transizione uscente
```

Conseguenze che valgono per ogni step:

- entrambi hanno `modificabile = false` e `emittibile = false`
  ([stati_commessa.csv](../../../../db/changelog/migrations_v2/80_data/sql/vendite/stati_commessa.csv));
- `fn_list_commesse_emittibili` filtra `sc.emittibile = true` → una commessa
  chiusa o annullata **esce per sempre** dal giro di fatturazione;
- non esiste UPDATE applicativo che la riporti indietro: la matrice non ha archi
  uscenti e `fn_cambia_stato_commessa` legge solo da lì.

**Un errore di chiusura o annullamento non è correggibile via applicazione.**
È questo che alza la priorità dei guard §2.1 e §2.2 e che ha portato a scartare
l'auto-chiusura (§1, D2).

---

## 1. Decisioni prese (Tid, 2026-07-23)

| # | Decisione | Motivo |
| --- | --- | --- |
| **D1** | **→ANNULLATA vietata con righe EMESSE** (guard) | Danno concreto e irreversibile: §2.1 |
| **D2** | **→CHIUSA vietata con righe APPROVATE+NON_EMESSE** (guard) | Chiude la simmetria col guard in ingresso già vivo: §2.2 |
| **D3** | **Il vicolo cieco si chiude aggiungendo l'arco `IN_ESECUZIONE → CHIUSA` in matrice**, NON vietando «riapri» | È un buco nel **dato**, non un eccesso di libertà dell'operatore: §2.3 |
| **D4** | **Nessuna auto-chiusura** (era DEC-1 del BE). Il DB **espone la condizione**, la UI invita, la chiusura resta un atto umano | L'evento scatenante (`fattura_riga_id`) è **reversibile**, lo stato prodotto no: §2.4 |
| **D5** | I guard e le capabilities condividono **una sola sorgente**: funzioni pure `script.fn_check_commessa_*`. Mai due copie della stessa regola | Divergerebbero al primo ritocco (no logica duplicata) |
| **D6** | `fn_get_commessa_stato` si estende in modo **additivo** (`commessa_codice`, `cliente_display`), riusando l'espressione già viva nella vista di competenza | §2.5 |
| **D7** | Il criterio di D1 è **`stato_emissione = 'EMESSA'`**, non «esiste una fattura viva» | Più restrittivo di proposito: l'annullamento è irreversibile, un falso blocco costa una riga in più, un falso permesso non si corregge. Analisi in §2.1-bis |

### Cosa NON si fa (non-obiettivi dichiarati)

- **Nessuna auto-chiusura**, in nessuna variante (D4).
- **Non si rende `CHIUSA` reversibile**: cambiare la semantica di uno stato
  terminale è una decisione di dominio, non un effetto collaterale.
- **Non si vieta «riapri»**: resta l'unica leva per togliere una commessa dal
  giro di fatturazione (`IN_ESECUZIONE` ha `emittibile = false`).
- Non si tocca `fn_upsert_commessa_attivita` né la pipeline di fatturazione.

---

## 2. Problemi e evidenze

### 2.1 →ANNULLATA con righe EMESSE (D1)

Oggi si annulla una commessa che ha righe già emesse verso fatture reali.
Non è solo semantica sporca:
[vw_dash_competenza_attivita](../../dbzero/vendite/views/vw_dash_competenza_attivita.md)
filtra `sc.codice_interno <> 'ANNULLATA'` → quelle righe **spariscono dalla
dashboard di competenza mentre le fatture restano fiscalmente vive**.
Sotto-riporto gestionale silenzioso, e irreversibile (§0).

#### 2.1-bis Perché il criterio è «EMESSA» e non «fattura viva» (D7)

`stato_emissione = 'EMESSA'` significa «uscita verso una fattura», **non**
«fatturata in via definitiva»: `fn_cleanup_fatture_by_ids` (reset lotto DRAFT)
cancella le fatture e azzera `fattura_riga_id` sulle AF, ma **non riporta
indietro `commesse_attivita.stato_emissione`**. Esiste quindi uno stato reale in
cui una commessa ha righe EMESSE il cui lotto è stato resettato e le cui fatture
non esistono più.

| Criterio | Effetto |
| --- | --- |
| **(a) `stato_emissione = 'EMESSA'`** ← **scelto (D7)** | Più restrittivo: blocca l'annullamento anche quando le fatture sono state cancellate da un reset |
| (b) esiste una fattura viva (join CA→AF con `fattura_riga_id IS NOT NULL`) | Più preciso, ma più codice e **dipendente dallo stato del lotto** |

Scelto **(a)** perché l'annullamento è irreversibile (§0): un falso blocco si
risolve con una riga in più, un falso permesso non si risolve affatto. La scelta
non è definitiva per costruzione — restringere il criterio in seguito è una
modifica della sola `EXISTS` dentro `fn_check_commessa_annullabile`, **senza
alcun impatto di contratto** su guard, capabilities, BE o FE.

### 2.2 →CHIUSA con righe APPROVATE+NON_EMESSE (D2)

Sono esattamente le righe che `fn_list_commesse_emittibili` avrebbe raccolto:
chiudere le perde, per sempre. Il guard vivo ha già la regola **speculare in
ingresso** — →PRONTA_FATTURAZIONE **richiede** ≥1 riga APPROVATA+NON_EMESSA
([trgfn_commesse_guard_transizione.md:64-87](../../dbzero/vendite/funzioni/trgfn_commesse_guard_transizione.md#L64-L87)).
Questo guard è la sua chiusura: **si entra se hai qualcosa da emettere, si esce
se non ti resta niente**.

### 2.3 Il vicolo cieco, e perché la cura è un arco (D3)

Sequenza reale: PRONTA → «riapri» → IN_ESECUZIONE con tutte le righe emesse.
Da lì `3→4` esige ≥1 APPROVATA+NON_EMESSA (non c'è), `3→5` **non esiste**, resta
ANNULLATA — che con righe emesse sarà pure vietata da D1. Commessa murata viva.

La causa non è che «riapri» sia permessa: **manca l'arco `IN_ESECUZIONE→CHIUSA`**.

1. Il guard è scritto per **leggere il grafo da tabella** («no grafo
   hardcodato», commento della fn): turare un arco mancante con un divieto
   significa correggere il dato con il codice.
2. `PRONTA_FATTURAZIONE` ha `modificabile = true` → i push entrano **senza**
   riaprire. «Riapri» non serve a ricevere lavoro: serve a **togliere la
   commessa dal giro** (`IN_ESECUZIONE` ha `emittibile = false`). Vietarla
   toglie all'operatore quella leva.
3. Lo stallo **non si raggiunge solo da «riapri»**: una commessa appena nata in
   IN_ESECUZIONE con tutte le righe in BOZZA è nello stesso vicolo. Il divieto
   non lo copre, l'arco sì.

Con D2 attivo, l'arco è **sicuro per costruzione**: da IN_ESECUZIONE si chiude
solo se non resta nulla di approvato e non emesso.

### 2.4 Perché l'auto-chiusura è stata scartata (D4)

`attivita_fatturabili.fattura_riga_id` è scritto da `fn_generate_fatture_righe`
ma **azzerato** da
[fn_cleanup_fatture_by_ids](../../dbzero/vendite/funzioni/fn_cleanup_fatture_by_ids.md)
(`fattura_riga_id = NULL, fatturato = false`), cioè dal **reset lotto DRAFT**,
operazione normale del cockpit. Sequenza rovinosa con soli passi previsti:

1. genero le fatture → l'ultima AF prende `fattura_riga_id` → il trigger chiude;
2. l'operatore fa **reset lotto** → le righe tornano fatturabili;
3. la commessa è **CHIUSA**: fuori da `fn_list_commesse_emittibili` e **senza
   archi uscenti** (§0).

Righe fatturabili vive dentro una commessa che nessuna via applicativa riapre:
peggio del problema che l'automazione voleva risolvere. Al posto suo, il DB
**espone** la condizione «non resta nulla da fatturare» tramite le capabilities
(§3.4): l'azione «Chiudi» appare abilitata e la UI la mette in evidenza, ma a
premere è una persona.

Due imprecisioni della richiesta originale, registrate perché non si ripetano:

- «non ANNULLATA/RIFIUTATA» **confonde due assi**: `stato_approvazione ∈
  BOZZA|APPROVATA|RIFIUTATA`, `stato_emissione ∈ NON_EMESSA|EMESSA|ANNULLATA`
  (CHECK in [20260224-07](../../../../db/changelog/migrations_v2/00_schema/vendite/20260224-07-create-commesse-attivita-mctit.yaml#L352-L358));
- `fattura_riga_id` sta sulle **AF**, non su `commesse_attivita`: servirebbe un
  join CA→AF, e una CA in BOZZA non ha AF.

### 2.5 Testata non identificabile (D6)

Il drawer può mostrare solo `#<PK>` mentre la lista mostra `commessa_codice`:
non correlabili dall'operatore. `cliente_display` **esiste già** come
`s.ragione_sociale_completa` con il join BA→SR→soggetti
([vw_dash_competenza_attivita.md:14](../../dbzero/vendite/views/vw_dash_competenza_attivita.md#L14)):
si riusa quell'espressione, non se ne inventa un'altra.

⚠️ Trabocchetto di naming: `fn_get_commessa_stato` ritorna **già** `sc.codice AS
stato_commessa` (codice **dello stato**). Il campo nuovo è `c.codice` (codice
**della commessa**) e va chiamato **`commessa_codice`**, come nella lista —
altrimenti si crea ambiguità proprio dove il BE lamenta la non-correlabilità.

---

## 3. Piano di sviluppo

Numerazione: sequenza **globale per data** ([[feedback_liquibase_numerazione_globale_per_data]]).
Decisioni prese il 2026-07-23, changeset creati il **2026-07-24**: `20260724-01..05`.
I due append CSV (codici errore §3.1, arco §3.5) **non consumano un numero**: i
loader `loadUpdateData` `runOnChange` esistenti li ripescano da soli.

### Convenzioni SQL applicate a tutti i changeset

Due regole che sono costate un errore in corso d'opera e vanno ricordate:

1. **`%TYPE` ovunque una firma o una colonna di ritorno specchi una colonna
   reale**, inclusa la `RETURNS TABLE` (PostgreSQL lo ammette: la grammatica
   `func_type` accetta `schema.tabella.colonna%TYPE`). ⚠️ **La doc auto-gen
   scioglie i `%TYPE` in tipi concreti**: il corpo si copia da lì, ma **firma e
   `RETURNS` vanno prese dall'ultimo YAML che definisce la funzione**, altrimenti
   si regredisce a tipi cablati ([[feedback_autogen_firma_perde_type]]).
   Restano espliciti solo i tipi che non specchiano nessuna colonna (contatori,
   aggregati). `COMMENT ON` e `DROP FUNCTION` esigono invece **tipi risolti**:
   lì `%TYPE` non si usa.
2. **Apostrofi.** Dentro i letterali `COMMENT ... IS '...'` ogni apostrofo va
   raddoppiato (`perche''`, `e''`): **basta un `perche'` non raddoppiato per
   chiudere la stringa in anticipo** e far fallire il migrate con
   *«Unterminated string literal»*. Nei commenti `--` **fuori** dai blocchi
   dollar-quoted conviene evitare del tutto gli apostrofi. Dentro
   `$function$ … $function$` sono liberi.

### 3.1 — Codici errore nuovi (append al CSV)

**File**: `db/changelog/migrations_v2/80_data/sql/config/messaggi_errore.csv`
— **solo append**, nessun loader nuovo ([[feedback_messaggi_errore_no_new_loader]]):
i `loadUpdateData` `runOnChange` esistenti ripescano il CSV. Ultimo id occupato: **557**.

| id | codice | messaggio (2 `%s`) |
| --- | --- | --- |
| 558 | `E_COMMESSA_ANNULLA_CON_RIGHE_EMESSE` | «Commessa %s: annullamento non consentito, %s riga/e già emesse.» |
| 559 | `E_COMMESSA_CHIUSURA_CON_RIGHE_PENDENTI` | «Commessa %s: chiusura non consentita, %s riga/e approvate non ancora emesse.» |

**Contratto di arità (vincolante per i motivi futuri)**: ogni motivo prodotto
dalle `fn_check_commessa_*` espone `dettaglio` numerico, e il guard solleva
sempre con la coppia `(NEW.codice, dettaglio)` → **ogni nuovo codice di questa
famiglia deve avere esattamente 2 `%s` in quest'ordine**. È ciò che permette al
guard di restare generico invece di ramificare per codice.

### 3.2 — `20260724-01` e `-02`: le due funzioni pure (D5)

`20_code/script/`, mirror di
[fn_check_ddt_emittibile](../../dbzero/script/funzioni/fn_check_ddt_emittibile.md):
**pure** (`STABLE`, non sollevano, non scrivono), ritornano `[]` se l'uscita è
lecita, altrimenti un array ordinato di
`{codice, reason, reason_key, dettaglio}`.

```sql
script.fn_check_commessa_annullabile(p_commessa_id bigint) RETURNS jsonb  -- -01
script.fn_check_commessa_chiudibile (p_commessa_id bigint) RETURNS jsonb  -- -02
```

| fn | Motivo | `reason` | `reason_key` | `dettaglio` |
| --- | --- | --- | --- | --- |
| `_annullabile` | esiste ≥1 riga con `stato_emissione = 'EMESSA'` (**D7**: criterio deliberatamente restrittivo, non «fattura viva» — §2.1-bis) | `RIGHE_EMESSE` | `vendite.commesse.azione_reason.righe_emesse` | conteggio |
| `_chiudibile` | esiste ≥1 riga `APPROVATA` + `NON_EMESSA` | `RIGHE_DA_EMETTERE` | `vendite.commesse.azione_reason.righe_da_emettere` | conteggio |

Parametro `p_commessa_id` (non il row type): serve identico al guard trigger
(`NEW.id`) e alle capabilities, e le verifiche leggono solo
`commesse_attivita`. Guard parametro standard (NULL o `<= 0` → errore parlante).

L'indice `ix_commesse_attivita_commessa_stati (commessa_id, stato_approvazione,
stato_emissione)` copre entrambe le `EXISTS`.

### 3.3 — `20260724-03`: guard di uscita nel trigger

`20_code/vendite/` — `CREATE OR REPLACE` di
`vendite.trgfn_commesse_guard_transizione` **partendo dal corpo della doc
auto-gen**, non dagli YAML ([[feedback_db_doc_first]]). Si aggiunge una **Regola 3**
dopo la Regola 2 esistente, che consuma le funzioni di §3.2 e solleva il codice
del **primo** motivo:

```sql
-- Regola 3: guard di USCITA. Speculare alla Regola 2 (ingresso a
-- PRONTA_FATTURAZIONE): si esce solo se non resta niente di vivo.
-- CHIUSA e ANNULLATA sono terminali (nessun arco uscente in matrice):
-- un errore qui non e' recuperabile per via applicativa -> fail-fast.
-- La regola vera vive nelle fn_check_* (sorgente unica, condivisa con
-- script.fn_available_actions_commessa): qui si solleva soltanto.
IF v_codice_a IN ('CHIUSA', 'ANNULLATA') THEN
  v_motivi := CASE v_codice_a
                WHEN 'CHIUSA' THEN script.fn_check_commessa_chiudibile(NEW.id)
                ELSE               script.fn_check_commessa_annullabile(NEW.id)
              END;

  IF jsonb_array_length(v_motivi) > 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'database', TG_NAME::text,
      v_motivi -> 0 ->> 'codice',
      jsonb_build_object('commessa_id', NEW.id,
                         'codice',      NEW.codice,
                         'stato_a',     v_codice_a,
                         'motivi',      v_motivi),
      NEW.tx_id,
      coalesce(NEW.codice, NEW.id::text),
      coalesce(v_motivi -> 0 ->> 'dettaglio', '0'));
  END IF;
END IF;
```

Il trigger resta `trg_commesse_a10_guard_transizione_upd` (fase `_a10_` = guard,
già in posizione). Nessun trigger nuovo.

### 3.4 — `20260724-04`: capabilities con `enabled` + `reasons`

`20_code/script/` — `CREATE OR REPLACE` di
`script.fn_available_actions_commessa`. Per ogni azione manuale della matrice si
aggiungono `enabled` e `reasons`, **shape identica a
`fn_available_actions_ddt`** (che il FE già consuma, §6.2):

- `chiudi` → `enabled = (jsonb_array_length(fn_check_commessa_chiudibile) = 0)`,
  `reasons` = l'array dei motivi;
- `annulla` → idem con `fn_check_commessa_annullabile`;
- `riapri` e ogni altra azione → `enabled = true`, `reasons = '[]'`.

⚠️ **`can_change_state` va ricalcolato sulle sole azioni abilitate**: oggi è
`jsonb_array_length(v_actions) > 0` e, con le azioni disabilitate in lista,
resterebbe sempre `true`.

Le due `fn_check_*` si chiamano **una volta sola** e si riusa il risultato per
`enabled` e `reasons` (evita la doppia valutazione per azione).

### 3.5 — Arco `IN_ESECUZIONE → CHIUSA` (D3) — solo append CSV, nessun changeset

**File**: `db/changelog/migrations_v2/80_data/sql/vendite/transizioni_stati_commessa.csv`
— **solo append**. Verificato: il loader
[20260607-05](../../../../db/changelog/migrations_v2/80_data/changelog/20260607-05-seed-transizioni-stati-commessa-mctit.yaml)
è `loadUpdateData` + `runOnChange: true` + `primaryKey: id` → **nessun loader nuovo**.

Riga `id = 12`, `stato_da_id = 3`, `stato_a_id = 5`, `attivo = t`, con lo
**stesso `meta` della transizione 10** (`4→5`): `action_key: chiudi`,
`label_key: vendite.commesse.azione_chiudi` (**chiave i18n già esistente**),
`severity: success`, `icon: pi pi-lock`, `requires_confirm: true`,
`outlined: false`, `manuale: true`.

**Ordine di applicazione garantito**: `20_code` viene eseguito prima di
`80_data` nello stesso migrate ([[feedback_liquibase_phase_ordering_preconditions]])
→ il guard §3.3 è in vigore **prima** che l'arco esista. Nessuna finestra aperta.

### 3.6 — `20260724-05`: testata identificabile (D6)

`20_code/vendite/` — `fn_get_commessa_stato`: `RETURNS TABLE` **non si modifica
con `CREATE OR REPLACE`** → `DROP FUNCTION IF EXISTS` + ricreazione
([[feedback_pg_returns_table_drop_required]]). Verificato: **nessun oggetto DB
dipende** dalla funzione.

Due colonne **in coda** alla `RETURNS TABLE` (posizione più sicura per eventuali
consumatori posizionali; il BE usa comunque colonne nominate, §6.1):

| Colonna | Origine |
| --- | --- |
| `commessa_codice varchar` | `c.codice` |
| `cliente_display varchar` | `s.ragione_sociale_completa`, via `LEFT JOIN anagrafiche.billing_account ba ON ba.id = c.billing_account_id` → `LEFT JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ba.soggetto_ruolo_id` → `LEFT JOIN anagrafiche.soggetti s ON s.id = sr.soggetto_id` |

`LEFT JOIN` obbligatorio: un BA senza soggetto non deve far sparire la riga di
stato. Entrambe le espressioni vanno aggiunte al `GROUP BY` esistente.

---

## 4. Test

### 4.1 Nuovo: `db/pgtap/vendite/test-guard-uscita-commessa-v1.sql`

Indice in testa al file (regola AGENTS.md). Copertura minima:

| # | Test |
| --- | --- |
| 1-2 | `fn_check_commessa_chiudibile` / `_annullabile` presenti |
| 3 | Arco `3→5` presente e attivo in matrice |
| 4 | `_chiudibile` ritorna motivo con commessa che ha righe APPROVATE+NON_EMESSE |
| 5 | `_chiudibile` ritorna `[]` quando non resta nulla di pendente |
| 6 | →CHIUSA con righe pendenti **rifiutata** (`throws_ok`, `P0001`) |
| 7 | **→CHIUSA da IN_ESECUZIONE senza pendenti ammessa** ← chiude il vicolo cieco (§2.3) |
| 8 | `_annullabile` ritorna motivo con righe EMESSE |
| 9 | →ANNULLATA con righe emesse **rifiutata** |
| 10 | →ANNULLATA senza righe emesse ammessa |
| 11 | Capabilities: `chiudi` con `enabled = false` + `reasons` non vuoto quando pendenti |
| 12 | Capabilities: `chiudi` con `enabled = true` e `can_change_state` coerente quando nulla pende |
| 13 | Codici **558/559** presenti in `config.messaggi_errore` |
| 14 | `fn_get_commessa_stato` espone `commessa_codice` e `cliente_display` valorizzati |

Fixture: riusare il pattern di `test-commesse-transizioni-stati-v1.sql`
(`fn_get_or_create_commessa` con `p_force_new => true`); righe sourceless come in
`test-porta-oneri-v1.sql` per non passare da `fn_emit`
([[feedback_pgtap_patterns]]).

### 4.2 Adeguamento obbligatorio ([[feedback_guard_breaks_existing_tests]])

[test-commesse-transizioni-stati-v1.sql:73-77](../../../../db/pgtap/vendite/test-commesse-transizioni-stati-v1.sql#L73-L77)
asserisce **`count(*) = 11`** sulla matrice: con l'arco nuovo va portato a **12**
(e l'indice test in testa aggiornato). Non è una regressione: è il test che
segue il modello. Il test 7 («BOZZA→CHIUSA rifiutata», `1→5`) **resta valido** e
non va toccato.

Grep di controllo prima di applicare: `grep -rn "transizioni_stati_commessa" db/pgtap/`
per intercettare altri conteggi hardcodati.

---

## 5. Contratto capabilities (per il BE/FE)

Shape emessa da `fn_available_actions_commessa` dopo §3.4, per ogni azione:

```json
{
  "key": "chiudi", "target_state": "CHIUSA",
  "label_key": "vendite.commesse.azione_chiudi",
  "severity": "success", "icon": "pi pi-lock",
  "requires_confirm": true, "outlined": false,
  "enabled": false,
  "reasons": [{
    "codice": "E_COMMESSA_CHIUSURA_CON_RIGHE_PENDENTI",
    "reason": "RIGHE_DA_EMETTERE",
    "reason_key": "vendite.commesse.azione_reason.righe_da_emettere",
    "dettaglio": 3
  }]
}
```

**Regola di lettura**: presenza in `available_actions` **non significa più
eseguibile**. Chi consuma deve guardare `enabled`.

---

## 6. Impatti fuori DB

### 6.1 BE — una riga, obbligatoria e contestuale

`backend/apps/vendite/services/commesse_service.py::cambia_stato_commessa`
costruisce la difesa applicativa così:

```python
stati_ammessi = {a.get("target_state") for a in azioni}
```

Con le azioni disabilitate nella lista, **una transizione vietata risulterebbe
ammessa** dal BE e arriverebbe al DB, che la respinge con 558/559: la difesa
applicativa (nata per bloccare le transizioni automatiche forzate via API) si
aprirebbe silenziosamente. Fix:

```python
stati_ammessi = {a.get("target_state") for a in azioni if a.get("enabled") is not False}
```

Confronto stretto con `False`, coerente col mapper FE: le azioni senza `enabled`
degradano ad abilitato. **Va rilasciato insieme al DB**, non dopo.

Nessun altro impatto BE: verificato,
[commesse_repository.py:662-669](../../../../backend/apps/vendite/db/commesse_repository.py#L662-L669)
seleziona **colonne nominate** da `fn_get_commessa_stato` → l'aggiunta di §3.6 è
additiva e non rompe il mapping posizionale. Serve solo estendere
`CommessaStatoResult` per esporre i due campi nuovi.

Codici 558/559 da registrare in `error_policies.py` → **409** (conflitto di
stato, come la famiglia immutabilità), `show_error_banner`.

### 6.2 FE — zero modifiche

Verificato: `CommessaGestioneDrawer.vue` instrada le azioni di stato attraverso
il mapper condiviso `mapAvailableActionsToDrawerActions`
([useDrawerActions.js:37-73](../../../../frontend/src/core/composables/useDrawerActions.js#L37-L73)),
che **già gestisce** `enabled: false` → pulsante **disabilitato con tooltip**
costruito da `reasons[].reason_key`, e degrada ad abilitato se `enabled` manca.
La decisione «disabled, mai nascosto» è già quella cablata lì.

Restano da aggiungere **due chiavi i18n** — `vendite.commesse.azione_reason.
righe_emesse` e `.righe_da_emettere` — in `it.json`/`en.json`. **Non
bloccanti**: `labelOrCode` è fail-visible e mostra il codice macchina se la
chiave manca, non il path né un crash.

---

## 7. Rischi

| Rischio | Valutazione |
| --- | --- |
| Guard troppo restrittivo blocca flussi esistenti | Coperto dal grep pgTAP di §4.2. Non siamo in produzione: nessun dato storico da salvare |
| L'arco `3→5` espone «Chiudi» in uno stato dove prima non c'era | Voluto (D3). Con D2 attivo è sicuro; quando ci sono pendenti compare **disabilitato con motivo** |
| Doppia valutazione delle `fn_check_*` nelle capabilities | Mitigato in §3.4: una chiamata per azione, risultato riusato |
| `DROP FUNCTION` su `fn_get_commessa_stato` | Verificato: nessun dipendente DB. Il BE usa colonne nominate |

---

## 8. Segnalazione al team BE — permesso mancante su chiusura e annullamento

> **Fuori dal perimetro di questo brief.** Non è una richiesta al team DB: è una
> cosa emersa verificando il contorno di E-DB-1, che riguarda il BE e che il
> team BE deve decidere. Qui è registrata perché non vada persa.

`ApiCommessaStato` ([views.py:635](../../../../backend/apps/vendite/api/views.py#L635))
dichiara `area_funzionale = "vendite"` ma **non ha `post_permission`**:
chiunque abbia accesso all'area vendite può portare una commessa a `CHIUSA` o
`ANNULLATA`, cioè compiere un atto **irreversibile** (§0) che può far uscire per
sempre righe fatturabili dal giro.

L'asimmetria è netta rispetto alle azioni molto meno gravi della stessa entità:
le tre operazioni di prezzo N5/N7 (`riallinea`, `variazione eccezionale`,
`sblocca`) sono gated da `prezzo_override_manuale`, e la porta oneri da
`carica_voce_manuale`. Il cambio di stato terminale non è gated da niente.

**Cosa servirebbe**, se il team BE decide di chiuderla:

- un codename in `config.azioni_processo` — nuovo (es. `chiudi_commessa`) o il
  riuso di uno esistente, è una scelta di modello permessi che spetta a voi;
- il seed CSV corrispondente (append, nessun loader nuovo) — **è l'unica parte
  che tocca il DB**: apritela come micro-prerequisito e il team DB la evade;
- `post_permission` sulla view, con il gate FE via `useActionPermission` come
  già fatto per le azioni prezzo.

Nota di interazione con questo brief: i guard §3.3 e le capabilities §3.4
riducono il **danno da errore** (non si chiude più una commessa con righe
pendenti), ma **non sostituiscono il permesso** — restano due assi diversi:
*cosa è lecito fare* e *chi può farlo*.

---

## 9. Note operative

- **Nessun punto aperto di dominio**: tutte le decisioni (D1-D7) sono chiuse.
- **Stato consegna (2026-07-24)**: DB scritto e verificato staticamente, **non
  ancora applicato**. Manufatti:

| File | Tipo |
| --- | --- |
| `20_code/script/20260724-01-create-fn-check-commessa-annullabile-mctit.yaml` | nuovo |
| `20_code/script/20260724-02-create-fn-check-commessa-chiudibile-mctit.yaml` | nuovo |
| `20_code/vendite/20260724-03-update-trgfn-commesse-guard-transizione-uscita-mctit.yaml` | nuovo |
| `20_code/script/20260724-04-update-fn-available-actions-commessa-enabled-reason-mctit.yaml` | nuovo |
| `20_code/vendite/20260724-05-update-fn-get-commessa-stato-codice-cliente-mctit.yaml` | nuovo |
| `80_data/sql/config/messaggi_errore.csv` | +2 righe (558, 559) |
| `80_data/sql/vendite/transizioni_stati_commessa.csv` | +1 riga (id 12, arco 3→5) |
| `db/pgtap/vendite/test-guard-uscita-commessa-v1.sql` | nuovo, `plan(16)` |
| `db/pgtap/vendite/test-commesse-transizioni-stati-v1.sql` | adeguato (11 → 12) |

- **Da fare all'applicazione**: `make db-migrate`, poi
  `scripts/testpgtap.sh db/pgtap/vendite/test-guard-uscita-commessa-v1.sql` e
  `scripts/testpgtap.sh db/pgtap/vendite/test-commesse-transizioni-stati-v1.sql`.
- **BE (§6.1)**: non ancora fatto — il filtro `enabled` in
  `cambia_stato_commessa`, i codici 558/559 in `error_policies.py` e i due campi
  nuovi in `CommessaStatoResult`. Da decidere se li fa il team DB in coda a
  questa slice o il team BE su `dev/backend-tid`.

---

## 10. Riferimenti

- Analisi critica di origine: sessione 2026-07-23 (steps E-DB-1..4 del BE).
- Guard vivo: [trgfn_commesse_guard_transizione](../../dbzero/vendite/funzioni/trgfn_commesse_guard_transizione.md)
- Capabilities: [fn_available_actions_commessa](../../dbzero/script/funzioni/fn_available_actions_commessa.md) ·
  pattern: [fn_available_actions_ddt](../../dbzero/script/funzioni/fn_available_actions_ddt.md) ·
  [fn_check_ddt_emittibile](../../dbzero/script/funzioni/fn_check_ddt_emittibile.md)
- Testata: [fn_get_commessa_stato](../../dbzero/vendite/funzioni/fn_get_commessa_stato.md) ·
  espressione cliente: [vw_dash_competenza_attivita](../../dbzero/vendite/views/vw_dash_competenza_attivita.md)
- Entrypoint stato: [fn_cambia_stato_commessa](../../dbzero/vendite/funzioni/fn_cambia_stato_commessa.md)
- Brief committente: [brief-be-fe-processi-fatturazione.md](brief-be-fe-processi-fatturazione.md)
