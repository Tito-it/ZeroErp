# Brief DB — Slice RESI vendita (motore resi su DDT)

> **Tipo**: brief al team DB · **Target**: `dev/db-tid` · **Data**: 2026-07-13 · **Owner**: Tid
> **Contesto**: unica slice di sviluppo DDT rimasta. Riprende la predisposizione
> fissata in `work-done/brief-db-ddt-vendita-evasione-e-stati.md` **§12**
> (invarianti: fulfillment append-only; transizioni di rientro stato ordine già
> seedate). Decisione Tid 2026-07-09: il reso è un **ibrido** — a credito oppure
> per ri-consegna.
>
> **Nota di revisione (2026-07-13, analisi critica DB).** Questo brief è stato
> rivisto contro gli oggetti DDT **vivi** (doc auto-gen, non gli YAML). La revisione
> ha corretto **premesse errate** e **omissioni strutturali** rispetto alla stesura
> iniziale: le correzioni sono raccolte in **§0** e recepite nelle sezioni. Le regole
> DB del progetto (viste `security_invoker`+RLS, numerazione fiscale bespoke, guard
> data-driven, ordinamento trigger, forward-only Liquibase) sono applicate ovunque,
> non solo dove il capitolato le nominava.
> (invarianti: fulfillment append-only; transizioni di rientro stato ordine già
> seedate). Decisione Tid 2026-07-09: il reso è un **ibrido** — a credito oppure
> per ri-consegna.
>
> **Nota di revisione (2026-07-13, analisi critica DB).** Questo brief è stato
> rivisto contro gli oggetti DDT **vivi** (doc auto-gen, non gli YAML). La revisione
> ha corretto **premesse errate** e **omissioni strutturali** rispetto alla stesura
> iniziale: le correzioni sono raccolte in **§0** e recepite nelle sezioni. Le regole
> DB del progetto (viste `security_invoker`+RLS, numerazione fiscale bespoke, guard
> data-driven, ordinamento trigger, forward-only Liquibase) sono applicate ovunque,
> non solo dove il capitolato le nominava.
>
> **Decisioni di design (Tid, 2026-07-13):**
>
> 1. **Entità autonoma con sorgente data-driven** (`sorgente_tipo_id` +
>    `sorgente_uid`, pattern del DDT): in questa slice l'unica sorgente
>    abilitata è `DDT_VENDITA`; in futuro si aggiungerà `FATTURA` senza rework.
> 2. **Tipo reso PER RIGA** (un rientro fisico può mescolare righe a credito e
>    righe da ri-consegnare).
> 3. **Nota di credito: SOLO predisposizione** (coda "da accreditare"
>    interrogabile; il branch NC è slice successiva).
> 4. **Macchina a stati data-driven** mirror DDT: gli effetti valgono solo per
>    i resi CONFERMATI.
> 5. **DDT origine → stato RESO automatico solo se reso totale**; su parziale
>    resta CONSEGNATO (la verità fine sta nelle righe reso).
> 6. **Flip DDT→RESO SOLO automatico (deciso 2026-07-13).** Il pulsante manuale
>    «Reso» oggi presente sul DDT viene **rimosso**: il DDT entra in RESO solo per
>    effetto del motore (reso totale confermato), mai flippando lo stato a mano.
>    Niente doppia strada. Vedi §0.2 e §5.3.
> 7. **Ri-consegna con aggancio DURO e ciclo completo in questa slice
>    (deciso 2026-07-13).** L'aggancio reso↔ri-spedizione è una **tabella-ponte**
>    `vendite.resi_righe_riconsegne` (mirror `ordini_righe_fulfillment`): supporta la
>    ri-spedizione **parziale/multipla** di una riga reso. Lo **stato ri-consegna è
>    DERIVATO** dalla copertura (`qta_resa` vs `Σ riconsegne.qta` →
>    `DA_RICONSEGNARE/PARZIALE/COMPLETATA`), calcolato nella vista: nessuna colonna di
>    stato fisica, nessun lookup (vedi §9). La ri-spedizione è un'azione dedicata
>    `fn_genera_ddt_riconsegna(reso)` che genera il nuovo DDT e inserisce le righe-ponte.
>    **Ammessa su qualsiasi DDT, anche standalone** (la coda è agganciata al DDT, non
>    all'ordine): niente guard "solo con ordine". Per i resi order-backed si riapre in
>    più il residuo dell'ordine (coerenza stato ordine). Vedi §0.8, §4, §5, §6, §9.

---

## 0. Rilievi critici e correzioni alla stesura iniziale

> Questa sezione elenca gli errori/omissioni trovati confrontando il brief con gli
> oggetti DDT vivi. Ogni voce è **recepita** nella sezione indicata. Numerazione
> stabile per riferimento incrociato.

**0.1 — [ERRORE DI PREMESSA] `fn_ordine_ha_residuo_evasione` NON è reso-aware.**
Il corpo vivo calcola solo `quantita − Σ qta_evasa > 0`. L'addendo
`qta_resa_per_riconsegna` **non esiste**: vive solo nel COMMENT come promessa.
Non c'è nessun placeholder «oggi = 0» da puntare, né alcuna colonna omonima. La
slice resi deve **riscrivere** la funzione (nuovo changeSet forward-only,
`CREATE OR REPLACE`) aggiungendo il sub-select sui resi. → §5.1.

**0.2 — [CONFLITTO STRUTTURALE] Il flip DDT→RESO oggi è un pulsante manuale.**
Il seed `config.transizioni_stati_ddt` ha `CONSEGNATO→RESO` (id 7) e `SPEDITO→RESO`
(id 6) con `meta.manuale:true` → oggi compaiono come azione «Reso» in
`fn_available_actions_ddt`. Col motore resi il flip è automatico e solo su reso
totale (decisione 5/6). → §5.3: `manuale:false` + rimozione azione manuale;
`SPEDITO→RESO` **rimossa** (la sorgente reso è il DDT in CONSEGNATO).

**0.3 — [GAP] `RESO→CONSEGNATO` non esiste nel seed.** La matrice DDT non ha
alcuna transizione in uscita da RESO. L'annullo di un reso che aveva flippato il
DDT deve poterlo riportare a CONSEGNATO. → §5.3: nuova riga seed `RESO→CONSEGNATO`
con `manuale:false`.

**0.4 — [SOTTO-SPECIFICATO] La numerazione non è "una sequenza".** Il numero-a-EMESSO
del DDT ha richiesto **4 oggetti**: sequenza, riga `config.sistema_codici`
(`usa_sequenza=false`), opt-out `automation_lock_columns` (lock piatto disabilitato),
trigger `gen_numero` **e** `protect_num` (immutabilità condizionale NULL→valore).
Il reso replica lo stesso pattern, con numero a **CONFERMATO**. → §2.

**0.5 — [DIFFERENZA STRUTTURALE] `config.sorgenti.DDT_VENDITA` (id 8) esiste già.**
Presente con `scope=PUSH_COMMESSA`, `target_table=vendite.ddt`, `key_selector='id'`
(rappresenta il DDT come sorgente di push a commessa). Va **riusata**, non creata; la
risoluzione del DDT di provenienza avviene per **`uid`** (come già fa il DDT-da-ordine,
che ignora `key_selector` nel path normalize). → §3.

**0.6 — [DIFFERENZA STRUTTURALE] `normalize` eredita dalla FONTE = il DDT.**
`trgfn_ddt_normalize` fa JOIN su `vendite.ordini` (sorgente ORDINE_VENDITA). Il
`trgfn_resi_normalize` è mirror **nella forma** ma JOIN su `vendite.ddt` (sorgente
DDT_VENDITA): eredita `billing_account_id/utility_id/valuta_id/emittente_fiscale_id`
dal DDT, dove sono già valorizzati (emittente `NOT NULL`). → §3.

**0.7 — [ORDINE TRIGGER] `normalize` deve firing prima del guard emittente.**
Sul DDT il guard è `trg_ddt_z10_guard_emittente_ba` (fase `z10`) e spara dopo
`trg_ddt_normalize` (ordine alfabetico dei trigger). Replicare i nomi così che
`resi_normalize` popoli BA/emittente **prima** di `resi_z10_guard_emittente_ba`.
Nota: `trgfn_resi_default_emittente` (mirror DDT) **salta le sorgenti valorizzate**;
poiché in questa slice la sorgente c'è sempre, è **predisposizione inerte** (spara
solo su un futuro reso standalone). → §3.

