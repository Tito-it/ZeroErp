# Brief DB — la distinta contabile prende il numero dal registro

> **Cos'è.** La distinta di incasso (`pagamenti.vendite_contabili`) oggi ha un
> `codice` che nasce da un **DEFAULT di colonna** — `VC_<timestamp>_<md5>` — e,
> sulla strada delle sistemazioni, da una **seconda composizione**
> (`SIS_<atto>_<timestamp>`). Non è un numero: è un'etichetta unica. Tid ha
> chiesto (2026-09-15) che entri nella **numerazione standard**, cioè sui
> registri di `vendite.famiglie_documento` / `vendite.registri_fatturazione`:
> prefisso, anno, progressivo, **reset a Capodanno**.
>
> ⭐ **Il meccanismo esiste e non si tocca.** Cinque famiglie ci passano già, e
> il 2026-09-14 (`20260914-07`) è stata aperta la porta a una famiglia **senza
> billing account** — che è esattamente la distinta. Quello che cambia è
> **la distinta**, non il motore: deve dire **di quale emittente è**, perché un
> registro appartiene a un emittente e oggi lei non lo sa.
>
> **Decisioni prese da Tid il 2026-09-15**, in chat, sull'analisi (§2):
> **D1** la sigla dell'emittente sta **dentro** il codice (`DIS-<SIGLA>-<ANNO>-<7 cifre>`,
> come la commessa); **D3** la RLS della distinta passa sulla **colonna
> emittente della riga**, non più sul canale. Le altre quattro (momento,
> colonne, sedi di composizione, righe esistenti) le ho proposte e non hanno
> avuto obiezioni: sono scritte come decise, con la ragione.
>
> **Sede.** Piano DB qui (§4). Per BE (§5) e FE (§6) c'è **solo l'elenco**: il
> piano lo scrivono loro. Il copione di collaudo prende quattro righe (§7).
>
> **Stato:** 📝 **brief scritto il 2026-09-15, in attesa dell'ok di Tid per lo
> sviluppo.** Nessun changeSet scritto. Le misure sono datate (§1, §2.6) e non
> sono la ragione di nessuna scelta.

---

## 0. In una pagina

| | Cosa | Dove |
| --- | --- | --- |
| **D1** ✅ | Il codice è `DIS-<SIGLA>-<ANNO>-<NNNNNNN>` (es. `DIS-ACME-2026-0000001`): **identità a stringa**, `uq_vendite_contabili_codice` resta com'è. La sigla è `emittenti_fiscali.codice`, come nella commessa | §2.1 |
| **D2** | Si numera **alla creazione** (`BEFORE INSERT`), come ordine e commessa; i buchi da bozza annullata sono accettati e dichiarati. L'anno viene da `data_contabile`; `presidia_data_documento = false` | §2.2 |
| **D3** ✅ | La distinta porta **`emittente_soggetto_ruolo_id NOT NULL`** più `registro_id` e `anno`; la policy RLS passa **sulla colonna** (forma di `rls_fatturazione_lotti_ef_whitelist`); il ramo «senza canale = di tutti» sparisce; la chiave di riuso di `fn_get_or_create_vendite_contabile` include l'emittente — chiude la «decisione aperta» del `20260822-20` | §2.3 · §3 |
| **D4** | L'emittente della riga si **risolve in un posto solo** (trigger): dato → dal canale → dall'operatore in sessione → altrimenti **rifiuto parlante**. Se dato **e** canale dissentono: rifiuto | §2.4 |
| **D5** | Il DEFAULT della colonna cade; `fn_conferma_sistemazione` smette di comporre `SIS_…`; un `codice` fornito dall'esterno è **rispettato** (no-op, precedente ordini) e un presidio pretende che nessuna madre viva lo fornisca | §2.5 |
| **D6** | Le 3 righe esistenti restano `VC_…` (pregresso, forma diversa: non collidono). ⚠️ Due su tre sono **bozze vuote senza emittente ricostruibile**: si cancellano (dev) o Tid le assegna — il backfill è **fail-closed** | §2.6 · §4 P-2 |
| **Storico** | La distinta **non ha shadow**: nessuna `storico_scope_policy`, nessuna policy di shadow da spostare | §3.1 |
| **Impatto RLS** | policy testata riscritta; risolutore modo `contabile` legge la colonna (righe e lotti seguono da soli); un guard di scope sostituito; **22 pgTAP** da censire, uno pinna il vecchio predicato per costruzione | §3.2 · §4 P-12 |

---

## 1. Cosa dice il modello, verificato

Letto dalla doc auto-gen e dalla guida
[numerazione-documenti-e-codici](/guide/numerazione-documenti-e-codici), non
dagli YAML.

| Domanda | Risposta del modello | Dove |
| --- | --- | --- |
| Chi numera con reset annuale? | **Solo i registri**: il catalogo dei formati (`config.sistema_codici`) «non sa cosa sia un anno» (§7 della guida, campanello 2). La distinta non è in `sistema_codici`: il suo codice è un DEFAULT inline | guida §2.2, §7 |
| Cosa serve a un documento per numerarsi su un registro? | Una riga in `vendite.famiglie_documento` (dove vive, quale colonna porta il numero, quale la serie, quale il cliente — le ultime due possono essere NULL), **un registro per emittente**, e un trigger che chiama `vendite.fn_assegna_numero_documento` nel **momento** scelto | [famiglie_documento](/dbzero/vendite/manual/famiglie_documento), [fn_assegna_numero_documento](/dbzero/vendite/funzioni/fn_assegna_numero_documento) |
| Un registro può non avere emittente? | **No**: `registri_fatturazione.emittente_soggetto_ruolo_id NOT NULL`, e `fn_get_registro_documento` **solleva** su emittente nullo (`E_VENDITE_CHIAMATA_NON_VALIDA`) e su registro assente (`E_CONFIG_MANCANTE`, fail-closed) | [fn_get_registro_documento](/dbzero/vendite/funzioni/fn_get_registro_documento) |
| La distinta sa di chi è? | **No.** Nessuna colonna emittente. Lo si ricava solo per catena `ente_incasso → soggetto_ruolo_conto_bancario → soggetto_ruolo` (il conto è del soggetto-ruolo dell'emittente, garantito da `ex_src_bancari_conto_incasso_un_solo_soggetto`), e **il canale è facoltativo** | [vendite_contabili](/dbzero/pagamenti/manual/vendite_contabili), `fn_resolve_emittente_fiscale_id` modo `ente_incasso` |
| Quando l'identità è la stringa nuda, cosa deve contenere? | Tutto ciò che discrimina il contatore: **sigla e anno** (§6.4, §8-bis, §8-ter). È il caso della commessa, `CMM-<sigla>-<anno>-<9 cifre>`, e `fn_assegna_numero_documento` lo serve col parametro `p_corpo` | guida §6.4, §8-ter |
| Chi controlla che una famiglia nuova sia ben formata? | Presidi **derivati** dal catalogo: `test-identita-documenti-derivata-v1` (l'identità distingue l'emittente — ramo «indice con `registro_id`» **o** ramo «stringa nuda unica»), `test-registri-per-emittente-v1`, `trgfn_famiglie_documento_guard_riferimenti` (la tabella e le colonne dichiarate esistono). Coprono la sesta famiglia **da soli** | §8-bis della guida |
| Chi crea distinte? | **Tre** INSERT: `fn_get_or_create_vendite_contabile` (manuale dal BE; fondo fattura da `vendite.fn_sync_contabili_fondo_fattura`, sempre con `p_lotto_id`), `fn_crea_distinta_correzione`, `fn_conferma_sistemazione` (INSERT diretto, **con codice proprio**) | doc auto-gen delle tre |
| Ogni creatrice sa l'emittente? | **Sì, tutte**: canale → conto; lotto → `fatturazione_lotti.emittente_soggetto_ruolo_id` (NOT NULL); sistemazione → `fatture.emittente_soggetto_ruolo_id` della fattura d'origine; correzione → la distinta corretta. La sola eccezione è la **manuale senza canale** (es. CASSA) aperta da chi non ha un emittente in sessione (super admin, admin globale) | §2.4 |
| «Una distinta interna raccoglie i fondi di TUTTI gli emittenti»? | È una proprietà della **chiave di riuso**, non di un percorso vivo: il fondo passa per lotto (⇒ per emittente), la sistemazione fa una distinta **per atto**. Il ramo `GENERATA` senza lotto e senza canale **non ha chiamanti** | `fn_get_or_create_vendite_contabile`, `20260822-20` (🔵 decisione aperta) |
| Ha uno storico? | **No**: nessuna `storico.vendite_contabili`, nessun `trgfn_storico_generic`; in `pagamenti` è storicizzata solo `sepa_mandati` | §3.1 |

⭐ **Nessuna delle due richieste contraddice il modello.** Il motore è fatto
per questo; la distinta è l'unico documento numerabile che non dichiara il
proprio emittente, e il modello lo aveva già annotato come decisione aperta.

**Fatti datati** (misurati il 2026-09-15 su dbdev, **non** ragioni):

- `pagamenti.vendite_contabili`: **3 righe** (id 5720, 5730, 5869), tutte
  `MANUALE`, tutte con `ente_incasso_id NULL`, tutte su centro `CASSA`, tutte
  aperte da `tid`, per cui `script.fn_resolve_emittente_for_user` risponde
  NULL. La 5720 ha **una** riga con fattura (emittente ricostruibile); 5730 e
  5869 hanno **zero** righe (§2.6).
- Emittenti: 2 (`PGTAPEF202` sr 72, `EMITEST` sr 159); registri per ciascuna
  delle quattro famiglie non fiscali su entrambi (`DDT-72`, `ORD-72`, `RES-72`,
  `COM-72`, e i `-159`).

---

## 2. Le decisioni

### 2.1 ✅ D1 — La sigla sta dentro il codice: identità a stringa, come la commessa

**Cosa si fa.** Il codice è `<prefisso><sigla>-<anno>-<progressivo>`, cioè
`DIS-ACME-2026-0000001`: prefisso dal registro (`DIS-`, default di famiglia),
sigla = `anagrafiche.emittenti_fiscali.codice` passata come `p_corpo`
(`sigla || '-'`), anno messo dal registro (`anno_nel_numero = true`, che nasce
da solo per una famiglia con `anno_nel_numero_default = true` e politica
`ANNUALE`), **7 cifre** (`lunghezza_default` 7: una distinta al giorno per
emittente non ne consuma centomila in un anno).

`uq_vendite_contabili_codice UNIQUE (codice)` **resta**: l'identità è la
stringa nuda, unica nell'intera tabella, e il presidio
`test-identita-documenti-derivata-v1` (test 2) la riconosce sul ramo (b).

**Perché la sigla, e non `PREFISSO-ANNO-NUMERO` secco.** Con un registro per
emittente, due emittenti producono entrambi `DIS-2026-0000001`. Con l'unicità
sulla sola stringa il secondo INSERT prende un **23505**, il rollback riporta
indietro il contatore, e al tentativo dopo si sbatte di nuovo: è il numeratore
piantato della guida §8-bis. L'alternativa — unicità `(registro_id, codice)` e
la stessa stringa ripetuta fra emittenti — è stata **scartata**: le distinte
sono visibili al super admin tutte insieme, e due `DIS-2026-0000001` nella
stessa lista sono l'ambiguità «nella stringa che una persona legge» di §8-ter.
⭐ La commessa ha già risolto questo problema nello stesso modo, ed è per questo
che `fn_assegna_numero_documento` ha un `p_corpo`.

⚠️ La sigla ha già il vincolo che serve (`chk_emittenti_fiscali_codice_forma`:
maiuscole e cifre, niente trattino), perché la commessa lo pretende.

### 2.2 D2 — Si numera alla creazione

**Cosa si fa.** Un trigger `BEFORE INSERT` assegna `codice`, `registro_id` e
`anno` **insieme** (sono una cosa sola: la chiave del documento), come
[trgfn_ordini_gen_numero](/dbzero/vendite/funzioni/trgfn_ordini_gen_numero).
L'anno lo compone `fn_assegna_numero_documento` dalla **`data_contabile`**
(«l'anno viene dalla data del documento», guida §6.2): una distinta datata
31/12 e registrata il 2/1 è del 2026.

**Perché non alla registrazione.** Il codice è la maniglia con cui l'operatore
lavora la distinta **da subito** — la lista, il drawer, «ridà quella di prima»
del get-or-create — e `codice` è `NOT NULL`. Numerare a `CHIUSA` vorrebbe dire
una bozza senza nome per tutta la sua vita. I **buchi** da bozza annullata sono
la conseguenza dichiarata della scelta, come per l'ordine (guida §4): per una
distinta manuale il get-or-create riusa la testata della giornata, quindi ne
nascono poche.

`presidia_data_documento = false`: la distinta di ieri inserita stamattina,
dopo che ne è già uscita una di oggi, è un caso d'uso normale — è lo stesso
argomento del DDT (§6.3). ⚠️ Non è una scelta da fare «per sicurezza» al
contrario: con `true` il cancello di sequenza rifiuterebbe proprio quel caso.

### 2.3 ✅ D3 — La distinta porta il suo emittente, e la RLS passa di lì

**Cosa si fa.** Tre colonne su `pagamenti.vendite_contabili`:

| Colonna | Tipo | Nullable | Ruolo |
| --- | --- | --- | --- |
| `emittente_soggetto_ruolo_id` | bigint, FK `anagrafiche.soggetti_ruoli` | **NO** | l'**input**: di chi è la distinta. SR e non PK, come `fatturazione_lotti` e `fatture`, che sono i vicini di pipeline, e come vuole il registro |
| `registro_id` | bigint, FK `vendite.registri_fatturazione` | sì | l'**output** del trigger; NULL sul pregresso (§2.6), come sulle sorelle |
| `anno` | smallint | sì | l'asse del contatore, interrogabile (come `commesse.anno`, `20260902-07`) |

La policy `rls_vendite_contabili_perimetro_incasso` viene **riscritta** sulla
colonna, nella forma di `rls_fatturazione_lotti_ef_whitelist`
(`FOR ALL`, `USING` = `WITH CHECK` = gate `OPERATORE` +
`script.fn_scope_ef_whitelist_via_sr(user, emittente_soggetto_ruolo_id)`). Il
ramo «`ente_incasso_id IS NULL` ⇒ visibile a tutti» **sparisce**: una distinta
interna è del suo emittente, come il lotto da cui nasce.

La chiave di riuso di `fn_get_or_create_vendite_contabile` include
l'emittente su **tutte** le origini. Sulla manuale e sul fondo non cambia
niente in pratica (operatore ⇒ emittente; lotto ⇒ emittente); sulla
`GENERATA` senza lotto — che nessuno chiama — smette di raccogliere di tutti.
⭐ È la «decisione aperta» annotata nel changeSet `20260822-20`, chiusa nel
verso «una per emittente», **a costo zero** perché nessun percorso vivo la
esercitava nell'altro verso.

**Perché la colonna, e non la sola `registro_id`.** `registro_id` implica
l'emittente, ma è un output: il trigger deve **ricevere** l'emittente per
risolvere il registro, e un `BEFORE INSERT` riceve solo colonne. Le quattro
sorelle portano entrambe (`emittente_*` + `registro_id`) per la stessa ragione.

### 2.4 D4 — L'emittente si risolve in una sede sola, e la riserva è di chi agisce

**Cosa si fa.** Un trigger `BEFORE INSERT OR UPDATE OF ente_incasso_id,
emittente_soggetto_ruolo_id` — `pagamenti.trgfn_vendite_contabili_emittente()`
— con **un** ordine di risoluzione:

1. `NEW.emittente_soggetto_ruolo_id` valorizzato → si tiene; **se c'è anche il
   canale**, deve essere il suo (`ente → soggetto_ruolo_conto_bancario →
   soggetto_ruolo`), altrimenti `E_CONTABILE_CANALE_DI_ALTRO_EMITTENTE`
   (`DATO_ERRATO`, campo `ente_incasso_id`);
2. altrimenti dal **canale**, se c'è (derivazione completa: la catena è tutta
   `NOT NULL` e il conto ha un solo padrone);
3. altrimenti dall'**operatore in sessione**:
   `script.fn_resolve_emittente_for_user(GUC app.current_user_id)` → PK →
   SR. È la riserva di D13 (`brief-db-ba-riserva-emittente-operatore-d13`,
   chiuso il 13-09): «la riserva è di chi agisce»;
4. altrimenti **rifiuto**: `E_CONTABILE_EMITTENTE_OBBLIGATORIO` (`DATO_ERRATO`,
   campo `emittente_fiscale_id`) — è il super admin / admin globale che apre
   una manuale su CASSA: deve **scegliere** l'emittente nel form (§6).

⛔ **Nessun quarto livello «il default dell'installazione»**: dichiarare di un
emittente a caso il denaro di un altro è esattamente l'attribuzione che la
numerazione per emittente esiste per impedire (guida §6.1). Il rifiuto è
parlante e arriva al campo giusto.

**Perché nel trigger e non nelle tre madri.** Tre INSERT, una regola: scritta
nelle madri sarebbero tre copie, e la quarta madre di domani la
dimenticherebbe. Le madri passano ciò che **sanno in più** del trigger (il
lotto, la fattura, la distinta corretta); il trigger sa il resto.

⚠️ **Ordine dei `BEFORE ROW`**, che è alfabetico sul nome del trigger:
`a10_emittente_ins_upd` (**e**) → `a10_gen_codice_ins` (**ge**) →
`a10_guard_emittente_scope_ins_upd` (**gu**) → `guard_ente_centro` →
`guard_transizione` → `guard_validazione`. L'emittente è risolto **prima** che
il numeratore lo chieda e **prima** che lo scope lo verifichi. Va scritto nel
COMMENT di entrambi i trigger nuovi, perché regge sul nome.

**Il guard di scope.** `script.trgfn_guard_emittente_scope('soggetto_ruolo',
'emittente_soggetto_ruolo_id')` **sostituisce** quello in modo `ente_incasso`
(`trg_vendite_contabili_a10_guard_emittente_scope_ins_upd`, stesso nome di
trigger: si `DROP` e si ricrea in modo SR). Con la coerenza canale↔emittente
del punto 1 e l'emittente in perimetro, il canale è in perimetro per
costruzione: due guard sulla stessa domanda sarebbero due frasi per lo stesso
rifiuto.

### 2.5 D5 — Una sede sola compone il codice

**Cosa si fa.**

- `ALTER COLUMN codice DROP DEFAULT`: il DEFAULT era la sede del `VC_…`, e con
  un trigger che numera un DEFAULT valorizzato renderebbe il trigger muto
  (`NEW.codice` arriverebbe già pieno).
- `fn_conferma_sistemazione` **non scrive più `codice`** nell'INSERT: l'id
  dell'atto è già in `meta.sistemazione_id`, e «il codice della distinta porta
  l'id dell'atto» (COMMENT del 22-08) era una seconda composizione.
- Il trigger numera **quando `NEW.codice IS NULL`**; un codice fornito è
  rispettato (no-op), come `trgfn_ordini_gen_numero`. ⚠️ Non è una porta per le
  madri: è per le **fixture**, che in **sette** pgTAP inseriscono distinte con
  un codice proprio (`PGTAP_…`) e non devono diventare rosse per un
  cambio di forma. Il presidio è un test che legge `pg_proc` e pretende che
  **nessuna funzione viva** faccia `INSERT INTO pagamenti.vendite_contabili`
  con `codice` fra le colonne — perimetro = l'elenco delle tre madri, come i
  presidi sul testo.

### 2.6 D6 — Il pregresso resta, e il backfill è fail-closed

Le tre righe esistenti tengono il loro `VC_…`: forma diversa, `registro_id` e
`anno` NULL, come i documenti numerati prima del trasloco (guida §6.6). Non
collidono con i nuovi **perché la forma è diversa**.

⚠️ Ma `emittente_soggetto_ruolo_id` è `NOT NULL`, e va riempito. Il backfill
prova, nell'ordine: canale → lotto (`vendite_contabili_lotti`) → fattura delle
righe (`vendite_contabili_righe.fattura_id → fatture.emittente_soggetto_ruolo_id`,
se **una** sola) → e poi **si ferma**: un `sqlCheck` a `0` righe residue in
`preConditions` del changeSet che alza il `NOT NULL`. Sul modello una riga senza
emittente ricostruibile non è un dato da inventare.

**Misurato il 15-09**: 5720 risolve dalla riga (emittente della fattura);
**5730 e 5869 no** — bozze `MANUALE` vuote, aperte da un super admin senza
emittente. 📮 **Decisione a Tid prima dell'apply**: cancellarle (sono vuote, e
non siamo in produzione) o assegnarle a mano. Il changeSet non decide.