**0.8 — [RISOLTO CON AGGANCIO DURO] Ri-consegna anche su DDT standalone.**
Rilievo iniziale: senza ordine non c'è residuo da riaprire → la ri-consegna
sembrava impossibile. **Sciolto dall'aggancio duro (decisione 7):** la coda
ri-consegna e la chiusura sono **per-reso**, agganciate al DDT — non all'ordine.
La ri-spedizione è generata dall'azione dedicata `fn_genera_ddt_riconsegna` che
collega il nuovo DDT alla riga reso; per i resi order-backed crea in più il
fulfillment (chiude il residuo). Nessuna guard "solo con ordine". → §4/§5/§6.

**0.9 — [REGOLE] La read-side NON copia i rami DDT-specifici.**
`fn_available_actions_ddt` include `push_commessa` (via `fn_list_ddt_da_pushare`) e il
blocco `pdf` (da `stati_doc_ddt.pdf_mode`). La `fn_available_actions_reso` copia
**solo** matrice→azioni + `can_edit_*` (DRAFT) + `non_editable_fields` + `stato_codice`;
**omette** push_commessa e pdf. `stati_doc_reso` **senza** colonne pdf (resi fuori dal
motore stampa in questa slice). → §6.

**0.10 — [REGOLE] Viste `security_invoker=on` + RLS sulla base, entrambe.**
Vale sia per `vw_resi_lista` sia per `vw_resi_da_accreditare`: entrambe leggono
`resi` sotto scope emittente. La vista espone `emittente_fiscale_id` +
`emittente_fiscale_codice` (filtro applicativo BE, mirror `vw_ddt_lista`) e
`emittente_fiscale_descrizione = COALESCE(s_ef.ragione_sociale_completa, ef.descrizione)`
(brief etichetta 2026-07-13). NB: `security_invoker` non è riportato nell'auto-gen —
è un **requisito** sui nuovi oggetti, non un rilievo dedotto dalle viste esistenti. → §6.

**0.11 — [GUARD quantità] `qta_resa` ha bisogno dell'unità.** Il confronto
`Σ qta_resa ≤ quantità consegnata` deve essere nella stessa unità: `ddt_righe`
porta `quantita` (base) **e** `qta_operativa/uom_operativa_id/factor_to_base`.
`resi_righe` porta le stesse colonne operative (mirror) e il guard normalizza a base.
Lock anti-concorrenza sul modello di `trgfn_ordini_ful_guard_consistenza` (`FOR UPDATE`
serializzante). → §4.

**0.12 — [PICCOLO] `sorgente_tipo_id`/`sorgente_uid` `NOT NULL` in questa slice.**
Poiché `ddt_riga_id` è `NOT NULL`, ogni reso ha sempre una fonte DDT → coppia sorgente
`NOT NULL` (a differenza del DDT, nullable per lo standalone). → §3.

---

## 1. Vocabolario `config.tipi_reso`

Tabella codice/descrizione standard (id `INTEGER GENERATED BY DEFAULT AS IDENTITY`,
codice, `codice_interno` lockato/immutabile, descrizione, `riapre_residuo boolean
NOT NULL`, attivo, audit `data_insert/user_insert/data_update/user_update`, `tx_id`).
Seed (CSV `80_data`, loader runOnChange):

| codice_interno        | descrizione                      | riapre_residuo |
| --------------------- | -------------------------------- | -------------- |
| `RESO_A_CREDITO`      | Reso a credito (nota di credito) | `false`        |
| `RESO_PER_RICONSEGNA` | Reso per ri-consegna             | `true`         |

Nessun `IF` hardcoded nel motore: si legge il flag `riapre_residuo` (§12 del brief DDT).
Whitelist lookup generico (`core/lookup/codici`) da estendere lato BE.

## 2. Stati, transizioni e numerazione

### 2.1 Stati e transizioni reso

`config.stati_doc_reso` + `config.transizioni_stati_reso`, stesso impianto
data-driven di `stati_doc_ddt`/`transizioni_stati_ddt` (fase per le dashboard,
`meta.ui` con `action_key/label_key/severity/icon/requires_confirm/outlined/manuale`,
`available_actions` via fn dedicata):

- Stati minimi: `DRAFT` (fase APERTO) → `CONFERMATO` (fase CHIUSO) +
  `ANNULLATO` (terminale). Lo stato "ACCREDITATO" arriverà con la slice NC
  (è un seed, non un rework).