---

## 3. Storico e impatto della RLS sulla riga

### 3.1 Storico: non c'è

`pagamenti.vendite_contabili`, `_righe`, `_lotti`, `enti_incasso`,
`centri_riscossione` **non hanno shadow** in `storico`; in `pagamenti` è
storicizzata solo `sepa_mandati`. Quindi: nessuna riga in
`dbops/storico_scope_policy.csv` (il presidio segnala le tabelle **con** shadow
che entrano in RLS — qui la RLS c'è già e la shadow no), nessuna policy di
shadow da spostare. `vendite.registri_fatturazione` è storicizzata, ma il
provisioning del registro `DISTINTA` è un INSERT e lo storico scrive su
UPDATE/DELETE: nessuna versione.

### 3.2 Chi cambia con D3, in ordine di lettura

| Oggetto | Cosa cambia | Perché |
| --- | --- | --- |
| `rls_vendite_contabili_perimetro_incasso` | riscritta sulla colonna (§2.3) | il ramo «senza canale = di tutti» non descrive più il modello |
| `script.fn_resolve_emittente_fiscale_id`, modo `contabile` | legge `c.emittente_soggetto_ruolo_id` invece della catena per canale; **non risponde più NULL** sulle interne | una lettura invece di tre JOIN; la riga sa di chi è |
| `script.fn_scope_ef_whitelist_via_contabile` | **nessuna modifica di codice**: delega al risolutore. Cambia il COMMENT («su una distinta interna risponde FALSE, apposta» diventa falso) | il predicato è lo stesso; la frase no |
| policy delle **righe** (`20260822-21`) e dei **lotti** (`20260910-18`) | **nessuna modifica**: la strada 1 (`via_contabile`) ora copre anche le righe di una distinta interna, in perimetro | seguono da sole; i loro commenti nei changeSet sono immutabili, la correzione va nel manual |
| `trgfn_guard_emittente_scope` in modo `ente_incasso` | **DROP** del trigger; ricreato in modo `soggetto_ruolo` (§2.4) | una domanda, un guard |
| `trgfn_vendite_contabili_guard_ente_centro` | invariato | la coerenza centro↔canale è un'altra domanda |
| `zeroerp_batch_fatturazione` | invariato (`BYPASSRLS`) | il giro dei fondi non passa dalla policy |
| super admin | invariato | bypass |
| BE delle distinte | nessun filtro applicativo da cambiare («la RLS dello schema»); il commento in `list_distinte` («le policy passano dal canale e dalla fattura, non da una colonna emittente») diventa falso | §5 |

### 3.3 Cosa si vede diversamente, ed è voluto

- una distinta **senza canale** aperta da un operatore di A **non è più visibile**
  agli operatori di B (oggi lo è: `test-rls-pagamenti-perimetro` test 7 e 10);
- le **righe** di una distinta interna di A sono visibili agli operatori di A
  anche senza passare dalla fattura (oggi: solo via fattura, test 8);
- `INSERT … RETURNING` di `fn_get_or_create_vendite_contabile` passa dalla
  `USING`: la riga appena creata è dell'emittente in sessione o del canale in
  perimetro, quindi **visibile a chi l'ha scritta** — la regola del 22-08 resta
  vera per costruzione (il guard di scope la fa rispettare prima del RETURNING).

---

## 4. Piano DB

Regole di lavorazione: corpo di ogni oggetto esistente **dalla doc auto-gen**;
un changeSet per file, `runOnChange: false` in `00_schema`/`20_code`;
codici errore **in coda al CSV** con la loro classe; numerazione `NN`
assegnata **al momento della scrittura**; `SECURITY INVOKER`/`DEFINER`
espliciti; la prova è **l'SQL estratto** in `BEGIN … ROLLBACK`, poi i pgTAP
nella stessa transazione; ⛔ l'apply e il lancio col runner sono di Tid.
⚠️ Le preCondition di `00_schema`/`20_code` non interrogano `80_data` (§11.4
delle linee guida): la famiglia `DISTINTA` e i registri si nominano come
**stringhe** e si risolvono a runtime.

| Passo | Cosa | Fase | Note |
| --- | --- | --- | --- |
| **P-1** | `pagamenti.vendite_contabili`: `ADD COLUMN emittente_soggetto_ruolo_id bigint` (**nullable in questo passo**), `registro_id bigint`, `anno smallint`; FK `fk_vendite_contabili_emittente_sr → anagrafiche.soggetti_ruoli(id)`, `fk_vendite_contabili_registro → vendite.registri_fatturazione(id)`; indice `ix_vendite_contabili_registro_anno (registro_id, anno)` (copre la FK, come `ix_commesse_registro_anno`); indice `ix_vendite_contabili_emittente_sr (emittente_soggetto_ruolo_id)` — è la colonna su cui la policy filtra ogni lettura. `ALTER COLUMN codice DROP DEFAULT`. ⚠️ Le automazioni `ci_apply` genereranno da sole il `require_attivo` sul registro e il `block_deact` su `registri_fatturazione` per questa FK (memoria: FK nuova = guard che oscura — il nome `trg_vendite_contabili_a10_registri_fatturazione_require_att_…` sarà **hashato** a 63 caratteri) | `00_schema/pagamenti` | il `NOT NULL` è in P-2, dopo il backfill |
| **P-2** | Backfill di `emittente_soggetto_ruolo_id` sul pregresso, nell'ordine di §2.6 (canale → lotto → fattura delle righe, solo se **una**), poi `SET NOT NULL` con `preConditions: sqlCheck expectedResult 0` su `emittente_soggetto_ruolo_id IS NULL`. ⛔ **`onFail: HALT`**, non `MARK_RAN`: una riga residua deve fermare il migrate e nominarsi, non essere segnata come fatta. 📮 Prima dell'apply Tid decide su 5730 e 5869 (§2.6). ⚠️ Su un DB ricostruito da zero l'`UPDATE` è su zero righe: innocuo, nessun `dati_macchina` | `00_schema/pagamenti` | changeSet separato da P-1: il backfill legge le colonne che P-1 crea |
| **P-3** | Seed della famiglia: riga `6,DISTINTA,Distinta contabile di incasso,pagamenti,vendite_contabili,codice,,true,false,{},…` in `80_data/sql/vendite/famiglie_documento.csv` (`colonna_billing_account` **vuota** = NULL con `nullValue: ""` di quel mirror) **e** una riga in ciascuno dei tre CSV laterali: `famiglie_documento_formato.csv` (`DISTINTA,DIS-,7`), `famiglie_documento_colonna_serie.csv` (`DISTINTA,NULL`), `famiglie_documento_anno_nel_numero.csv` (`DISTINTA,t`). Non in `_regole_fiscali.csv` (default `false`). ⚠️ I mirror sono **quattro** e tutti `runOnChange` + `ANY`; le loro preCondition contano le cinque famiglie **per nome** (`IN (…)`, `expectedResult 5`) e restano verdi con la sesta. ⚠️ Provare con l'upsert di **tutte** le righe in transazione annullata: `20260914-07` ha reso nullable `colonna_billing_account` ma il mirror base risale al 30-08 — è la specie di mina «CSV stantìo, mirror dormiente» | `80_data` | `left('DISTINTA',3) = 'DIS'` ⇒ i registri si chiameranno `DIS-<sr>`; nessuna collisione con `DDT-/ORD-/RES-/COM-` (`uq_registri_fatturazione_codice`) né su `(emittente, prefisso)` (`DIS-` ≠ `CMM-`) |
| **P-4** | Registri per gli emittenti esistenti: changeSet `80_data` `runOnChange` che chiama `vendite.fn_provision_registri_famiglia('DISTINTA')` (idempotente: `WHERE NOT EXISTS`); dopo il seed P-3 nell'ordine di timeline. Gli emittenti **futuri** li prendono da `anagrafiche.trgfn_emittenti_fiscali_provision_registri`. ⭐ `trgfn_registri_fatturazione_set_anno_nel_numero` mette `anno_nel_numero = true` all'INSERT (famiglia `true` + politica `ANNUALE`): niente da scrivere. ⚠️ Non è un CSV, per la stessa ragione del `20260831-03`: dipende da quali emittenti esistono su **questa** macchina | `80_data` | `test-registri-per-emittente-v1` lo pretende |
| **P-5** | `pagamenti.trgfn_vendite_contabili_emittente()` + trigger `trg_vendite_contabili_a10_emittente_ins_upd` (`BEFORE INSERT OR UPDATE OF ente_incasso_id, emittente_soggetto_ruolo_id`): i quattro livelli di §2.4 e la coerenza canale↔emittente. `SECURITY INVOKER`; la lettura del canale **non** passa da tabelle con RLS (`enti_incasso` ha una policy: letta da INVOKER sotto un operatore fuori perimetro darebbe NULL → «canale sconosciuto»; si legge via `script.fn_resolve_emittente_fiscale_id('ente_incasso', …)`, che è DEFINER e risponde la PK, poi PK → SR su `emittenti_fiscali`, che non ha RLS). ⚠️ Sull'UPDATE: cambiare canale su una distinta che ha già l'emittente verso un canale di un altro → rifiuto (livello 1); cambiare l'emittente di una riga esistente non è previsto da nessun verbo e resta possibile da SQL — dichiarato in §8, non presidiato | `20_code/pagamenti` | 2 codici nuovi (P-8) |
| **P-6** | `pagamenti.trgfn_vendite_contabili_gen_codice()` + trigger `trg_vendite_contabili_a10_gen_codice_ins` (`BEFORE INSERT`): se `NEW.codice IS NOT NULL` → no-op; altrimenti sigla da `emittenti_fiscali.codice` per `soggetto_ruolo_id = NEW.emittente_soggetto_ruolo_id`, poi `vendite.fn_assegna_numero_documento(p_famiglia_documento => 'DISTINTA', p_emittente_soggetto_ruolo_id => NEW.emittente_soggetto_ruolo_id, p_data => NEW.data_contabile, p_documento_id => NEW.id, p_utility_id => NULL, p_corpo => sigla \|\| '-', p_serie => NULL)`, e **insieme** `NEW.registro_id`, `NEW.anno`, `NEW.codice`. Modello: `trgfn_ordini_gen_numero` (ordini) per il momento, `fn_get_or_create_commessa` per il corpo. ⚠️ `NEW.id` è già valorizzato in un `BEFORE INSERT` (default della sequenza): è così per gli ordini. ⚠️ Emittente senza registro → `E_CONFIG_MANCANTE` da `fn_get_registro_documento`: fail-closed, giusto, e P-4 lo rende irraggiungibile sugli emittenti esistenti | `20_code/pagamenti` | nessun codice nuovo |
| **P-7** | Le tre madri, corpo dalla doc auto-gen: (a) `fn_get_or_create_vendite_contabile` — parametro **in coda** `p_emittente_fiscale_id bigint DEFAULT NULL` (**PK**, ciò che BE e FE conoscono; la traduzione PK → SR è esplicita nel corpo, come in `trgfn_ordini_gen_numero`), derivazione dal lotto se `p_lotto_id` (`fatturazione_lotti.emittente_soggetto_ruolo_id`), emittente **nella chiave di riuso** di entrambi i rami, e nell'INSERT; se resta NULL si lascia al trigger (canale / sessione / rifiuto). ⛔ Parametro in più = overload: `DROP` prima del `CREATE`, e la chiamata del BE è **nominata** (`p_… :=`), quindi non cambia se non lo passa; `fn_sync_contabili_fondo_fattura` **non cambia** (passa il lotto, e basta). (b) `fn_conferma_sistemazione` — via `codice` dall'INSERT (D5), `emittente_soggetto_ruolo_id => v_fattura.emittente_soggetto_ruolo_id` (già carica `v_fattura`); il COMMENT smette di dire «il codice porta l'id dell'atto». (c) `fn_crea_distinta_correzione` — copia `emittente_soggetto_ruolo_id` dalla distinta corretta: stesso emittente, stesso registro, e il codice della correzione è il **prossimo** del sezionale (`meta.correzione_di` continua a portare il codice dell'originale) | `20_code/pagamenti` | tre changeSet, uno per funzione |
| **P-8** | Seed codici: `E_CONTABILE_EMITTENTE_OBBLIGATORIO` e `E_CONTABILE_CANALE_DI_ALTRO_EMITTENTE`, classe `DATO_ERRATO`, note col nome del trigger; due righe `it` in `messaggi_errore.csv` con `causa` e `soluzione` («scegliere l'emittente per cui si apre la distinta» / «scegliere un canale dell'emittente indicato, o cambiare emittente»). ⚠️ Apostrofo singolo nel CSV; prova con l'upsert di **tutte** le righe. ⚠️ Entrambi `IGNOTO` per il rubinetto degli accumulatori (sollevati con `fn_log_and_raise_error` diretta su `IF` composti): la baseline B-7 non si muove | `80_data/config` | il BE rigenera `error_policies_generated.py` e scrive i due ripieghi (§5) |
| **P-9** | La RLS (D3), in **un** changeSet `00_schema` con `DROP POLICY` + `CREATE POLICY` sulla colonna, `FOR ALL`, forma di `20260603-24`; nello stesso file `DROP TRIGGER trg_vendite_contabili_a10_guard_emittente_scope_ins_upd` e ricreazione in modo `soggetto_ruolo`. ⚠️ **Dopo P-2** (la colonna deve essere `NOT NULL` prima che una policy la legga: una riga con NULL sparirebbe a tutti). Un `20_code` gemello riscrive il modo `contabile` di `script.fn_resolve_emittente_fiscale_id` (corpo dalla doc auto-gen, gli altri modi **intatti**) e il COMMENT di `fn_scope_ef_whitelist_via_contabile` e di `trgfn_guard_emittente_scope` (la frase «una distinta interna non è il canale di nessuno» resta vera per il ramo, falsa per la distinta: si riscrive) | `00_schema` + `20_code` | ⛔ `security_invoker`/DEFINER invariati: il risolutore resta DEFINER, la policy lo chiama |
| **P-10** | `dbops.fk_index_policy`: due righe in un CSV laterale `80_data/sql/pagamenti/fk_index_policy_vendite_contabili_numerazione.csv` (forma di `vendite/fk_index_policy_documenti_registro.csv`): `fk_vendite_contabili_registro` → `consentito=false` («coperta da `ix_vendite_contabili_registro_anno`»), `fk_vendite_contabili_emittente_sr` → `consentito=false` («indice creato in P-1»), `dll_command` **sempre valorizzato** | `80_data` | altrimenti `vw_fk_con_indice_missing_policy` le mette in coda |
| **P-11** | pgTAP nuovo `db/pgtap/pagamenti/test-distinta-numerazione-registro-v1.sql` (runner **app**, contesto operatore; fixture **costruita** con `fn_pgtap_crea_emittente_operatore` per il **secondo** emittente — ⚠️ il primo creato è il default, memoria «due aziende»): (1) la famiglia `DISTINTA` è a catalogo con `pagamenti.vendite_contabili`/`codice`, serie NULL, BA NULL, `DIS-`/7/anno; (2) ogni emittente attivo ha un registro `DISTINTA` con `anno_nel_numero`; (3) manuale con canale → `codice ~ '^DIS-<sigla>-2026-\d{7}$'`, `registro_id`/`anno` scritti insieme; (4) la seconda è `+1`; (5) l'altro emittente parte da `0000001` senza collisione; (6) `data_contabile` 31/12 vs 2/1 → anni diversi e il secchio nuovo riparte da 1; (7) senza canale, con operatore in sessione → l'emittente è il suo; (8) senza canale e senza emittente in sessione → `E_CONTABILE_EMITTENTE_OBBLIGATORIO` (`throws_like` sulla frase); (9) emittente A + canale di B → `E_CONTABILE_CANALE_DI_ALTRO_EMITTENTE`; (10) `codice` fornito → rispettato; (11) la correzione nasce sullo stesso registro col progressivo successivo; (12) la sistemazione non porta più `SIS_`; (13) **presidio della sede unica**: nessuna funzione in `pg_proc` fa `INSERT INTO pagamenti.vendite_contabili` con `codice` fra le colonne (perimetro: le tre madri, per nome); (14) `fn_componi_numero_documento` sui valori della distinta, in una riga (la composizione si prova sui **valori**) | pgTAP | `throws_like` dove la frase è la posta |
| **P-12** | 🔴 **Censimento dei 22 pgTAP** che nominano `vendite_contabili`, `fn_get_or_create_vendite_contabile`, `fn_conferma_sistemazione` o `fn_sync_contabili_fondo_fattura` (elenco in §7). Attesi: **nessun cambio** per i 9 che inseriscono direttamente sotto contesto operatore (il livello 3 di §2.4 dà l'emittente della sessione; 7 passano un `codice` proprio e restano no-op); `rls/test-rls-pagamenti-perimetro.sql` **rosso per costruzione** sui test 7, 8 e 10 (pinnano il predicato vecchio): si riscrivono nel verso di §3.3, non si tolgono; `rls/test-role-batch-fatturazione-postura.sql` senza contesto: verificare che il ruolo batch passi da `row_security_active() = false` nel guard. ⛔ Regressione = **asserzioni**, non file rossi; la baseline non si aggiorna per far passare | pgTAP | `scripts/pgtap-baseline.sh pagamenti rls vendite` |
| **P-13** | Doc manuale: `pagamenti/manual/vendite_contabili.md` (sezione nuova «Il codice viene dal registro, e la distinta sa di chi è»: le tre colonne, i quattro livelli, il pregresso `VC_`, la RLS sulla riga — **corregge** la sezione «Chi la vede» del 22-08 senza cancellarla, con la data); `vendite/manual/famiglie_documento.md` (la sesta famiglia, **la prima fuori da `vendite`** e la prima senza billing account in servizio — la rev 2026-09-14 diceva «sarà il cantiere acquisti»: è stata la distinta); guida [numerazione-documenti-e-codici](/guide/numerazione-documenti-e-codici) §2.2 «chi lo usa», §4 tabella (sesta riga: `DISTINTA` · registro · registro · alla creazione; «tre modi di scrivere l'identità»: la distinta è come la commessa), §6.4 (la sigla dentro il codice vale per due documenti); `script/manual/fn_resolve_emittente_fiscale_id.md`, `fn_scope_ef_whitelist_via_contabile.md`; `guide/gestione-dei-pagamenti.md` §distinte (una riga: come nasce il codice). ⛔ La doc auto-gen non si edita | docs | rimando al meccanismo (la guida), non copia |

**Cosa il DB NON fa, e perché**

| | |
| --- | --- |
| Nessuna rinumerazione delle 3 righe | guida §6.6: i numeri già assegnati non si rifanno; la forma diversa li tiene separati |
| Nessun lock su `codice`/`emittente`/`registro_id` | nessuna delle cinque sorelle numerate sul registro lo ha via `automation_lock_columns` (le righe DDT/resi sono **disabilitate**); un lock qui sarebbe la prima eccezione, e va deciso per tutte e sei insieme. Dichiarato in §8 |
| Nessuna modifica a `fn_sync_contabili_fondo_fattura` | passa già `p_lotto_id`: l'emittente lo deriva la madre (P-7a) |
| Nessuna modifica alle policy di righe e lotti | seguono il risolutore (§3.2) |
| Nessuna colonna `anno` nella lista 50 | il codice la porta dentro; se servirà un filtro per anno è una riga di `ui.lista_colonna`, non DDL |
| Nessun rename di `registri_fatturazione` | debito dichiarato in quattro sedi; non si infila qui |

---

## 5. Cosa deve fare il backend *(solo l'elenco: il piano è loro)*

| | Cosa | Perché |
| --- | --- | --- |
| **BE-1** | `crea_distinta`: `emittente_fiscale_id` **opzionale** nel payload (whitelist + `optional_positive_int`), passato a `get_or_create_distinta` → `p_emittente_fiscale_id`. ⛔ Il BE **non risolve** l'emittente dal profilo: lo fa il DB (livello 3), e un secondo risolutore sarebbe una seconda sede. Il 400 con `fields: ["emittente_fiscale_id"]` arriva dal trigger | il campo si accende da solo (`campiErrati`) |
| **BE-2** | `_DISTINTA_SELECT` + `DistintaRow`: `emittente_soggetto_ruolo_id`, `emittente_codice` (sigla, `JOIN emittenti_fiscali ef ON ef.soggetto_ruolo_id`), `registro_id`, `anno` | il drawer dice di chi è; la lista può filtrare |
| **BE-3** | `./manage-env.sh genera_error_policies` (due codici) + ripieghi in `error_messages_fallback.py`; `test_ogni_codice_vivo_ha_un_messaggio_di_ripiego` | cancello CI |
| **BE-4** | Il commento di `PagamentiRepository.list_distinte` («le policy passano dal canale e dalla fattura, non da una colonna emittente») diventa falso: si riscrive | un commento che dice il falso è peggio di nessuno |
| **BE-5** | Test: `crea_distinta` con e senza `emittente_fiscale_id`; `api_pagamenti.md` (campo nuovo, il codice `DIS-…`, i due errori) | |
| **BE-6** | ⚠️ Verificare che la lista/CRUD delle **famiglie** (`api_famiglie_documento`, drawer FE) non cabli `schema_tabella = 'vendite'`: la sesta famiglia vive in `pagamenti` | la prima famiglia fuori da `vendite` |

---

## 6. Cosa deve fare il frontend *(solo l'elenco)*

| | Cosa | Perché |
| --- | --- | --- |
| **FE-1** | `ApriDistintaDialog`: `EmittenteFiscaleField` (create: operatore → testo dal profilo; admin globale → Select), **visibile solo senza canale** — col canale scelto l'emittente è il suo, e il campo si nasconde con la frase che lo dice. Il payload porta `emittente_fiscale_id` solo se il campo è a video. `:invalid="campiErrati.includes('emittente_fiscale_id')"` | §2.4 livello 4: chi non ha un emittente in sessione deve sceglierlo |
| **FE-2** | `DistintaDrawer` header: la **sigla** accanto al codice (`emittente_codice`), come i documenti | di chi è, a colpo d'occhio |
| **FE-3** | i18n `it`/`en` per la frase del campo e per l'help; `check_i18n_keys.py` verde | |
| **FE-4** | Nessun parsing del codice, da nessuna parte (verificato: oggi non c'è) | resta così |

---

## 7. Il copione di collaudo — righe da aggiungere

In [collaudo-in-app-incassi-distinte-e-sistemazioni.md](collaudo-in-app-incassi-distinte-e-sistemazioni.md),
§2 (e una in §1):

| | Cosa fare | Cosa deve succedere | Se non succede |
| --- | --- | --- | --- |
| **2.4-bis** | Guarda il codice della distinta appena aperta | `DIS-<sigla del tuo emittente>-2026-0000001`; la seconda della giornata (altro canale) finisce in `…0000002` | Un `VC_…` dice che il trigger non è montato; un codice senza sigla dice che il registro non ha la forma |
| **2.4-ter** | Togli il canale e apri su CASSA come **operatore** | Il campo emittente compare **già compilato** col tuo, non modificabile | Se resta vuoto e Salva passa, il livello 3 non ha risolto |
| **2.4-quater** | Stessa cosa come **super admin** | Il campo emittente è una **tendina** e Salva è spento finché non scegli | Se passa senza scegliere, il rifiuto D4-4 non è arrivato |
| **1.6-bis** | Come operatore dell'altro emittente, apri Distinte | ⛔ Non vedi la distinta su CASSA del primo (oggi la vedi: era «di tutti») | È la prova di D3 |

**Censimento pgTAP per P-12** (misurato il 2026-09-15, 22 file):
`pagamenti/`: `test-abbinamento-rata`, `test-centri-riscossione-vincoli-ruolo`,
`test-contabili-origine-e-quadratura`, `test-fn-crea-distinta-correzione`,
`test-fn-get-or-create-vendite-contabile`, `test-fn-get-saldo-fattura-tre-numeri`,
`test-fn-posta-contabile`, `test-righe-contabili-eliminazione-v1`,
`test-righe-contabili-guard-dati`, `test-sistemazione-annullo-riporto`,
`test-sistemazioni-giro-completo`, `test-sistemazioni-registro`,
`test-transizioni-stati-contabili`, `test-vendite-contabili-stato-obbligatorio`,
`test-vendite-movimenti-contabile-riga`; `vendite/`: `test-fondi-fattura`,
`test-fondi-fattura-governo`, `test-fondo-fattura-eseguito`; `rls/`:
`test-rls-pagamenti-perimetro` (🔴 pinna il predicato vecchio),
`test-rls-vendite-contabili-lotti`, `test-rls-fondi-fattura-source-functional`,
`test-role-batch-fatturazione-postura` (senza contesto).

---

## 8. Trappole da non ripagare, viste scrivendo

- ⛔ **Il DEFAULT rende muto il trigger.** Con il DEFAULT ancora sulla colonna
  `NEW.codice` arriva pieno e il trigger no-op non numera nulla: nessun errore,
  distinte `VC_…` per sempre. Il `DROP DEFAULT` sta in P-1 e il test 3 di P-11
  lo pinna.
- ⛔ **L'ordine dei `BEFORE ROW` regge sul nome.** `emittente` < `gen_codice` <
  `guard_emittente_scope`: chi rinomina uno dei tre sposta la risoluzione
  dopo il numeratore. Scritto nei COMMENT (memoria: due guard `BEFORE ROW`,
  ordine alfabetico).
- ⚠️ **Il primo emittente creato è il default** (memoria «due aziende»): la
  fixture di P-11 deve creare il **secondo** e lavorare da lì, o i test 5 e 9
  passano per coincidenza.
- ⚠️ **`INSERT … RETURNING` passa dalla `USING`.** La policy nuova legge la
  colonna che il trigger ha appena risolto: un emittente fuori perimetro viene
  fermato dal guard di scope **prima** del RETURNING, con un messaggio; senza
  il guard il rifiuto sarebbe il «new row violates row-level security policy»
  che il 22-08 aveva già respinto.
- ⚠️ **Una colonna nuova di riga = censire le copie** (memoria). Le copie
  esplicite della testata sono la **correzione** (P-7c) e nient'altro: la
  revisione non esiste per le distinte.
- ⚠️ **I quattro mirror delle famiglie** sono tutti `runOnChange` e
  ri-eseguono: la sesta riga va in **tutti** i CSV laterali, o la famiglia
  nasce con `lunghezza_default` 7 e `anno_nel_numero_default` **false** —
  cioè `DIS-ACME-0000001` senza anno, e l'anno nel numero **non si aggiunge**
  a un registro che ha già numerato (guida §8-ter).
- ⚠️ **`E_CONFIG_MANCANTE` sull'emittente senza registro** è giusto e
  fail-closed, ma su un DB nuovo l'ordine è: `00_schema` + `20_code`, poi
  `80_data` (famiglia, poi registri). Nessuna distinta nasce durante il migrate,
  quindi la finestra è vuota; i pgTAP girano dopo.
- Dichiarati, non fatti: (a) l'emittente di una riga resta **modificabile da
  SQL** dopo la nascita (nessun lock, come sulle sorelle) — se un giorno si
  decide un lock, vale per le sei famiglie; (b) `E_CONFIG_MANCANTE` è riusato
  da `fn_get_registro_documento` (già a catalogo) e la sua frase nomina la
  famiglia, non «distinta»: accettato, è la stessa frase per DDT e ordini.

---

## 9. Registro

| Data | Cosa |
| --- | --- |
| **2026-09-15** | Analisi in chat su richiesta di Tid («la numerazione del codice distinta deve rientrare nella numerazione standard, prefisso-anno-progressivo con reset anno, le 3 righe numerate restano così»). Verificato: nessuno storico sulla distinta; ogni creatrice conosce l'emittente; il ramo «di tutti» non ha chiamanti. **D1** (sigla) e **D3** (RLS sulla riga) decise da Tid; D2, D4, D5, D6 proposte senza obiezione. Brief scritto; **nessun changeSet**. Aperto a Tid: la sorte di 5730 e 5869 (§2.6) prima dell'apply di P-2 |