- Transizioni (tutte `manuale:true` → azioni utente): `DRAFT→CONFERMATO`,
  `DRAFT→ANNULLATO`, `CONFERMATO→ANNULLATO` (l'annullo post-conferma storna gli
  effetti: l'addendo residuo è calcolato sui soli resi CONFERMATI → l'esclusione è
  automatica, ma serve il ricalcolo/proiezione stato ordine alla transizione, §5).
- **`stati_doc_reso` SENZA colonne `pdf_mode`/`pdf_allow_allegati`** (0.9): i resi
  sono fuori dal motore stampa in questa slice.
- Guard transizione: `trgfn_resi_guard_transizione` mirror
  `trgfn_ddt_guard_transizione` (legge `config.transizioni_stati_reso`, no-op se lo
  stato non cambia, fail-fast `E_STATO_RESO_TRANSIZIONE_NON_VALIDA`), trigger `_a10_`
  su `UPDATE OF stato_doc_reso_id`.

### 2.2 Numerazione bespoke a CONFERMATO (recepisce 0.4)

Il `numero` NON è "una sequenza": è il **pattern completo del DDT** (mirror fatture),
assegnato alla **CONFERMA** (NULL in DRAFT, niente buchi fiscali da bozze scartate):

1. **Sequenza dedicata** `vendite.resi_numero_seq`.
2. **Riga `config.sistema_codici`** `codice_interno='reso'` con `usa_sequenza=false`
   (fuori dal framework che numera all'INSERT) + `prefisso/separatore/lunghezza_numero`.
3. **Opt-out `automation_lock_columns`**: disabilitare il lock piatto framework su
   `resi.numero` (create-if-not-exists; su DB esistenti serve DROP+rigenera del
   trigger lock — [[feedback_automation_lock_columns_create_if_not_exists]]).
4. **`trgfn_resi_gen_numero`** mirror `trgfn_ddt_gen_numero_emesso`: assegna il numero
   solo alla transizione a `CONFERMATO`, formato da `sistema_codici` + `nextval`.
5. **`trgfn_v_resi_protect_num`** mirror `trgfn_v_ddt_protect_num`: immutabilità
   condizionale (consente NULL→valore alla conferma, blocca ogni modifica successiva,
   codice `CODICE_NON_MODIFICABILE`).

## 3. Testata `vendite.resi`

Mirror strutturale della testata DDT dove ha senso:

- id BIGINT, uid uuidv7, numero/anno (a conferma), data, meta, audit, tx_id.
- **`sorgente_tipo_id` + `sorgente_uid`** (FK `config.sorgenti`): guard
  data-driven che in questa slice ammette solo `DDT_VENDITA` e richiede il
  DDT in stato `CONSEGNATO` (non si rende ciò che non è stato consegnato).
  N.B. servirà la riga `DDT_VENDITA` in `config.sorgenti` se non già presente
  come sorgente "in ingresso".
- Denormalizzati ereditati dal DDT sorgente via trigger normalize (mirror
  `trgfn_ddt_normalize`): `billing_account_id`, `destinatario_soggetto_ruolo_id`,
  `utility_id`, `valuta_id`.
- **`emittente_fiscale_id` NOT NULL**: stesso modello deciso il 2026-07-13
  per il DDT (vedi `work-done/brief-db-ddt-emittente-user-e-etichetta-soggetto.md`, CHIUSO) —
  ereditato dal DDT sorgente; trigger `default_emittente` da GUC user come
  fallback + `guard_emittente_ba`; RLS `rls_resi_ef_whitelist` +
  `trgfn_guard_emittente_scope` in scrittura, mirror DDT.
- `stato_doc_reso_id` FK.

## 4. Righe `vendite.resi_righe`

- `reso_id` FK, `ddt_riga_id` FK `vendite.ddt_righe` **NOT NULL** (la riga sorgente;
  quando arriverà la sorgente FATTURA si aggiungerà la colonna gemella + CHECK XOR —
  concentrico, nessun rename).
- `ordine_riga_id` derivato dalla riga DDT/fulfillment (**nullable**: DDT standalone
  non ha ordine → nessun residuo da riaprire), snapshot per alimentare l'addendo del
  residuo senza JOIN a catena. **Non** condiziona l'ammissibilità della ri-consegna
  (che ora è agganciata al DDT, decisione 7): valorizza solo l'effetto residuo quando
  l'ordine c'è.
- **Articolo/UoM + unità operativa (0.11)**: `articolo_id`, `descrizione`,
  `uom_operativa_id`, `factor_to_base`, `qta_operativa`, `quantita` (base) — **stesse
  colonne di `ddt_righe`**, derivate dalla riga DDT (immutabili: il reso non inventa
  articoli). `CHECK (quantita > 0)`.
- **`tipo_reso_id` FK `config.tipi_reso` NOT NULL** (per riga, decisione 2).
- **Aggancio duro via tabella-ponte** (decisione 7, §9): la relazione riga-reso ↔
  DDT di ri-spedizione NON è una colonna su `resi_righe`, ma la tabella
  `vendite.resi_righe_riconsegne` (definita in §4b), mirror di
  `ordini_righe_fulfillment` → supporta ri-spedizione parziale/multipla. Lo stato
  ri-consegna è **derivato** dalla copertura (nessuna colonna di stato). Ammesso solo su
  righe con `tipo_reso.riapre_residuo=true` (guard sul ponte, data-driven).
- `motivo` testo libero (+ eventuale vocabolario motivi in futuro).
- **Guard quantità (0.11)**: `Σ quantita` (base) dei resi non-ANNULLATI sulla stessa
  `ddt_riga_id` `≤ ddt_righe.quantita` (base). Guard fail-fast
  `E_RESO_QTA_SUPERA_CONSEGNATO`, con lock `FOR UPDATE` serializzante sulla riga DDT
  (mirror `trgfn_ordini_ful_guard_consistenza`: anti over-return concorrente). Normalizza
  sempre a base prima del confronto.
- Righe modificabili solo con testata in DRAFT (mirror DDT).

### 4b. Tabella-ponte ri-consegna `vendite.resi_righe_riconsegne`

Aggancio duro reso↔ri-spedizione, mirror strutturale di `ordini_righe_fulfillment`
(stesso problema: una quantità soddisfatta da N DDT nel tempo → §9 decisione R2):

- `id` `INTEGER GENERATED BY DEFAULT AS IDENTITY` (tabella tecnica).
- `resi_riga_id` FK `vendite.resi_righe` **NOT NULL**.
- `ddt_riga_id` FK `vendite.ddt_righe` **NOT NULL** (la riga del DDT di ri-spedizione).
- `qta NUMERIC CHECK (> 0)` (base, coerente con la guard quantità).
- audit + `tx_id` + `storicizza`.
- **UNIQUE `(resi_riga_id, ddt_riga_id)`** (mirror fulfillment).
- **Guard consistenza** `trgfn_resi_riconsegne_guard`: `Σ qta` per `resi_riga_id`
  `≤ resi_righe.quantita` (non si ri-spedisce più di quanto reso), lock `FOR UPDATE`
  serializzante — mirror `trgfn_ordini_ful_guard_consistenza`. Guard tipo: la
  `resi_righe` referenziata deve avere `tipo_reso.riapre_residuo=true` (data-driven).
- Popolata solo da `fn_genera_ddt_riconsegna` (§5b). Lo **stato ri-consegna** di una
  riga reso è derivato: `Σ riconsegne.qta` = 0 → `DA_RICONSEGNARE`; `< qta_resa` →
  `PARZIALE`; `= qta_resa` → `COMPLETATA` (calcolato nella vista, §6).

## 5. Effetti alla CONFERMA (fn madre, una transazione)

`vendite.fn_conferma_reso(p_reso_id bigint)` — funzione madre atomica (DB-first),
mirror di spirito di `fn_genera_ddt_da_ordine`. Guard input `p_reso_id > 0`.

1. **Riapertura residuo (recepisce 0.1).** L'addendo reso di
   `fn_ordine_ha_residuo_evasione` **oggi non esiste**: la funzione va **riscritta**
   (nuovo changeSet forward-only) portando la formula a
   `residuo = quantita − Σ qta_evasa + Σ qta_riconsegna`, dove `Σ qta_riconsegna` =
   somma di `resi_righe.quantita` con `tipi_reso.riapre_residuo = true` su resi
   **CONFERMATI**, aggregata per `ordine_riga_id`. NON toccare `qta_evasa` (append-only,
   §12 invariante 1). La funzione diventa dipendente da `vendite.resi`,
   `vendite.resi_righe`, `config.tipi_reso` → **ordinamento Liquibase**: le tabelle
   (`00_schema`) precedono il `CREATE OR REPLACE` (`20_code`); resta `plpgsql`/`STABLE`.
2. **Proiezione stato ordine**: ricalcolo alla conferma (e all'annullo post-conferma)
   via la stessa matrice/proiezione di `fn_genera_ddt_da_ordine`
   (`EVASO→PARZIALMENTE_EVASO` ecc.). Le transizioni di rientro sono già seedate
   (§12 invariante 3).
3. **Stato DDT origine (decisione 5 + 6, recepisce 0.2/0.3).** Se le quantità rese
   cumulate (resi CONFERMATI, qualunque tipo) coprono **tutte** le quantità consegnate
   del DDT (Σ per ogni `ddt_riga` = `ddt_righe.quantita`) → flip **automatico**
   `CONSEGNATO→RESO`; altrimenti nessun cambio. Il flip passa dal guard transizione DDT
   (`trgfn_ddt_guard_transizione`, matrice attiva). **Modifiche al seed
   `transizioni_stati_ddt`** (nuovo CSV append + changeSet):
   - `CONSEGNATO→RESO` (id 7): `meta.manuale` → **`false`** (non è più un bottone).
   - `SPEDITO→RESO` (id 6): **rimossa** (`attivo=false`): la sorgente reso è il DDT in
     CONSEGNATO (§3).
   - **Nuova** `RESO→CONSEGNATO` con `meta.manuale:false`: l'annullo di un reso che
     aveva flippato il DDT lo riporta a CONSEGNATO (se non resta reso totale attivo).
   - Effetto read-side: l'azione manuale «Reso» sparisce da `fn_available_actions_ddt`
     (il filtro `manuale` la esclude). Nessuna modifica alla fn: è data-driven.
4. **Coda "da accreditare" (decisione 3).** Nessuna generazione NC; le righe
   `RESO_A_CREDITO` confermate sono interrogabili via **`vw_resi_da_accreditare`**
   (riga reso + riferimenti DDT/BA/emittente/importi). **`security_invoker=on` + RLS
   sulla base + `emittente_fiscale_id` esposto** (0.10) come `vw_resi_lista`; il consumo
   arriva con la slice NC.
5. **Coda "da ri-consegnare" (decisione 7).** Le righe `RESO_PER_RICONSEGNA`
   confermate con copertura ri-consegna incompleta (`Σ resi_righe_riconsegne.qta <
   qta_resa`) sono interrogabili via **`vw_resi_da_riconsegnare`** (riga reso +
   DDT/articolo/qta residua/BA/emittente). Coda **per-reso, agganciata al DDT** →
   funziona anche per lo standalone. Stesse regole invoker/RLS/emittente della coda
   accrediti. Si auto-svuota quando la copertura raggiunge `qta_resa`.

### 5b. Azione di ri-spedizione — `vendite.fn_genera_ddt_riconsegna(p_reso_id, p_righe jsonb DEFAULT NULL)`

Funzione madre atomica che chiude il ciclo ri-consegna (aggancio duro, decisione 7).
`p_righe` = `[{resi_riga_id, qta}]` per ri-spedizione **parziale**; `NULL` = tutta la
copertura residua:

- Genera un nuovo DDT (testata da snapshot del DDT/reso di origine: destinatario,
  billing/emittente/valuta ereditati) in stato DRAFT.
- Per ogni riga `RESO_PER_RICONSEGNA` da ri-spedire (fino alla copertura residua
  `qta_resa − Σ riconsegne.qta`): crea la `ddt_righe` (copia articolo/UoM/qta dal reso)
  e inserisce **`resi_righe_riconsegne(resi_riga_id, ddt_riga_id, qta)`** → riduce la
  copertura residua di quella riga reso.
- **Se la riga reso ha `ordine_riga_id`** (DDT origine order-backed): crea anche il
  `ordini_righe_fulfillment(ordine_riga_id, ddt_riga_id, qta)` → il residuo riaperto in
  §5.1 si richiude e lo stato ordine torna coerente (proiezione via matrice). **Se è
  standalone**: nessun fulfillment, il nuovo DDT è standalone. (Doppio binario per-reso
  vs per-ordine, §9 R2.)
- Guard input `p_reso_id > 0`; guard: il reso deve essere CONFERMATO e avere almeno una
  riga ri-consegna con copertura residua (fail-fast `E_RESO_NESSUNA_RICONSEGNA_PENDENTE`);
  la guard consistenza del ponte (§4b) blocca l'over-ri-spedizione.
- Idempotenza per copertura (mirror `fn_genera_ddt_da_ordine`): righe già coperte
  saltate; concorrenza coperta dal lock `FOR UPDATE` del guard ponte.

## 6. Read-side e contorno

- **`vw_resi_lista`** mirror `vw_ddt_lista` (decodifiche, stato, sorgente DDT,
  destinatario, importi). `security_invoker=on` + RLS sulla base (0.10). Espone
  `emittente_fiscale_id` + `emittente_fiscale_codice` (filtro applicativo BE) e
  `emittente_fiscale_descrizione = COALESCE(s_ef.ragione_sociale_completa, ef.descrizione)`
  (JOIN `soggetti_ruoli sr_ef`/`soggetti s_ef`, brief etichetta 2026-07-13). Alias
  fedeli alla sorgente (linee-guida-sql §6c). Target `20_code`.
- **`script.fn_available_actions_reso`** mirror `fn_available_actions_ddt` ma
  **ridotta** (0.9): matrice `config.transizioni_stati_reso` → `available_actions`
  (filtro `manuale`), `can_change_state`, `can_edit_testata`/`can_edit_righe` (solo
  DRAFT), `non_editable_fields`, `stato_codice`. **NIENTE** `push_commessa` (nessun
  `fn_list_resi_da_pushare` in questa slice) né blocco `pdf`. Target `20_code/script`.
- **`vw_resi_da_accreditare`** (§5.4) e **`vw_resi_da_riconsegnare`** (§5): due code di
  lavoro per-reso, entrambe `security_invoker=on` + RLS sulla base + `emittente_fiscale_id`
  esposto (0.10). La coda ri-consegna espone la **copertura residua** (`qta_resa −
  Σ resi_righe_riconsegne.qta`) e lo **`stato_riconsegna` derivato**
  (`DA_RICONSEGNARE/PARZIALE/COMPLETATA`, §4b) come colonna virtuale — nessuna colonna
  fisica (§9 R1).
- **`fn_genera_ddt_riconsegna`** (§5b): azione che genera il DDT di ri-spedizione e
  popola la tabella-ponte `resi_righe_riconsegne`.
- **Storicizzazione**: `trgfn_storico_generic` su `resi` e `resi_righe` (mirror DDT) +
  tabelle storico; audit e `tx_id` gestiti dai trigger generici.
- **pgTAP** (contesto RLS operatore, mirror `test-fn-genera-ddt-da-ordine-v1`):
  guard quantità (parziale, cumulato, oltre-soglia), guard ponte ri-consegna
  (over-ri-spedizione bloccata, tipo `riapre_residuo` obbligatorio), effetti
  conferma/annullo, riapertura residuo (`fn_ordine_ha_residuo_evasione` reso-aware
  post-replace), flip DDT totale/parziale + annullo (`RESO→CONSEGNATO`), **ciclo
  ri-consegna completo incl. parziale/multiplo** (conferma → coda `da_riconsegnare` →
  `fn_genera_ddt_riconsegna` parziale → `stato_riconsegna=PARZIALE` → 2ª ri-spedizione →
  `COMPLETATA` + residuo richiuso + ordine coerente; caso order-backed E standalone),
  numerazione a CONFERMATO + immutabilità, RLS/scope (operatore vede solo i propri
  emittenti; creazione fuori scope bloccata), read-side (azioni coerenti con la matrice,
  assenza push/pdf).

## 7. Piano di sviluppo (changeSet, ordine di costruzione concentrico)

Un changeSet per file, `logicalFilePath`, `runOnChange:true` solo per fn/trigger nello
stato finale, numerazione `YYYYMMDD-NN` a sequenza globale per data. Ordine
(00_schema → 20_code → 80_data), le fasi rispettano le precondizioni:

**Fase A — schema (`00_schema`)**
1. `config.tipi_reso` (§1).
2. `config.stati_doc_reso` (§2.1, senza pdf).
3. `config.transizioni_stati_reso` (matrice, mirror `transizioni_stati_ddt`).
4. `vendite.resi` (§3, colonne + FK + `sorgente NOT NULL` + `emittente NOT NULL`).
5. `vendite.resi_righe` (§4, colonne operative + FK, senza colonna di stato).
6. `vendite.resi_righe_riconsegne` (§4b, tabella-ponte, mirror fulfillment).
7. Sequenza `vendite.resi_numero_seq` (§2.2).
8. RLS `rls_resi_ef_whitelist` su `vendite.resi` (§3).
9. Tabelle storico `resi`/`resi_righe`/`resi_righe_riconsegne`.

**Fase B — codice (`20_code`)**
10. `trgfn_resi_normalize` + trigger (JOIN su `vendite.ddt`, 0.6).
11. `trgfn_resi_default_emittente` + trigger (predisposizione inerte, 0.7).
12. `trgfn_resi_guard_emittente_ba` + trigger fase `z10` (0.7); aggancio del generico
    `script.trgfn_guard_emittente_scope('fiscale','emittente_fiscale_id')`.
13. `trgfn_resi_guard_transizione` + trigger `_a10_` (§2.1).
14. Guard `resi_righe`: quantità (`E_RESO_QTA_SUPERA_CONSEGNATO`, lock `FOR UPDATE`) +
    editabilità solo DRAFT (§4).
15. `trgfn_resi_riconsegne_guard` sulla tabella-ponte: consistenza `Σ qta ≤ qta_resa` +
    tipo `riapre_residuo=true` (§4b), lock `FOR UPDATE`.
16. `trgfn_resi_gen_numero` + `trgfn_v_resi_protect_num` + trigger (§2.2).
17. `trgfn_storico_generic` su `resi`/`resi_righe`/`resi_righe_riconsegne`.
18. **`fn_ordine_ha_residuo_evasione` v2** — `CREATE OR REPLACE` reso-aware (0.1, §5.1).
    **Precondizione**: tabelle resi già create (Fase A) — [[feedback_liquibase_phase_ordering_preconditions]].
19. **`fn_conferma_reso`** (madre: riapertura residuo + proiezione stato ordine + flip
    DDT + guardie, §5).
20. **`fn_genera_ddt_riconsegna`** (madre: genera DDT ri-spedizione + popola ponte, §5b).
21. `vw_resi_lista` (`security_invoker`, §6).
22. `vw_resi_da_accreditare` (`security_invoker`, §5.4).
23. `vw_resi_da_riconsegnare` (`security_invoker` + copertura/`stato_riconsegna`, §5/§6).
24. `script.fn_available_actions_reso` (ridotta, §6).
25. **Update seed matrice DDT** — `transizioni_stati_ddt`: `CONSEGNATO→RESO`
    `manuale:false`, `SPEDITO→RESO` `attivo:false`, nuova `RESO→CONSEGNATO`
    `manuale:false` (§5.3). Nuovo file 20_code/data secondo dove vive il loader
    (append CSV se runOnChange).

**Fase C — dati (`80_data`, append CSV su loader runOnChange)**
26. Seed `config.tipi_reso` (§1).
27. Seed `config.stati_doc_reso` (§2.1).
28. Seed `config.transizioni_stati_reso` (matrice reso).
29. Seed riga `config.sistema_codici` `'reso'` (`usa_sequenza=false`) + opt-out
    `automation_lock_columns` per `resi.numero` (§2.2).
30. Append `messaggi_errore` (nuovi codici): `E_STATO_RESO_TRANSIZIONE_NON_VALIDA`,
    `E_RESO_QTA_SUPERA_CONSEGNATO`, `E_RESO_RICONSEGNA_SUPERA_RESO` (guard ponte),
    `E_RESO_NESSUNA_RICONSEGNA_PENDENTE`, codice emittente-BA incoerente reso — solo
    **append** al CSV, nessun nuovo loader ([[feedback_messaggi_errore_no_new_loader]]).
31. Seed `ui.lista_definizione` + colonne per `vendite.resi` (mirror lista DDT, con
    `priorita` responsive) — opzionale/companion se serve la lista FE subito.

**pgTAP** (`db/pgtap/vendite/`): come §6. Grep dei test DDT esistenti prima di agganciare
i trigger `_a10_` sul DDT modificato (matrice).

## 8. Fuori perimetro (esplicito)

- Generazione nota di credito (slice successiva; qui solo la vista-coda).
- Movimenti di magazzino (analisi-ddt §1.2: vivono su `magazzino`).
- Sorgente FATTURA (vocabolario predisposto, abilitazione futura).
- Stampa PDF resi (`stati_doc_reso` senza colonne pdf, read-side senza blocco pdf).
- BE/FE: partono a DB pronto con brief dedicato (endpoint CRUD+conferma,
  drawer reso da DDT, colonna/lista resi).
