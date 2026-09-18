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
> **Sede.** Piano DB qui (§4, progetto; §4-bis, sviluppo lotto per lotto). Per BE
> (§5) e FE (§6) c'è **solo l'elenco**: il piano lo scrivono loro. Il copione di collaudo prende quattro righe (§7).
>
> **Stato:** ✅ **CHIUSO il 2026-09-17** — riquadro «CHIUSO» qui sotto: DB
> applicato e verde, BE/FE mergiati, e **il primo numero è uscito a video**.
> Le misure sono datate (§1, §2.6) e non sono la ragione di nessuna scelta.
> ⚠️ Il piano ha **corretto** il brief in otto punti, e la scrittura ne ha
> aggiunti cinque (§4-bis.19): due sono mine di CI che l'analisi non aveva
> visto — e la CI ne ha mostrata una terza, sotto la seconda (🔴→✅
> CI-Validate rossa dopo il merge di PR #1598: riquadro sotto, §9). Il BE/FE
> ne ha corretti altri due (§5 BE-2, §6 FE-1), confermati da Tid.

---

> ## ✅ CHIUSO — 2026-09-17 · DB L1 → L17 · BE-1..6 · FE-1..4 · archiviato in `work-done/`
>
> **Lato DB**: changeSet `20260915-21 → -35` `EXECUTED` su dbdev (`-21…-25`
> alle 12:03, stop fail-closed su `-26` con le due residue 5730/5869, `UPDATE`
> a mano → sr 72, `-26…-35` alle 12:06); zero distinte senza emittente;
> registri `DIS-72` e `DIS-159` con l'anno nel numero. pgTAP **verdi come
> app** su dbdev (RLS esercitata) e sullo scratch `zeroerp_ci` da zero — dove
> L11 e `20260831-03` si sono incontrati davvero. Commit `e98cf2469`, PR #1598.
> 🔴→✅ **CI-Validate rossa dopo il merge**: `20260831-03` è morto lo stesso,
> nella **seconda** invocazione di Liquibase (`--contexts=ci_apply`), con
> «Expected '4' got '5'» — un `runOnChange` con un change `dbms:` viene
> ri-eseguito **una volta** all'update successivo alla prima esecuzione
> (Liquibase 5.0.4, letto nel jar). Corretto il cancello (conta le quattro
> famiglie **per nome**) e il corpo (la primitiva, non l'INSERT ricopiato);
> L11 resta com'è. Commit `237ea2939`; meccanismo, prova e perimetro in §9.
>
> **Lato BE/FE**: le sei voci di §5 e le quattro di §6 (commit `45046a6a7`),
> con la rigenerazione delle policy che copre anche il BB gemello
> (`emittente-di-default-un-bb-solo` §11). Provato per intero sul DB vero:
> service → madre → sede unica dell'emittente → trigger → `DIS-<sigla>-<anno>-\d{7}`.
>
> ⭐ **A video, da Tid, il 2026-09-17: `DIS-PGTAPEF202-2026-0000001` — il PRIMO
> numero emesso da un registro `DISTINTA`.** È la riga 2.4-bis del copione
> (§7), e chiude la domanda da cui il brief è nato il 15-09: *«un `VC_…` dice
> che il trigger non è montato; un codice senza sigla dice che il registro non
> ha la forma»* — è arrivato con la sigla, l'anno e sette cifre.
>
> ⚠️ **Che cosa ESCE dal brief, e dove va** — un residuo senza destinazione è
> un residuo che nessuno rilegge:
>
> | Cosa | Dove va |
> | --- | --- |
> | 🔴 `fn_sync_contabili_fondo_fattura` con una fattura **fuori lotto** passa `p_lotto_id = NULL` e la distinta del fondo cade al livello **3** (l'emittente di chi agisce) invece che a quello della fattura: per l'admin globale in «tutti» è un `E_CONTABILE_EMITTENTE_OBBLIGATORIO` in mezzo alla pipeline, in modo «uno» una fattura altrui darebbe una distinta attribuita alla sessione. La strada corretta è che la madre dei fondi passi `p_emittente_fiscale_id` dall'emittente della **fattura** (§4-bis.19, seconda tabella) | `.codex/PROJECT_CONTEXT.md` §«Aperto — Media priorità», cantiere DB |
> | Le tre righe del copione **non ancora provate a video** — 2.4-ter (operatore su CASSA: campo emittente già compilato), 2.4-quater (super admin in «tutti»: avviso e Apri spento), 1.6-bis (l'altro emittente non vede la distinta su CASSA) — la prova a video è l'unica cosa che ne esce | [collaudo-in-app-incassi-distinte-e-sistemazioni.md](../work-in-progress/collaudo-in-app-incassi-distinte-e-sistemazioni.md) §1 e §2, righe già scritte |
> | Una colonna «Emittente» nella lista 50 delle distinte: dato, non DDL (`ui.lista_colonna`), non chiesta | si fa quando serve, dall'amministrazione in-app |
| ⚠️ La **decisione sistemica** sui 28 `runOnChange` di `80_data`/`90_end` con un change `dbms:` — togliere `dbms:` (checksum deterministico, niente ri-esecuzione in `ci_apply`) o accettare la ri-esecuzione e censire i loro cancelli `HALT` sul contenuto — e la nota del guardrail `runOnChange` in `ci-validate.yaml`, che nomina `runOnChange` come causa quando la causa è `runOnChange` **+ `dbms:`** (§9, riga del 17-09 pomeriggio) | `.codex/PROJECT_CONTEXT.md` §«Aperto — Media priorità», cantiere DB (`dbops`) |

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
emittente. ✅ **Deciso da Tid il 2026-09-15**: si **assegnano a mano** a
«Gestore Test pgTAP» (`emittenti_fiscali.id = 32`, `soggetto_ruolo_id = 72`,
il default di questa installazione) — un `UPDATE` per `id`, non un DELETE.
⛔ Il changeSet non lo fa e non lo saprà mai: un «default dell'installazione»
nel backfill sarebbe il quarto livello che §2.4 vieta, e su un DB da zero
quell'emittente non esiste. Come si esegue in pratica: §4-bis.5.

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
| il giro dei fondi (pipeline) | passa dalla policy **nuova** come tutti | ⚠️ corretto il 2026-09-15 (Tid): questa riga diceva «`zeroerp_batch_fatturazione` invariato (`BYPASSRLS`), il giro non passa dalla policy». Il ruolo esiste ancora, ma il gateway che lo usava non c'è più dal 2026-09-05 (R-2, `system_context.py`): ogni processo gira con un **utente tecnico per (processo × azienda)** e i 5 GUC di sessione — dentro il proprio perimetro, RLS attiva. Il livello 3 di §2.4 risolve anche per lui |
| super admin | invariato | bypass |
| BE delle distinte | nessun filtro applicativo da cambiare («la RLS dello schema»); il commento in `list_distinte` («le policy passano dal canale e dalla fattura, non da una colonna emittente») diventa falso | §5 |

⚠️ **Corretto il 2026-09-15 scrivendo il piano** (§4-bis.9-bis): le righe
«policy delle righe e dei lotti: nessuna modifica» citano `20260822-21` e
`20260910-18`, ma le policy **vive** (`pg_policy`) sono `20260822-24` e
`20260910-18` ed entrambe portano un terzo ramo `EXISTS (… c.ente_incasso_id
IS NULL)` — «la testata senza canale è di tutti, il satellite la segue». Dopo
D3 è un ramo morto con un commento falso: si riscrivono senza (L9b).

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
| **P-12** | 🔴 **Censimento dei 22 pgTAP** che nominano `vendite_contabili`, `fn_get_or_create_vendite_contabile`, `fn_conferma_sistemazione` o `fn_sync_contabili_fondo_fattura` (elenco in §7). Attesi: **nessun cambio** per i 9 che inseriscono direttamente sotto contesto operatore (il livello 3 di §2.4 dà l'emittente della sessione; 7 passano un `codice` proprio e restano no-op); `rls/test-rls-pagamenti-perimetro.sql` **rosso per costruzione** sui test 7, 8 e 10 (pinnano il predicato vecchio): si riscrivono nel verso di §3.3, non si tolgono; `rls/test-role-batch-fatturazione-postura.sql` senza contesto: legge solo privilegi, nessun INSERT (⚠️ diceva «verificare che il ruolo batch passi dal guard»: quel ruolo non fa più girare niente dal 2026-09-05). ⛔ Regressione = **asserzioni**, non file rossi; la baseline non si aggiorna per far passare | pgTAP | `scripts/pgtap-baseline.sh pagamenti rls vendite` |
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

⚠️ **Tre passi di questa tabella sono stati corretti dal piano di sviluppo il
2026-09-15**, e il testo sopra resta com'era scritto: **P-3** non è un append
al CSV base ma un CSV dedicato (una mina di CI in `20260831-03`, §4-bis.0);
**P-5** la risoluzione vive in una funzione che trigger e madre chiamano
(§4-bis.2); **P-7b** usa l'emittente dell'**atto**; **P-12** i file rossi per
costruzione sono tre, non uno (§4-bis.16). Il dettaglio in §4-bis.19.

---

## 4-bis. Piano di sviluppo DB

> ⛔ **Nessun file scritto, nessuna migrazione applicata** (memoria
> `feedback_mai_applicare_migrazioni_db`): questo è il piano. L'esecuzione parte
> su «procedi», lotto per lotto, e l'apply resta di Tid.
>
> **Regole che valgono per tutti i lotti**, e non si ripetono dentro:
>
> * numerazione `NN` **globale per data** fra tutte le cartelle: il 2026-09-15
>   è arrivata a `20`; il primo libero si **rilegge** il giorno in cui si scrive
>   (`find db/changelog/migrations_v2 -name "AAAAMMGG-*"`), non si deduce da
>   qui. ⚠️ **L'ordine relativo dei lotti è un vincolo**: l'autogen mescola
>   `00_schema` e `20_code` per `NN`, quindi L1 < L2 < … < L10 nello stesso
>   giorno, o giorni crescenti;
> * un `changeSet` per file, `logicalFilePath` sempre, `runOnChange: false` in
>   `00_schema`/`20_code` (divieto presidiato in CI), `validCheckSums: ANY`
>   **al plurale** solo dove è lecito (mirror di `80_data`);
> * il corpo di una funzione esistente si copia dalla **doc auto-gen**
>   (`docs/it/dbzero/<schema>/funzioni/<nome>.md`), mai da uno YAML —
>   ⚠️ l'auto-gen non chiude il `$function$` con il `;` e scioglie i `%TYPE`
>   della firma: la **firma** si prende dall'ultimo YAML;
> * `%TYPE` in firma, `DECLARE` e `RETURNS TABLE`; `SECURITY INVOKER`/`DEFINER`
>   **espliciti**;
> * errori con `script.fn_log_and_raise_error(area, funzione, codice, context,
>   tx_id, VARIADIC valori)`: `codice` al backend, `context->>'campo'` al
>   frontend, `VARIADIC` all'operatore — e un messaggio **senza** `%s` vuole
>   `VARIADIC ARRAY[]::text[]` esplicito;
> * una preCondition di `00_schema`/`20_code` non interroga `80_data`: la
>   famiglia `DISTINTA` è una **stringa** risolta a runtime; i codici errore
>   idem;
> * la prova è **l'SQL estratto** dagli YAML in `BEGIN … ROLLBACK` con
>   `ON_ERROR_STOP=1`, poi i pgTAP nella stessa transazione (§4-bis.18).

### 4-bis.0 Il quadro in una tabella

| Lotto | Cosa | Fase | Dipende da | Sblocca |
| --- | --- | --- | --- | --- |
| **L1** | tre colonne (nullable), due FK, **un** indice (`registro_id, anno`; nessuno sull'emittente, §4-bis.19), `DROP DEFAULT` su `codice` | `00_schema/pagamenti` | — | tutto |
| **L2** | `pagamenti.fn_get_emittente_distinta()` — **la sede unica** dei quattro livelli di D4 | `20_code/pagamenti` | L1 (`%TYPE` sulle colonne nuove) | L3, L6 |
| **L3** | `trgfn_vendite_contabili_emittente()` + trigger `a10_emittente_ins_upd` | `20_code/pagamenti` | L2 | il `NOT NULL` di L5b (riempitore prima del vincolo) |
| **L4** | `trgfn_vendite_contabili_gen_codice()` + trigger `a10_gen_codice_ins` | `20_code/pagamenti` | L1 | il `DROP DEFAULT` smette di lasciare `codice` vuoto |
| **L5a** | backfill del pregresso (canale → lotto → fattura unica) | `00_schema/pagamenti` | L3 (ordine `NN`) | L5b |
| **L5b** | `SET NOT NULL`, con il cancello «zero residui» (fail-closed) | `00_schema/pagamenti` | L5a, ✅ 5730/5869 → sr 72 a mano (§4-bis.5) | L9 |
| **L6** | `fn_get_or_create_vendite_contabile`: `p_emittente_fiscale_id`, chiave di riuso, INSERT | `20_code/pagamenti` | L2 | BE-1 |
| **L7** | `fn_conferma_sistemazione`: via `codice`, dentro l'emittente dell'atto | `20_code/pagamenti` | L4 | presidio sede unica |
| **L8** | `fn_crea_distinta_correzione`: copia l'emittente | `20_code/pagamenti` | L1 | — |
| **L9a** | policy testata sulla colonna + guard di scope in modo `soggetto_ruolo` | `00_schema/pagamenti` | L5b | D3 |
| **L9b** | policy **righe** e **lotti** senza il ramo «senza canale» | `00_schema/pagamenti` | L9a, L10 | D3 sui satelliti |
| **L10** | `fn_resolve_emittente_fiscale_id` modo `contabile` sulla colonna + COMMENT dei due lettori | `20_code/script` | L1 | L9b |
| **L11** | famiglia `DISTINTA`: **CSV dedicato** + loader | `80_data` | L1 (il guard dei riferimenti legge la tabella) | L12 |
| **L12** | registri `DIS-<sr>` per gli emittenti esistenti | `80_data` | L11 | L4 raggiungibile |
| **L13** | i due codici errore + messaggi (append ai CSV vivi) | `80_data/config` | — | L2 |
| **L14** | `fk_index_policy` per le due FK nuove | `80_data` | L1 | `vw_fk_con_indice_missing_policy` a zero |
| **L15** | pgTAP nuovo `pagamenti/test-distinta-numerazione-registro-v1.sql` | `db/pgtap` | tutti | — |
| **L16** | **quattro** pgTAP rossi per costruzione (§4-bis.19), due aggiunte nei file delle madri, censimento sui 23 | `db/pgtap` | tutti | baseline che non si muove |
| **L17** | documentazione manuale + guida | `docs/` | tutti | — |

⚠️ **Perché L3 e L4 stanno PRIMA di L5b, ed è la lezione della commessa**
(`brief-db-emittente-commessa-invariante` §7.0): il `NOT NULL` non deve
prendere un `NN` più basso dei trigger che riempiono la colonna. Qui la
finestra non è esercitata da nessun `INSERT` durante il migrate, ma l'ordine
costa zero e una regola con un'eccezione «tanto qui non serve» è la prima che
si copia male.

⚠️ **Perché L10 sta PRIMA di L9b**: le policy dei satelliti chiamano
`fn_scope_ef_whitelist_via_contabile`, che passa dal modo `contabile` del
risolutore. Finché il risolutore legge la catena per canale, una distinta
**senza canale** risolve `NULL` e le sue righe sparirebbero **anche al suo
emittente** nel tratto fra L9b e L10.

⚠️ **Perché L11 non è un append a `famiglie_documento.csv`** — 🔴 trovato
scrivendo il piano, e il brief §4 P-3 lo dava per append.
`20260831-03-seed-registri-famiglie-per-emittente` ha
`sqlCheck expectedResult: 4` su «famiglie attive ≠ FATTURA» con `onFail: HALT`.
Su un database ricostruito da zero il mirror base (`20260830-14`) gira **prima**
e caricherebbe sei righe: il cancello trova **5**, e il migrate muore **in
CI**. Su dev non si vede: quel changeSet è `runOnChange`, ma ri-esegue solo se
**il suo file** cambia — e nessuno lo tocca. È la
forma esatta del difetto già pagato il 2026-09-02 (`20260831-53`: «il changelog
descrive un mondo che esiste solo dove qualcuno è passato prima»).
⇒ La sesta famiglia va in un **CSV dedicato con loader suo**, numerato dopo i
quattro mirror laterali: alla corsa di `20260831-03` le famiglie sono ancora
cinque. È il pattern di casa (`parameters*.csv` su cinque file,
`tipi_doc_fiscale_registri*.csv`, `famiglie_documento_*.csv` stessi).
~~⛔ **Non si rilassa il cancello** di `20260831-03` (changeSet mergiato): resta
scritto in §8 che la **settima** famiglia dovrà fare la stessa cosa.~~
🔴 **Smentito dalla CI il 2026-09-17** (§9): il CSV dedicato non è bastato,
perché il cancello non scatta solo nell'ordine di `80_data` — scatta anche
**fuori ordine**, alla ri-esecuzione una-tantum che Liquibase 5.0.4 impone a
ogni `runOnChange` con un change `dbms:` (in CI: la seconda invocazione,
`ci_apply`, dopo `20260915-33`). Un cancello su «quante righe ci sono oggi» era
una fotografia, non un presidio: ora conta le **quattro famiglie per nome**, e
il CSV dedicato resta per la ragione buona (la famiglia nasce col catalogo
completo), non come schivata di una mina.

---

### 4-bis.1 L1 — Le tre colonne, e il DEFAULT che cade

**File**: `00_schema/pagamenti/AAAAMMGG-NN-alter-vendite-contabili-emittente-registro-anno-mctit.yaml`

```sql
ALTER TABLE pagamenti.vendite_contabili
    ADD COLUMN emittente_soggetto_ruolo_id bigint,   -- NOT NULL in L5b
    ADD COLUMN registro_id                 bigint,
    ADD COLUMN anno                        smallint;

ALTER TABLE pagamenti.vendite_contabili
    ADD CONSTRAINT fk_vendite_contabili_emittente_sr
        FOREIGN KEY (emittente_soggetto_ruolo_id)
        REFERENCES anagrafiche.soggetti_ruoli (id),
    ADD CONSTRAINT fk_vendite_contabili_registro
        FOREIGN KEY (registro_id)
        REFERENCES vendite.registri_fatturazione (id);

-- ⚠️ NESSUN indice sull'emittente (scritto così in 20260915-21; il brief ne
--    prevedeva uno «perché la policy filtra ogni lettura»): la policy di L9a
--    filtra ATTRAVERSO fn_scope_ef_whitelist_via_sr(), non con un confronto
--    sulla colonna, e il planner non lo userebbe mai; le sorelle
--    (fk_fatturazione_lotti_emittente_sr, fk_sistemazioni_emittente) non ne
--    hanno; e un indice col nome canonico accanto alla riga `false` di L14 che
--    lo nomina verrebbe DROPPATO a ogni corsa del 90_end (apply_fk_index_policy).
-- Copre la FK sul registro e l'asse del contatore, come ix_commesse_registro_anno.
CREATE INDEX ix_vendite_contabili_registro_anno
    ON pagamenti.vendite_contabili (registro_id, anno);

-- ⛔ Con il DEFAULT ancora sulla colonna NEW.codice arriverebbe pieno e il
--    trigger di L4 (no-op su codice fornito) non numererebbe mai niente.
ALTER TABLE pagamenti.vendite_contabili ALTER COLUMN codice DROP DEFAULT;

COMMENT ON COLUMN pagamenti.vendite_contabili.emittente_soggetto_ruolo_id IS '…';
COMMENT ON COLUMN pagamenti.vendite_contabili.registro_id IS '…';
COMMENT ON COLUMN pagamenti.vendite_contabili.anno IS '…';
```

* FK verso `anagrafiche.soggetti_ruoli (id)` come le sorelle
  (`fk_fatturazione_lotti_emittente_sr`, `fk_sistemazioni_emittente`): SR e non
  PK. ⚠️ La FK **non** garantisce che quel soggetto-ruolo sia un emittente: lo
  garantisce il livello 0 di L2.
* ⚠️ Verificato su `pg_attribute`: `anagrafiche.soggetti_ruoli` **non ha
  `attivo`** → la FK sull'emittente **non** genera nessun `require_attivo`. La
  FK sul registro sì: a `ci_apply` nascono il `CONSTRAINT TRIGGER … require`
  sulla distinta (AFTER, `DEFERRABLE INITIALLY DEFERRED` — il pgTAP vuole
  `SET CONSTRAINTS ALL IMMEDIATE`) e il `block_deact` su
  `registri_fatturazione`, entrambi col nome **hashato** a 63 caratteri: in
  pgTAP si cercano per funzione + argomenti, mai per nome.
* `rollback`: DROP dell'indice, delle due FK e delle tre colonne, e **ripristino
  del DEFAULT** con l'espressione letta dall'auto-gen
  (`concat('VC_', to_char(clock_timestamp(), …), '_', substr(md5(…), 1, 8))`):
  un rollback che lasciasse `codice` senza default e senza trigger romperebbe
  ogni INSERT.
* preConditions: `tableExists pagamenti.vendite_contabili` + `NOT columnExists
  emittente_soggetto_ruolo_id`, `onFail: HALT`.

---

### 4-bis.2 L2 — `fn_get_emittente_distinta`: i quattro livelli in una sede sola

**File**: `20_code/pagamenti/AAAAMMGG-NN-create-fn-get-emittente-distinta-mctit.yaml`

⭐ **Perché una funzione e non solo il trigger, ed è un fatto del modello.**
La chiave di riuso di `fn_get_or_create_vendite_contabile` deve includere
l'emittente (D3) **prima** dell'INSERT — è la `SELECT … WHERE` che decide se
«ridà quella di prima». Un trigger risolve solo dentro l'INSERT: se la madre
cercasse con l'emittente a `NULL` non troverebbe mai niente e aprirebbe una
testata a ogni chiamata, cioè la manuale smetterebbe di essere il lotto di
lavoro dell'operatore (D12-a). Due copie della risoluzione — nella madre e nel
trigger — sarebbero la seconda sede che D4 esiste per impedire. ⇒ La regola
sta in **una funzione**; il trigger la applica a ogni INSERT (per gli `INSERT`
diretti dei pgTAP di §7 e per chiunque scriva da SQL), la madre la chiama per
la chiave di riuso. È lo stampo `fn_check_*` + guard che la chiama (§12.5.2
delle linee guida), nella variante «risolve o solleva» di
`anagrafiche.fn_get_emittente_fiscale_id`.

```sql
CREATE OR REPLACE FUNCTION pagamenti.fn_get_emittente_distinta(
    p_emittente_soggetto_ruolo_id pagamenti.vendite_contabili.emittente_soggetto_ruolo_id%TYPE,
    p_ente_incasso_id             pagamenti.vendite_contabili.ente_incasso_id%TYPE)
RETURNS bigint
LANGUAGE plpgsql
VOLATILE            -- il log dell'errore, come fn_get_registro_documento
SECURITY INVOKER    -- la lettura del canale passa dal risolutore, che è DEFINER
```

| Livello | Condizione | Esito |
| --- | --- | --- |
| **0** | `p_emittente_soggetto_ruolo_id` dato **e** `script.fn_resolve_emittente_fiscale_id('soggetto_ruolo', …)` risponde `NULL` | `E_PAGAMENTI_CHIAMATA_NON_VALIDA` (TECNICO, già a catalogo: «Chiamata non valida a %s: %s»): un SR che non è un emittente lo produce solo un chiamante rotto — la FK non lo ferma. ✅ Confermato da Tid il 2026-09-15 |
| **1** | dato; se c'è anche il canale, `fn_resolve_emittente_fiscale_id('ente_incasso', p_ente_incasso_id)` deve dare lo **stesso** emittente | dissenso → `E_CONTABILE_CANALE_DI_ALTRO_EMITTENTE` (`campo` = `ente_incasso_id`); altrimenti **torna il dato** |
| **2** | canale dato | il suo emittente → `emittenti_fiscali.soggetto_ruolo_id`. ⚠️ Se il canale **non risolve** (conto intestato a un SR che non è emittente) → `E_CONFIG_MANCANTE` («il conto di incasso del canale %s non è intestato a un emittente fiscale»), **non** il livello 3: attribuire il denaro di un canale all'emittente in sessione è l'attribuzione che D4 vieta |
| **3** | `app.current_user_id` valorizzata | `script.fn_resolve_emittente_for_user(user)` → PK → SR. ⭐ Quella funzione legge **prima** la GUC `app.current_emittente_id` (l'emittente attivo scelto in sessione, se in perimetro) e poi la riga 1-a-1: un super admin che ha scelto un emittente attivo risolve **qui**, senza passare dal form |
| **4** | niente | `E_CONTABILE_EMITTENTE_OBBLIGATORIO` (`campo` = `emittente_fiscale_id`, `VARIADIC ARRAY[]::text[]`) |

* ⛔ Nessun livello «default dell'installazione» (§2.4).
* Il canale si legge **solo** attraverso il risolutore `DEFINER`: `enti_incasso`
  ha la RLS, e da INVOKER un operatore fuori perimetro leggerebbe «canale
  inesistente» al posto di «canale di un altro» (memoria: un guard INVOKER
  legge sotto RLS). Per la frase del livello 1 il `codice` del canale si legge
  con `COALESCE((SELECT e.codice …), p_ente_incasso_id::text)`: la frase non
  deve dipendere dalla visibilità.
* `fn_resolve_emittente_for_user` **solleva** su utente `NULL`/`<= 0`: il
  livello 3 la chiama solo con `v_user_id IS NOT NULL`.
* Rubinetto degli accumulatori: i punti nuovi che riusano codici esistenti
  (`E_PAGAMENTI_CHIAMATA_NON_VALIDA` al livello 0, `E_CONFIG_MANCANTE` al 2 — e
  i due di L6) sono `IF v_… IS NULL` su **variabili**, cioè `IGNOTO` per il
  classificatore — nessuna famiglia
  nuova, la baseline B-7 non si muove. I due codici nuovi nascono con **un**
  punto ciascuno.
* COMMENT: i quattro livelli e il perché della funzione (sopra).

---

### 4-bis.3 L3 — Il trigger che applica L2 a ogni scrittura

**File**: `20_code/pagamenti/AAAAMMGG-NN-create-trgfn-vendite-contabili-emittente-mctit.yaml`

```text
pagamenti.trgfn_vendite_contabili_emittente()   -- RETURNS trigger, SECURITY INVOKER
trg_vendite_contabili_a10_emittente_ins_upd
    BEFORE INSERT OR UPDATE OF ente_incasso_id, emittente_soggetto_ruolo_id
    FOR EACH ROW
```

Corpo, in tre righe:

1. **INSERT**: `NEW.emittente_soggetto_ruolo_id :=
   pagamenti.fn_get_emittente_distinta(NEW.emittente_soggetto_ruolo_id,
   NEW.ente_incasso_id)` — i quattro livelli;
2. **UPDATE con `NEW.emittente_soggetto_ruolo_id IS NULL`**: `RETURN NEW`
   senza risolvere. ⚠️ È una scelta (✅ confermata da Tid il 2026-09-15): un
   `UPDATE … SET emittente = NULL` deve essere rifiutato dal `NOT NULL` (23502,
   con `column_name` che arriva al client), **non** ri-riempito in silenzio
   dalla sessione di chi lo fa — sarebbe un cambio di emittente che nessuno ha
   chiesto;
3. **UPDATE con entrambi**: `PERFORM pagamenti.fn_get_emittente_distinta(NEW.…,
   NEW.ente_incasso_id)` — solo i livelli 0-1, cioè la **coerenza** fra il
   canale nuovo e l'emittente della riga (§2.4: «cambiare canale verso un canale
   di un altro → rifiuto»).

⚠️ **L'ordine dei `BEFORE ROW` regge sul nome**, verificato sui trigger vivi:

```text
trg_vendite_contabili_a10_emittente_ins_upd            ← L3, risolve      (e)
trg_vendite_contabili_a10_gen_codice_ins               ← L4, numera       (ge)
trg_vendite_contabili_a10_guard_chiusura_upd           (esistente)        (gu)
trg_vendite_contabili_a10_guard_emittente_scope_ins_upd ← L9a, giudica lo scope
trg_vendite_contabili_a10_guard_ente_centro_ins_upd
trg_vendite_contabili_a10_guard_transizione_upd
trg_vendite_contabili_a10_guard_validazione_upd
trg_vendite_contabili_audit_data_user_upd
trg_vendite_contabili_gen_tx_id_ins_upd
```

I generati dell'automazione (`require_att…`, `_stati_requir…`) sono **AFTER**
e non entrano nell'ordine. Il fatto va nel COMMENT di **entrambi** i trigger
nuovi, perché chi rinomina uno dei tre sposta la risoluzione dopo il numeratore.

---

### 4-bis.4 L4 — Il numeratore

**File**: `20_code/pagamenti/AAAAMMGG-NN-create-trgfn-vendite-contabili-gen-codice-mctit.yaml`

```text
pagamenti.trgfn_vendite_contabili_gen_codice()   -- RETURNS trigger, SECURITY INVOKER
trg_vendite_contabili_a10_gen_codice_ins          BEFORE INSERT FOR EACH ROW
```

Calco di `vendite.trgfn_ordini_gen_numero` (momento) e di
`vendite.fn_get_or_create_commessa` (corpo):

```sql
-- Già numerato -> no-op: rispetta un codice fornito (le fixture dei sette
-- pgTAP con PGTAP_…) e rende innocua ogni finestra. ⛔ Non è una porta per le
-- madri: lo presidia il test 13 di L15.
IF NEW.codice IS NOT NULL AND btrim(NEW.codice) <> '' THEN RETURN NEW; END IF;

-- La sigla: emittenti_fiscali non ha RLS. L3 ha già garantito che il SR sia
-- un emittente (livello 0), quindi qui v_sigla non è mai NULL.
SELECT ef.codice INTO v_sigla
  FROM anagrafiche.emittenti_fiscali ef
 WHERE ef.soggetto_ruolo_id = NEW.emittente_soggetto_ruolo_id;

SELECT * INTO v_ass
  FROM vendite.fn_assegna_numero_documento(
           p_famiglia_documento          => 'DISTINTA',
           p_emittente_soggetto_ruolo_id => NEW.emittente_soggetto_ruolo_id,
           p_data                        => NEW.data_contabile,   -- l'anno, §2.2
           p_documento_id                => NEW.id,               -- già valorizzato (identity)
           p_utility_id                  => NULL,                 -- il registro «per tutte»
           p_corpo                       => v_sigla || '-',       -- come la commessa
           p_serie                       => NULL) v;

-- INSIEME: sono la chiave del documento (trgfn_ordini_gen_numero).
NEW.registro_id := v_ass.registro_id;
NEW.anno        := v_ass.anno;
NEW.codice      := v_ass.numero;      -- DIS-<sigla>-<anno>-<7 cifre>
RETURN NEW;
```

* L'anno lo mette il compositore generico perché il registro nasce con
  `anno_nel_numero = true` (`trgfn_registri_fatturazione_set_anno_nel_numero`
  legge `anno_nel_numero_default` della famiglia all'INSERT del registro —
  verificato sul corpo). Il separatore fra sigla e anno lo aggiunge il
  compositore; quello fra corpo e prefisso **sta nel prefisso** (`DIS-`).
* Emittente senza registro → `E_CONFIG_MANCANTE` da `fn_get_registro_documento`:
  fail-closed, giusto; L12 lo rende irraggiungibile sugli emittenti esistenti,
  `trgfn_emittenti_fiscali_provision_registri` (z90 su `emittenti_fiscali`) su
  quelli futuri.
* Con `presidia_data_documento = false` il pavimento di sequenza è `NULL` e il
  ramo d'errore di `fn_get_next_progressivo` — quello che compone un bersaglio
  con `tipo = p_famiglia_documento` — è **irraggiungibile**: per questo non
  serve una riga `DISTINTA` in `config.tipi_entita`. Dichiarato, non presidiato.
* ⚠️ Fatto verificato su `pg_proc` (non incide qui, ma va detto perché il
  COMMENT dice il contrario): `vendite.fn_assegna_numero_documento` sul DB vivo
  **non è** `SECURITY DEFINER`. Il percorso INVOKER già regge il trigger degli
  ordini come `zeroerp_app` (privilegi su `registri_fatturazione_progressivi`
  verificati), quindi vale anche qui.

---

### 4-bis.5 L5a / L5b — Il pregresso, e il `NOT NULL` che si ferma

**File L5a**: `00_schema/pagamenti/AAAAMMGG-NN-backfill-vendite-contabili-emittente-mctit.yaml`
**File L5b**: `00_schema/pagamenti/AAAAMMGG-NN-alter-vendite-contabili-emittente-not-null-mctit.yaml`
(⚠️ `NN` di L5a **maggiore** di L3; L5b subito dopo)

**L5a** — tre `UPDATE` nell'ordine di §2.6, ognuno `WHERE emittente_soggetto_ruolo_id IS NULL`:

```sql
-- 1) dal canale
UPDATE pagamenti.vendite_contabili c
   SET emittente_soggetto_ruolo_id = ef.soggetto_ruolo_id
  FROM pagamenti.enti_incasso e
  JOIN anagrafiche.soggetti_ruoli_conti_bancari src ON src.id = e.soggetto_ruolo_conto_bancario_id
  JOIN anagrafiche.emittenti_fiscali ef ON ef.soggetto_ruolo_id = src.soggetto_ruolo_id
 WHERE e.id = c.ente_incasso_id AND c.emittente_soggetto_ruolo_id IS NULL;

-- 2) dal lotto, se UNO solo
UPDATE pagamenti.vendite_contabili c
   SET emittente_soggetto_ruolo_id = x.sr
  FROM (SELECT vcl.contabile_id, min(l.emittente_soggetto_ruolo_id) AS sr
          FROM pagamenti.vendite_contabili_lotti vcl
          JOIN vendite.fatturazione_lotti l ON l.id = vcl.lotto_id
         GROUP BY vcl.contabile_id
        HAVING count(DISTINCT l.emittente_soggetto_ruolo_id) = 1) x
 WHERE x.contabile_id = c.id AND c.emittente_soggetto_ruolo_id IS NULL;

-- 3) dalla fattura delle righe, se UNA sola
UPDATE … FROM (SELECT r.contabile_id, min(f.emittente_soggetto_ruolo_id) AS sr
                 FROM pagamenti.vendite_contabili_righe r
                 JOIN vendite.fatture f ON f.id = r.fattura_id
                GROUP BY r.contabile_id
               HAVING count(DISTINCT f.emittente_soggetto_ruolo_id) = 1) x …;
```

**L5b** — il vincolo, dietro il cancello:

```sql
ALTER TABLE pagamenti.vendite_contabili
    ALTER COLUMN emittente_soggetto_ruolo_id SET NOT NULL;
```

* Liquibase gira come `zeroerp` (proprietario, RLS non forzata): il backfill
  vede tutte le righe. I trigger di L3 scattano sull'`UPDATE OF
  emittente_…` — livello 0 (è un emittente) e livello 1 (coerente col canale,
  perché **deriva** dal canale) passano per costruzione. Gli altri guard
  `BEFORE UPDATE` (`chiusura`, `transizione`, `validazione`) reagiscono solo a
  un cambio di `stato_id`: verificato sui corpi.
* preConditions di **L5b** (**`onFail: HALT`**, mai `MARK_RAN`):
  `columnExists` **e** `sqlCheck expectedResult: 0` su `SELECT count(*) …
  WHERE emittente_soggetto_ruolo_id IS NULL`. ⚠️ È lecito in `00_schema`: un
  `expectedResult: 0` («nessuna riga cattiva») è fra le forme ammesse dal
  guardrail. ⛔ Ed è il motivo per cui backfill e vincolo sono **due file**:
  una preCondition si valuta **prima** del proprio changeSet, quindi sul file
  del backfill sarebbe rossa sempre. L5a non ha cancelli sul contenuto: su un
  DB da zero tocca zero righe.
* ✅ **Il pregresso che non si risolve da solo — deciso da Tid il 2026-09-15.**
  La query di §4-bis.18 (passo 3) dice quali righe restano a `NULL`: oggi
  **5730 e 5869** (bozze `MANUALE` vuote su CASSA — zero righe, zero lotti,
  zero sistemazioni, verificato). Si assegnano a **«Gestore Test pgTAP»**
  (`soggetto_ruolo_id = 72`), **a mano e per `id`**:

  ```sql
  UPDATE pagamenti.vendite_contabili
     SET emittente_soggetto_ruolo_id = 72
   WHERE id IN (5730, 5869) AND emittente_soggetto_ruolo_id IS NULL;
  ```

  ⚠️ **Quando**: la colonna nasce con L1, quindi l'`UPDATE` non può precedere
  il migrate. Il flusso previsto è: `make db-migrate` → L5b si **ferma** sul
  cancello (è il suo mestiere: «Expected '0' got '2'», con L1–L5a già
  applicati) → l'`UPDATE` qui sopra → di nuovo `make db-migrate`, che riparte
  da L5b. Due lanci, uno stop atteso, nessuna sorpresa. ⛔ **Non entra nel
  changeSet**: sarebbe il quarto livello «default dell'installazione» che
  §2.4 vieta, e nominerebbe un id che esiste solo su questa macchina. È la
  regola di AGENTS §Workflow Safety («prima di un fix software per dati
  errati, correggerli a mano»). Su un DB da zero i tre `UPDATE` di L5a toccano
  zero righe e il cancello passa: nessun `dati_macchina`.
  ℹ️ L'`UPDATE` a mano attraversa L3 (già applicato): livello 0 — sr 72 **è**
  un emittente — e livello 1 — nessun canale — passano; il guard di scope è
  ancora in modo `ente_incasso` (L9a viene dopo) e su canale `NULL` salta.

---

### 4-bis.6 L6 — `fn_get_or_create_vendite_contabile`

**File**: `20_code/pagamenti/AAAAMMGG-NN-update-fn-get-or-create-vendite-contabile-emittente-mctit.yaml`

⛔ **Parametro in più = overload**: `DROP FUNCTION
pagamenti.fn_get_or_create_vendite_contabile(bigint, date, date, bigint, bigint,
text, jsonb, character varying)` **prima** del `CREATE`, con la firma per esteso
nel `COMMENT ON FUNCTION`. Il BE chiama **per nome** (`p_… := %s`, verificato
in `pagamenti_repository.py:701`) e `fn_sync_contabili_fondo_fattura` idem: non
cambiano. Corpo dalla doc auto-gen, con queste modifiche:

1. firma: `p_emittente_fiscale_id anagrafiche.emittenti_fiscali.id%TYPE DEFAULT
   NULL` **in coda** — la PK, ciò che BE e FE conoscono;
2. guard: `p_emittente_fiscale_id <= 0` → `E_PAGAMENTI_CHIAMATA_NON_VALIDA`
   (famiglia `PARAMETRO`, la stessa già in baseline per questa funzione);
   `p_emittente_fiscale_id` dato ma nessuna riga in `emittenti_fiscali` →
   stesso codice («p_emittente_fiscale_id (non è un emittente fiscale)»);
3. risoluzione, **prima** delle due `SELECT` di riuso:

   ```sql
   -- PK -> SR, esplicita, come trgfn_ordini_gen_numero.
   IF p_emittente_fiscale_id IS NOT NULL THEN
       SELECT ef.soggetto_ruolo_id INTO v_emittente_sr
         FROM anagrafiche.emittenti_fiscali ef WHERE ef.id = p_emittente_fiscale_id;
   END IF;
   -- Dal lotto: chi passa un lotto sa già di chi è la distinta.
   IF v_emittente_sr IS NULL AND p_lotto_id IS NOT NULL THEN
       SELECT l.emittente_soggetto_ruolo_id INTO v_emittente_sr
         FROM vendite.fatturazione_lotti l WHERE l.id = p_lotto_id;
       IF v_emittente_sr IS NULL THEN  -- il lotto non c'è, o non si vede (RLS)
           … E_PAGAMENTI_CHIAMATA_NON_VALIDA ('p_lotto_id (lotto inesistente o fuori perimetro)')
       END IF;
   END IF;
   -- Canale / sessione / rifiuto: la sede unica.
   v_emittente_sr := pagamenti.fn_get_emittente_distinta(v_emittente_sr, p_ente_incasso_id);
   ```

   ℹ️ **Perché una distinta può avere un lotto.** Un *fondo fattura* è denaro
   già in casa (un acconto, un accredito) assegnato a una fattura che deve
   ancora nascere. Quando il lotto di fatturazione la emette,
   `fn_ricalcola_totali_fattura` → `fn_sync_contabili_fondo_fattura` deve
   registrare quel denaro come **incasso** della fattura nuova — e un incasso
   sta su una distinta. Non c'è banca né operatore: la distinta è `GENERATA`
   sul centro «fondo fattura», una per lotto (chiave di riuso), agganciata al
   lotto in `vendite_contabili_lotti` per dire «questa l'ha fatta nascere il
   lotto X». Le distinte manuali un lotto non ce l'hanno.
   ⚠️ **Corretto il 2026-09-15 (Tid)**: questa nota diceva «il batch non ha un
   utente in sessione». Falso dal 2026-09-05 (R-2): ogni processo gira con un
   utente tecnico per (processo × azienda), che ha la sua riga 1-a-1 in
   `user_emittenti_fiscali` — il livello 3 risolve **anche per lui**. La
   ragione per cui il lotto resta una sorgente è un'altra, ed è del modello:
   la distinta di un lotto è **dell'emittente del lotto**, chiunque lanci il
   giro. Il giro di massa può partire da un **admin globale in modalità «tutti
   gli emittenti»** (scope `ALL`, nessun emittente attivo): i suoi lotti sono
   di N aziende e la sua sessione non risolve nessun emittente — con il solo
   livello 3 il fondo si fermerebbe al livello 4 in mezzo alla pipeline, con
   una frase pensata per un form. Il lotto porta `emittente_soggetto_ruolo_id
   NOT NULL` e dice il fatto giusto per primo. Sessione e lotto non possono
   dissentire: con un emittente attivo lo scope si restringe a lui, e i lotti
   degli altri non si vedono.
   ⚠️ Il ramo «lotto non visibile» è **fail-closed di proposito**: la funzione
   è INVOKER e `fatturazione_lotti` ha la RLS; senza questo ramo un operatore
   fuori perimetro cadrebbe al livello 3 e la distinta del lotto di un altro
   nascerebbe **sua** — è l'attribuzione silenziosa di §2.4. Dalla pipeline non
   ci si arriva: `fn_sync_contabili_fondo_fattura` legge il lotto della fattura
   che sta lavorando, che è nel perimetro di chi lavora; ci arriva solo una
   chiamata scritta a mano con un lotto altrui. È un `IF` solo, TECNICO, e resta
   perché il modello ammette il caso — ✅ **confermato da Tid il 2026-09-15**:
   senza, un lotto altrui darebbe una distinta intestata alla sessione e
   agganciata al lotto di un altro (la FK del link non guarda la RLS);
4. chiave di riuso: `AND vc.emittente_soggetto_ruolo_id = v_emittente_sr` in
   **entrambe** le `SELECT` (D3: la `GENERATA` senza lotto smette di
   raccogliere di tutti);
5. INSERT: `emittente_soggetto_ruolo_id` fra le colonne, con `v_emittente_sr`.
   Il trigger L3 la ri-valuta (livelli 0-1, idempotente) e L4 numera.
   ⛔ `codice` **non** entra fra le colonne (D5).

Il COMMENT esistente resta e si allunga con la rev.

---

### 4-bis.7 L7 — `fn_conferma_sistemazione`

**File**: `20_code/pagamenti/AAAAMMGG-NN-update-fn-conferma-sistemazione-senza-codice-mctit.yaml`

`CREATE OR REPLACE` a firma identica (`RETURNS TABLE` invariato). Nell'INSERT
della distinta:

* **via** `codice` e la sua espressione `concat('SIS_', v_atto.id, …)`: l'id
  dell'atto è già in `meta.sistemazione_id`, e `uq_sistemazioni_contabile`
  tiene l'unicità «una contabile per atto»;
* **dentro** `emittente_soggetto_ruolo_id => v_atto.emittente_soggetto_ruolo_id`.
  ⚠️ Il brief §4 P-7b diceva `v_fattura.emittente_soggetto_ruolo_id`: si usa
  **l'atto**, che è `NOT NULL` su `pagamenti.sistemazioni` ed è lo stesso valore
  che la funzione scrive due righe sopra sul fondo (`RIPORTO`) — una sola
  sorgente dentro la stessa funzione. I due coincidono per costruzione (l'atto
  nasce dalla fattura d'origine), ma se un giorno dissentissero sarebbe l'atto
  a dire di chi è il documento dell'atto;
* il commento in linea «⭐ Il codice porta l'id dell'atto» e la frase nel
  COMMENT («Il codice della distinta porta l'id dell'atto») **si riscrivono**:
  «la distinta di una sistemazione prende il numero dal registro DISTINTA
  dell'emittente dell'atto; l'atto si ritrova da `meta.sistemazione_id` e da
  `sistemazioni.contabile_id`».

Le due righe e il resto della madre non cambiano. Il canale del rimborso (se
`RIMBORSO`) e l'emittente dell'atto passano il livello 1 di L2 per costruzione:
il canale lo sceglie chi paga, dentro il proprio perimetro (RLS su
`enti_incasso`).

---

### 4-bis.8 L8 — `fn_crea_distinta_correzione`

**File**: `20_code/pagamenti/AAAAMMGG-NN-update-fn-crea-distinta-correzione-emittente-mctit.yaml`

`CREATE OR REPLACE` a firma identica. Nella `SELECT … FOR UPDATE OF c` si
legge anche `c.emittente_soggetto_ruolo_id` (variabile `v_emittente_sr
pagamenti.vendite_contabili.emittente_soggetto_ruolo_id%TYPE`) e nell'INSERT
della distinta nuova entra `emittente_soggetto_ruolo_id`. Stesso emittente ⇒
stesso registro ⇒ il codice della correzione è il **prossimo** del sezionale;
`meta.correzione_di` continua a portare il codice dell'originale (che per il
pregresso sarà un `VC_…`, ed è giusto: è il nome che quel documento ha).
Il commento in linea «⛔ `codice` non si passa: lo mette il DEFAULT della
colonna» diventa «lo assegna il trigger sul registro».

---

### 4-bis.9 L9a — La policy della testata, e il guard di scope che cambia modo

**File**: `00_schema/pagamenti/AAAAMMGG-NN-rewrite-rls-vendite-contabili-su-emittente-mctit.yaml`
(⚠️ `NN` maggiore di L5b: una riga con la colonna a `NULL` sparirebbe a tutti)

```sql
DROP POLICY IF EXISTS rls_vendite_contabili_perimetro_incasso ON pagamenti.vendite_contabili;

CREATE POLICY rls_vendite_contabili_perimetro_incasso
    ON pagamenti.vendite_contabili
    AS PERMISSIVE FOR ALL
    USING (
        current_setting('app.ruolo_applicativo', true) = 'OPERATORE'
        AND script.fn_scope_ef_whitelist_via_sr(
                NULLIF(current_setting('app.current_user_id', true), '')::integer,
                emittente_soggetto_ruolo_id))
    WITH CHECK ( -- identica alla USING, forma di rls_fatturazione_lotti_ef_whitelist
        … );

COMMENT ON POLICY … IS '…';   -- riscritto: la distinta sa di chi è; il ramo
                              -- «senza canale = di tutti» non descrive più il modello

DROP TRIGGER IF EXISTS trg_vendite_contabili_a10_guard_emittente_scope_ins_upd
    ON pagamenti.vendite_contabili;
CREATE TRIGGER trg_vendite_contabili_a10_guard_emittente_scope_ins_upd
    BEFORE INSERT OR UPDATE ON pagamenti.vendite_contabili
    FOR EACH ROW EXECUTE FUNCTION
    script.trgfn_guard_emittente_scope('soggetto_ruolo', 'emittente_soggetto_ruolo_id');
```

* Il nome della policy **resta**: la nominano il COMMENT delle policy sorelle e
  i pgTAP; cambia il predicato, non l'identità. Stessa cosa per il trigger.
* ⚠️ Il `DROP TRIGGER` è su un trigger scritto **a mano** (`20260822-20`), non
  su uno generato: il guardrail §11.5 non si applica.
* `ENABLE ROW LEVEL SECURITY` è già acceso e **non forzato** (verificato:
  `relforcerowsecurity = f`), e deve restarlo: il risolutore è DEFINER e con il
  FORCE rientrerebbe sotto la policy — ricorsione (COMMENT del 22-08).
* `INSERT … RETURNING` passa dalla `USING`: la riga appena creata porta
  l'emittente risolto da L3, che è quello in sessione o del canale in
  perimetro — il guard di scope la rifiuta **prima** e con una frase, la policy
  non arriva mai a dire «new row violates…» (§3.3).
* preConditions (HALT): `sqlCheck 1` su `information_schema.columns … is_nullable
  = 'NO'` per la colonna (schema, lecito) + `pg_proc` per
  `fn_scope_ef_whitelist_via_sr`.
* `rollback`: la policy di `20260822-20` e il trigger in modo `ente_incasso`,
  copiati per esteso.

### 4-bis.9-bis L9b — I satelliti: righe e lotti senza il ramo «senza canale»

**File**: `00_schema/pagamenti/AAAAMMGG-NN-rewrite-rls-satelliti-vendite-contabili-mctit.yaml`
(⚠️ `NN` maggiore di L9a **e** di L10)

🔴 **Correzione al brief §3.2**, che dava righe e lotti «nessuna modifica»
citando `20260822-21` e `20260910-18`. Le policy **vive** (lette da
`pg_policy` il 2026-09-15) sono `20260822-24` per le righe e `20260910-18` per
i lotti, e portano **entrambe** un terzo ramo:

```sql
OR EXISTS (SELECT 1 FROM pagamenti.vendite_contabili c
            WHERE c.id = contabile_id AND c.ente_incasso_id IS NULL)
```

cioè «la testata senza canale è di tutti, e il satellite la segue» (sulle righe
con in più `fattura_id IS NULL`). Dopo D3 quel ramo è **morto per costruzione**
— l'`EXISTS` legge la testata sotto la nuova policy, quindi vede solo ciò che
il ramo 1 (`via_contabile`) già copre — ma il suo commento («non c'è niente in
questa riga che dica di chi sia») diventa **falso**, e un predicato di sicurezza
con un ramo che nessuno può più raggiungere è la forma in cui una regola
cambia senza che si veda. ⇒ Si riscrivono entrambe **senza** il terzo ramo,
stesso nome, COMMENT riscritto («il perimetro è l'emittente della testata,
letto dal risolutore»). ⚠️ Il ramo 2 delle righe (la fattura, quando c'è)
**resta**: è quello che fa vedere la riga sul proprio documento finita sulla
distinta di un altro. Rollback: le due policy attuali per esteso.

---

### 4-bis.10 L10 — Il risolutore legge la colonna

**File**: `20_code/script/AAAAMMGG-NN-update-fn-resolve-emittente-fiscale-id-modo-contabile-mctit.yaml`

`CREATE OR REPLACE` di `script.fn_resolve_emittente_fiscale_id(text, bigint)`
— `STABLE SECURITY DEFINER SET search_path = pg_catalog, pg_temp`, corpo dalla
doc auto-gen, **gli altri cinque modi intatti**. Il ramo `contabile`:

```sql
ELSIF p_modo = 'contabile' THEN
    -- Rev AAAA-MM-GG: la distinta SA di chi e' (D3). Una lettura, non tre JOIN,
    -- e una distinta interna non risolve piu' NULL: e' del suo emittente.
    SELECT ef.id INTO v_emittente_fiscale_id
      FROM pagamenti.vendite_contabili c
      JOIN anagrafiche.emittenti_fiscali ef
        ON ef.soggetto_ruolo_id = c.emittente_soggetto_ruolo_id
     WHERE c.id = p_valore;
```

Nello stesso file, due `COMMENT ON FUNCTION`:

* `script.fn_scope_ef_whitelist_via_contabile`: **nessuna modifica di codice**;
  la frase «su una distinta INTERNA … risponde FALSE — ed è ciò che serve»
  diventa falsa e si riscrive;
* `script.trgfn_guard_emittente_scope`: nella lista dei modi la nota «una
  distinta interna non è il canale di nessuno» resta vera per il **ramo**
  «non risolvibile», falsa per la distinta: si riscrive.

⚠️ `CREATE OR REPLACE` di una `SECURITY DEFINER`: il proprietario resta chi
migra (`zeroerp`), e il `search_path` blindato va **ricopiato** — una DEFINER
senza è un'iniezione che aspetta. ⚠️ Cambiare il **motivo** di una funzione di
risoluzione censisce i pgTAP che ne pinnano la risposta: sono i tre di L16, già
contati.

---

### 4-bis.11 L11 — La sesta famiglia, in un CSV suo

**File**: `80_data/sql/vendite/famiglie_documento_distinta.csv` +
`80_data/changelog/AAAAMMGG-NN-seed-famiglia-documento-distinta-mctit.yaml`

```csv
codice_interno,descrizione,schema_tabella,nome_tabella,colonna_numero,colonna_billing_account,colonna_serie,attivo,presidia_data_documento,prefisso_default,lunghezza_default,anno_nel_numero_default,ammette_regole_fiscali,meta,data_insert,user_insert,data_update,user_update
DISTINTA,Distinta contabile di incasso,pagamenti,vendite_contabili,codice,NULL,NULL,true,false,DIS-,7,true,false,{},AAAA-MM-GG 00:00:00+02,SEED,AAAA-MM-GG 00:00:00+02,SEED
```

Loader `loadUpdateData`, `runOnChange: true` + `validCheckSums: ANY` (è un
mirror), `primaryKey: "codice_interno"`, `nullValue: "NULL"` (il token
letterale, come i quattro laterali: `colonna_billing_account` e `colonna_serie`
**devono** arrivare `NULL`, non stringa vuota), tutte le colonne dichiarate.

* ⛔ **Senza `id`**: la PK è `IDENTITY BY DEFAULT` e la prende da sé. Un id
  esplicito non avanza la sequence (memoria) e nessuno referenzia
  `famiglie_documento.id` — le FK vanno su `codice_interno`.
* preConditions (HALT): `tableExists vendite.famiglie_documento`,
  `columnExists anno_nel_numero_default`, `tableExists pagamenti.vendite_contabili`
  (il guard `trgfn_famiglie_documento_guard_riferimenti` fa `to_regclass` sulla
  tabella dichiarata e pretende la colonna `codice`).
* Il guard dei riferimenti con `colonna_billing_account` `NULL` **salta** il
  controllo su `pg_attribute` (`20260914-08`): la porta aperta il 14-09 per
  l'ordine d'acquisto la attraversa per prima la distinta.
* `uq_famiglie_documento_tabella_attiva (schema_tabella, nome_tabella) WHERE
  attivo`: coppia nuova, nessuna collisione.
* Su ri-esecuzione (`runOnChange`) l'`UPDATE` riscrive gli stessi valori: il
  guard di struttura confronta con `IS DISTINCT FROM` e `lock_columns` su
  `codice_interno` vede lo stesso valore. Provato nella ricetta con **due**
  passate dell'upsert.
* Il changeSet `20260830-14` dice «una famiglia nuova è un append, mai un
  INSERT a parte»: era vero fino a `20260831-03`. I CSV non hanno commenti: il
  fatto che il CSV base **non** contenga la sesta famiglia sta nel COMMENT del
  loader L11 e in `vendite/manual/famiglie_documento.md` (L17), che è dove lo
  cerca chi vuole aggiungere la settima. ⚠️ Il 2026-09-17 `20260831-03` **è
  stato editato** (cancello per nome, corpo sulla primitiva): la ragione è in
  §9 e nella sua intestazione, e l'edit fa un RERAN innocuo su dev
  (idempotente, nessuna riga da creare: misurato, due emittenti entrambi con
  registro).

### 4-bis.12 L12 — I registri `DIS-<sr>`

**File**: `80_data/changelog/AAAAMMGG-NN-seed-registri-distinta-per-emittente-mctit.yaml`
(⚠️ `NN` maggiore di L11)

```sql
SELECT vendite.fn_provision_registri_famiglia('DISTINTA');
```

Forma di `20260831-03` (`runOnChange: true` + `ANY`, idempotente sulla coppia),
ma **una chiamata** alla primitiva invece di un `INSERT` ricopiato: la regola di
come nasce un registro sta in `fn_provision_registri` e non si copia. Nasce con
`codice = 'DIS-<sr>'`, `prefisso 'DIS-'`, `lunghezza 7`, `ANNUALE`, e il
trigger `a10_set_anno_nel_numero_ins` mette `anno_nel_numero = true`.

* preCondition (HALT, lecita in `80_data`): `sqlCheck 1` su `famiglie_documento
  WHERE codice_interno = 'DISTINTA' AND attivo` + `pg_proc` per la funzione.
* Su un DB da zero non ci sono emittenti: crea 0 e passa. Gli emittenti che le
  fixture pgTAP costruiscono prendono il registro dal trigger z90.
* `uq_registri_fatturazione_prefisso_suffisso (emittente, prefisso, suffisso)`:
  `DIS-` ≠ `CMM-`/`DDT`/`ORD`/`RESO`; `uq_registri_fatturazione_codice`: `DIS-72`
  ≠ `DDT-72`. Nessuna collisione.
* `rollback`: `DELETE … WHERE famiglia_documento = 'DISTINTA' AND meta->>'origine'
  = 'C2-12' AND NOT EXISTS (distinta con quel registro_id)` — un registro che ha
  numerato non si toglie.

### 4-bis.13 L13 — I due codici

**File**: append a `80_data/sql/config/codici_errore.csv` e
`80_data/sql/config/messaggi_errore.csv` (mirror vivo: `20260614-08`,
`runOnChange` + `ANY`, `nullValue: "NULL"`; la chiave dei messaggi è `id`, oggi
al massimo **1071** → `1072`, `1073`, riletti al momento dell'append).

| codice | classe | nota (chi solleva, perché questa classe) |
| --- | --- | --- |
| `E_CONTABILE_EMITTENTE_OBBLIGATORIO` | `DATO_ERRATO` | `pagamenti.fn_get_emittente_distinta` (livello 4, D4): nessun emittente dato, nessun canale, nessun emittente in sessione — è il super admin / admin globale che apre una manuale su CASSA e deve **scegliere**. Campo `emittente_fiscale_id`. ⛔ Non `E_CONFIG_MANCANTE`: non manca una configurazione, manca una scelta |
| `E_CONTABILE_CANALE_DI_ALTRO_EMITTENTE` | `DATO_ERRATO` | stessa funzione (livello 1): l'emittente indicato e il canale scelto dissentono. Campo `ente_incasso_id`: si corregge il canale, o si cambia emittente |

Messaggi `it`:

* `Per aprire una distinta senza canale bisogna indicare l'emittente.` —
  nessun `%s`, `VARIADIC ARRAY[]::text[]`; `causa`: «senza un canale non c'è
  un conto che dica di chi è il denaro, e chi apre la distinta non lavora per un
  solo emittente»; `soluzione`: «scegliere l'emittente per cui si apre la
  distinta»;
* `Il canale %s è dell'emittente %s, non di %s.` — tre valori: codice del
  canale, sigla dell'emittente del canale, sigla dell'emittente indicato;
  `soluzione`: «scegliere un canale dell'emittente indicato, o cambiare
  emittente».

⚠️ Apostrofo **singolo** nelle celle (il CSV non è SQL); niente segnaposti
malformati (`format()` crasha). Il BE rigenera `error_policies_generated.py` e
scrive i due ripieghi (BE-3): fino a quel commit il cancello del terzo lato è
rosso su Tito-dev — è il presidio che lavora, non un incidente; le due metà si
mergiano insieme.

### 4-bis.14 L14 — `fk_index_policy`

**File**: `80_data/sql/pagamenti/fk_index_policy_vendite_contabili_numerazione.csv` +
`80_data/changelog/AAAAMMGG-NN-upsert-fk-index-policy-vendite-contabili-numerazione-mctit.yaml`

```csv
schema_name,table_name,constraint_name,consentito,dll_command,generated_by_script,user_insert,data_insert
pagamenti,vendite_contabili,fk_vendite_contabili_registro,false,CREATE INDEX IF NOT EXISTS ix_vendite_contabili_registro_id ON pagamenti.vendite_contabili(registro_id);,false,mctit,AAAA-MM-GG 00:00:00+02
pagamenti,vendite_contabili,fk_vendite_contabili_emittente_sr,false,CREATE INDEX IF NOT EXISTS ix_vendite_contabili_emittente_soggetto_ruolo_id ON pagamenti.vendite_contabili(emittente_soggetto_ruolo_id);,false,mctit,AAAA-MM-GG 00:00:00+02
```

Forma di `20260831-09`, ma `onFail: HALT` e non `MARK_RAN` (memoria: `MARK_RAN`
segna senza eseguire). `consentito = false` su entrambe: per il registro
l'indice c'è già (L1, `ix_vendite_contabili_registro_anno` copre per prefisso);
per l'emittente **non c'è e non serve** (la policy filtra via funzione; le
sorelle non ne hanno — §4-bis.19). ⚠️ `dll_command` **sempre**
valorizzato (`chk_fk_index_policy_dll_command_forma`) e nomina l'indice
**canonico**, non quello composto: nominare `…registro_anno` farebbe cancellare
al primo `90_end` l'indice a due colonne.

---

### 4-bis.15 L15 — Il pgTAP nuovo

**File**: `db/pgtap/pagamenti/test-distinta-numerazione-registro-v1.sql`
(runner **app**, preambolo presidiato: `BEGIN`, contesto, `SET CONSTRAINTS ALL
IMMEDIATE`; template `_TEMPLATE.sql.txt`).

**Fixture, costruita** (mai pescata):

```sql
-- ⛔ DUE aziende in DUE istruzioni, contesto sulla SECONDA: sullo scratch la
--    prima creata è il DEFAULT (bootstrap), su dbdev lo è un'altra — B non lo
--    è mai (memoria «due aziende»).
CREATE TEMP TABLE _mondi AS SELECT 'A' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();
INSERT INTO _mondi              SELECT 'B',         * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondi WHERE lato = 'B')); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;
```

Poi banca, filiale, un conto d'incasso per A e uno per B, un canale per
ciascuno **nel contesto del suo padrone** (calco di
`rls/test-rls-pagamenti-perimetro.sql`), il centro `BANCA` e il centro
`CASSA`. Gli emittenti creati dall'helper hanno il registro `DISTINTA` dal
trigger z90 (⚠️ solo se L11 è applicato: il test 1 lo pretende).

**Asserzioni** (plan **19** — numerazione del file scritto; tutte nel verso «si costruisce il caso»):

| # | Cosa | Come |
| --- | --- | --- |
| 1 | B non è il default dell'installazione | `NOT EXISTS (… is_default AND emittente_soggetto_ruolo_id = B.sr)` |
| 2 | la famiglia è a catalogo com'è dichiarata | `is(row(schema, tabella, colonna, ba, serie, prefisso, lunghezza, anno, presidia), row('pagamenti','vendite_contabili','codice',NULL,NULL,'DIS-',7,true,false))` |
| 3 | ogni emittente attivo ha un registro `DISTINTA` con `anno_nel_numero` | conteggio derivato, nessun nome |
| 4 | manuale **con canale** di B → `codice ~ '^DIS-<sigla B>-<anno>-\d{7}$'`, `registro_id` = il registro DISTINTA di B, `anno` = `vendite.fn_get_anno_registro(data_contabile)` | `matches` + `is` sulle tre colonne |
| 5 | la seconda distinta di B — stesso canale, `data_contabile` diversa nello stesso anno, così la chiave di riuso **non** la ridà — è `+1` | `is(progressivo, 2)` letto da `right(codice, 7)` |
| 6 | nel contesto di A, la prima di A è `…0000001` sul **suo** registro: nessuna collisione con B | `is` |
| 7 | `data_contabile` 31/12 e 2/1 → due `anno`, e il secchio nuovo riparte da 1 | `is` sui due progressivi |
| 8 | senza canale, come B → l'emittente è B (livello 3) | `is(emittente_soggetto_ruolo_id, B.sr)` |
| 9 | senza canale e **senza** emittente in sessione (`set_config('app.current_user_id','',true)`, poi rimessa) → `E_CONTABILE_EMITTENTE_OBBLIGATORIO` | `throws_like '%indicare l''emittente%'` su un INSERT diretto. ⭐ Arriva la **nostra** frase e non `E_SCOPE_SENZA_UTENTE` né un 42501: i `BEFORE ROW` scattano prima della `WITH CHECK`, e fra i BEFORE `a10_emittente` precede `a10_guard_emittente_scope` — è l'ordine alfabetico di L3 che qui si misura |
| 10 | emittente A indicato + canale di B → `E_CONTABILE_CANALE_DI_ALTRO_EMITTENTE` | `throws_like '%non di %'` |
| 11 | `codice` fornito (`PGTAP-DIS-KO`) → rispettato, `registro_id`/`anno` `NULL` | `is` |
| 12 | ⭐ **presidio della sede unica**: nessuna funzione in `pg_proc` fa `INSERT INTO pagamenti.vendite_contabili (…)` con `codice` fra le colonne | regex sul `prosrc` delle **tre** madri per nome (perimetro = elenco) |
| 13 | gemello «esiste»: le tre madri contengono quell'INSERT, e **nessun'altra** funzione lo contiene | un quarto scrittore fa rosso: si dichiara aggiungendolo all'elenco |
| 14 | la composizione si prova sui **valori**: `vendite.fn_componi_numero_documento('DIS-', 'ACME-2026-', 1, 7, NULL) = 'DIS-ACME-2026-0000001'` | `is` |
| 15 | `UPDATE` che sposta il canale di una distinta di B su un canale di A → rifiuto (livello 1 su UPDATE) | `throws_like` |
| 16 | la colonna è `NOT NULL` — è il **vincolo** che parla su un UPDATE a NULL, non il trigger | `col_not_null` (memoria: sotto RLS il `WITH CHECK` scatta **prima** di `NOT NULL`, quindi come app il rifiuto è `42501`, come owner `23502`: un `throws_ok(…, '23502')` sarebbe rosso proprio nel runner previsto) |
| 17 | `UPDATE … SET emittente_soggetto_ruolo_id = NULL` → rifiutato, il trigger **non** ri-riempie dalla sessione | `DO` che cattura `not_null_violation OR insufficient_privilege` e scrive `RIFIUTATO:<sqlstate>`, poi `matches('^RIFIUTATO:(23502\|42501)$')` |
| 18 | l'operatore di A **non vede** la distinta senza canale di B (D3, il verso di §3.3) | contesto A, `count = 0` |
| 19 | …e le sue **righe** neppure: il ramo «senza canale = di tutti» non esiste più | contesto A, `count = 0` su `vendite_contabili_righe` |

* Test 9: la GUC si salva in una temp table e si **rimette** subito dopo
  (transazione unica).
* Correzione e sistemazione **non stanno qui**: la fixture di una distinta
  CHIUSA con righe POSTATE e quella di un'eccedenza vera esistono già nei file
  di quelle madri, e si asseriscono lì (L16, due aggiunte).
* Nessun test sui trigger **generati** (nome hashato, e su dev arrivano coi
  job pgAgent, non con `db-ci-apply`): sono presidiati per famiglia da
  `test-registri-per-emittente-v1` e non qui.
* `throws_ok` sempre con SQLSTATE o `throws_like` sulla frase, mai `NULL, NULL`.

### 4-bis.16 L16 — I pgTAP che diventano rossi per costruzione, e il censimento

🔴 **Quattro file**, non uno (il brief P-12 ne prevedeva uno; il piano tre — il quarto è emerso scrivendo, §4-bis.19):

| File | Perché è rosso | Cosa si fa |
| --- | --- | --- |
| `rls/test-rls-pagamenti-perimetro.sql` | test **7** (interna visibile a entrambi) e **10** (riga su manuale senza canale visibile all'altro) pinnano il predicato vecchio | si riscrivono nel verso di §3.3 (**plan 19**): 7 → `0` (B non vede l'interna di A); il vecchio 10 diventa **11** → `0` per B, e nasce il **10** nuovo: A **vede** quella riga dalla sola testata (`count = 1` nel contesto di A, né fattura né canale). ⚠️ Il test **8** (B non vede la riga dell'interna di A) **resta verde nel valore** — era già `0` perché la fattura è di A — e cambia solo il titolo: da «…ma la riga no» a «la testata è di A, e la fattura pure». I titoli cambiano frase: «non è di nessuno» diventa «è del suo emittente». Il test 13 (ex 12: B su canale di A) **resta verde**: il rifiuto arriva dal guard di scope in modo `soggetto_ruolo` con la stessa frase, e L3 ha risolto l'emittente dal canale via DEFINER prima che il guard giudichi |
| `rls/test-rls-vendite-contabili-lotti.sql` | 🔴 **non era nel piano**: la fixture inserisce la distinta INTERNA (`PGTAP-CTBL-INTERNA`, canale `NULL`) **senza emittente e prima di vestire un contesto**: con L3/L5b la sede unica cade al livello 4 e il file **muore in fixture**; e il test **7** (`isnt(manifesto_interna, '0')` letto da B) pinnava il ramo «senza canale = di tutti» | la fixture **dichiara** l'emittente (A, come farebbe la madre dei fondi dal lotto di A); 7 cambia verso (A vede il manifesto della propria interna) e nasce **7-bis** (B → `0`); **plan 11**. Il test 8 (invariante «il satellite non è mai più chiuso della testata») è rimasto identico |
| `pagamenti/test-fn-crea-distinta-correzione.sql` | test **2** `matches(codice, '^VC_\d{17}_[0-9a-f]{8}$')` | → `'^DIS-[A-Z0-9]{2,10}-\d{4}-\d{7}$'` (la sigla ha `chk_emittenti_fiscali_codice_forma ^[A-Z0-9]{2,10}$`), e il titolo «lo genera il DEFAULT» → «lo assegna il trigger sul registro». ⚠️ Il brief lo dava fra i «nessun cambio»: inserisce direttamente **e** asserisce la forma |
| `vendite/test-numero-prefisso-registro-v1.sql` | test **6** `'COMMESSA=CMM-, DDT=DDT, ORDINE=ORD, RESO=RESO'` — i registri di un emittente nuovo | → `'COMMESSA=CMM-, DDT=DDT, DISTINTA=DIS-, ORDINE=ORD, RESO=RESO'`. ⚠️ **Fuori dal censimento di §7**, che cercava i nomi della tabella e delle madri: questo pinna il **catalogo delle famiglie**. Il censimento si rifà anche con `grep -l "famiglie_documento\|'COMMESSA'" db/pgtap` |

**Due aggiunte** (non correzioni) nei file delle madri, dove la fixture c'è già:

| File | Cosa si aggiunge |
| --- | --- |
| `pagamenti/test-fn-crea-distinta-correzione.sql` | la correzione nasce sullo **stesso registro** dell'originale col progressivo **successivo**, e `meta.correzione_di` porta il codice dell'originale |
| `pagamenti/test-sistemazioni-giro-completo.sql` | la distinta del rimborso/compensazione ha un codice `DIS-<sigla dell'emittente dell'atto>-…`, non `SIS_…`, e `meta.sistemazione_id` resta l'aggancio all'atto |

Gli altri **20** del censimento di §7 restano attesi «nessun cambio»: i nove
`INSERT` diretti girano sotto `fn_pgtap_set_contesto_operatore()`, che senza
argomento sceglie un operatore **con riga in `user_emittenti_fiscali`** (letto
dal corpo) — il livello 3 risolve; i sette con `codice` proprio restano no-op
sul numeratore ma **prendono l'emittente** (livello 3), che non asseriscono.
`rls/test-role-batch-fatturazione-postura.sql` legge solo privilegi.
`test-anno-nel-numero-v1` (test 1) filtra le cinque famiglie **per nome** e non
si accorge della sesta: resta verde, e resta un test che non la guarda —
dichiarato, non un difetto.

Verifica: `scripts/pgtap-baseline.sh pagamenti rls vendite` (la lancia Tid).
⛔ Regressione = **asserzioni**, non file rossi; la baseline non si aggiorna
per far passare. Su dbdev alcuni file dipendono dalla popolazione: un rosso
va letto sulla baseline che lo conosce.

### 4-bis.17 L17 — Documentazione

Come in §4 P-13, con tre precisazioni emerse dal piano:

* `vendite/manual/famiglie_documento.md`: la sesta famiglia vive in un **CSV
  dedicato** e il perché (`20260831-03`), più la regola per la settima;
* `pagamenti/manual/vendite_contabili.md` §«Chi la vede»: la correzione porta
  la data e nomina i due changeSet dei satelliti (`20260822-24`, `20260910-18`)
  che il testo del 22-08 non poteva conoscere;
* `script/manual/fn_resolve_emittente_fiscale_id.md`: il modo `contabile` legge
  la colonna; `trgfn_guard_emittente_scope.md`: la distinta è in modo
  `soggetto_ruolo`, il modo `contabile` resta per le righe.

⛔ La doc auto-gen non si edita, né si rigenera (memoria).

---

### 4-bis.18 La prova, prima di chiedere l'apply

1. **Estrarre**, non riscrivere: `changes[].sql.sql` dagli YAML di L1–L10
   (`yaml.safe_load`, in ordine di lotto) più il render dei loader di L11–L14
   con `scripts/liquibase5.sh --url=offline:postgresql updateSQL` (le
   preCondition offline non si valutano: si prova la copia senza). Un file solo,
   `BEGIN; … ROLLBACK;`, `psql -v ON_ERROR_STOP=1`, come il **migratore**
   (su dbdev è `titodb`, `db/internal.env`: proprietario di tabelle e funzioni,
   non membro di `zeroerp_app`, non superuser — ⚠️ quindi la RLS **non** è
   esercitata nella prova: i test che la misurano si leggono solo dopo l'apply,
   come app). ⚠️ Lo script si scrive con `Write` e si lancia da file: il
   guardrail blocca un heredoc che contiene la parola *rollback*.
   ⚠️ `ALTER TABLE … SET NOT NULL` (L5b) dopo l'`UPDATE` di L5a con eventi di
   constraint trigger pendenti fallisce nella stessa transazione: la prova
   apre con `SET CONSTRAINTS ALL IMMEDIATE`.
2. **Il seed nella prova**: solo le righe **nuove** dei CSV di `config`
   (`WHERE codice NOT IN (…)`): l'upsert completo di `messaggi_errore` prende un
   lock per chiave e il primo errore su un codice **vecchio** impicca il dblink
   di `fn_log_error_only` (memoria). L'upsert **completo** di
   `famiglie_documento_distinta.csv` sì — è una riga, e va provato **due volte**
   (la seconda è l'UPDATE della ri-esecuzione, contro i guard di struttura).
3. **Il pregresso** (dbdev): dopo il backfill di L5a,
   `SELECT id, codice FROM pagamenti.vendite_contabili WHERE
   emittente_soggetto_ruolo_id IS NULL` → l'elenco per Tid. Nella prova le
   righe residue si trattano **dentro la transazione** (annullata) per
   arrivare fino ai pgTAP, e lo si scrive nell'esito: la decisione resta a Tid
   (✅ presa: l'`UPDATE` per `id` di 5730/5869 → sr 72, §4-bis.5; nella prova
   è quello, non un `DELETE`).
4. **I pgTAP nella stessa transazione**: `SET ROLE zeroerp_app`, poi L15 e i
   tre di L16 **senza** il loro `BEGIN`/`ROLLBACK` (o in `SAVEPOINT`). I
   `WARNING` «dblink … viola fk_error_log_messaggio_errore_id» sui due codici
   nuovi sono attesi (il seed non è committato): non sono un rosso. Se la
   sessione resta in `DblinkGetResult` per più di qualche secondo, è la trappola
   del punto 2: `pg_cancel_backend`.
5. **Il cancello statico**: `python scripts/guardrail_run_on_change.py`,
   `guardrail_precondition_seed.py`, `guardrail_ddl_su_trigger_automazione.py`,
   `guardrail_grant_ruolo_batch.py`, `guardrail_pgtap_preambolo.py`,
   `guardrail_sql_letterali.py` — tutti a zero.
6. Poi l'apply è di Tid (`make db-migrate`), i trigger generati arrivano coi
   job pgAgent `automations_*` (su dev `db-ci-apply` non li rilancia), la suite
   con `scripts/pgtap-baseline.sh pagamenti rls vendite`. ⚠️ Verde su dbdev non
   dice nulla sulla CI: `zeroerp_ci` ricostruito da zero è l'unico posto dove
   L11 e `20260831-03` si incontrano davvero.

### 4-bis.19 Che cosa il piano ha corretto del brief (per §9)

| Dove | Diceva | Verificato | Effetto |
| --- | --- | --- | --- |
| §3.2 | righe e lotti «nessuna modifica» | le policy vive (`20260822-24`, `20260910-18`) hanno il ramo `ente_incasso_id IS NULL = di tutti` | **L9b** |
| §4 P-3 | append a `famiglie_documento.csv` | `20260831-03` pretende **4** famiglie ≠ FATTURA, HALT, e su un DB da zero gira dopo il mirror base | **L11** CSV dedicato |
| §2.4 D4 | «un trigger con un ordine di risoluzione» | la chiave di riuso della madre vuole l'emittente **prima** dell'INSERT | **L2** funzione + trigger che la chiama |
| §4 P-7b | `v_fattura.emittente_soggetto_ruolo_id` | `sistemazioni.emittente_soggetto_ruolo_id` è `NOT NULL` e il fondo usa già quello | `v_atto.…` |
| §4 P-12 | «nessun cambio» per i nove INSERT diretti; un file rosso | `test-fn-crea-distinta-correzione` pinna `VC_`; `test-numero-prefisso-registro-v1` elenca i registri | tre file in **L16** |
| §2.4 | quattro livelli | un SR dato che **non** è un emittente passa la FK | livello **0** (TECNICO, codice esistente) ✅ confermato |
| §4 P-7a | derivazione dal lotto | un lotto invisibile sotto RLS cadrebbe al livello 3 | lotto **strict** (TECNICO) ✅ confermato |
| §2.4 | — | un `UPDATE … SET emittente = NULL` verrebbe ri-riempito | su UPDATE il trigger non risolve: parla il `NOT NULL` ✅ confermato |

**Aggiunte scrivendo lo sviluppo (2026-09-15, sera):**

| Dove | Diceva | Verificato | Effetto |
| --- | --- | --- | --- |
| §4 P-1/P-10, §4-bis.1 | indice `ix_vendite_contabili_emittente_sr` «perché la policy filtra ogni lettura» | la policy filtra **attraverso** `fn_scope_ef_whitelist_via_sr()` (nessun confronto sulla colonna: il planner non lo userebbe); le sorelle `fk_fatturazione_lotti_emittente_sr` e `fk_sistemazioni_emittente` non ne hanno; e `dbops.apply_fk_index_policy()` **droppa** l'indice che una riga `false` nomina — indice + riga `false` col nome canonico sarebbero in contraddizione a ogni `90_end` | **L1** senza indice sull'emittente; **L14** riga `false` col nome canonico `ix_vendite_contabili_emittente_soggetto_ruolo_id` |
| §4-bis.16 | tre file rossi | `rls/test-rls-vendite-contabili-lotti.sql` inserisce l'interna **senza emittente e senza contesto** (livello 4 → muore in fixture) e il test 7 pinna «di tutti» | **quarto** file in L16 (plan 11, test 7 cambia verso, 7-bis nuovo) |
| §4-bis.16 | test **8** del perimetro fra i rossi | il valore era già `0` (la fattura è di A); cambia solo il **significato** | resta verde; nuovo test 10 (A vede la riga dalla sola testata) e plan 19 |
| §4-bis.15 | test 16 `throws_ok(…, '23502')` | sotto RLS il `WITH CHECK` scatta **prima** di `NOT NULL`: come app arriva `42501`, come owner `23502` (memoria «`col_not_null`, non INSERT») | `col_not_null` + `DO` che accetta i due SQLSTATE (test 16/17, plan 19) |
| §4-bis.6, §5 BE-2 | `fn_sync_contabili_fondo_fattura` «passa dal lotto» | passa `p_lotto_id => v_lotto_id`, che è **NULL** se la fattura figlia non è in nessun lotto (`fatturazione_lotti_fatture`): la distinta del fondo cade al livello **3** (l'emittente di chi agisce), non a quello della fattura. Per un operatore è lo stesso emittente (la fattura la vede solo se è sua); per l'**admin globale** in modo «tutti» il livello 3 non risolve → `E_CONTABILE_EMITTENTE_OBBLIGATORIO`, e in modo «uno» una fattura di un altro emittente darebbe una distinta attribuita **all'emittente della sessione** | ⚠️ **residuo dichiarato, non cambiato** (fuori dal perimetro del brief): la strada corretta è che la madre dei fondi passi `p_emittente_fiscale_id` dall'emittente della **fattura**; da decidere con Tid |
| §2.4 D4 livello 3 | — | il BB parallelo `script.trgfn_default_emittente_fiscale` (`20260915-36`, brief `emittente-di-default-un-bb-solo`) risolve dalla **stessa** `script.fn_resolve_emittente_for_user`: la distinta non lo adotta (ha la sede unica con i livelli 0–2 prima), ma la riserva è la stessa funzione — nessun dissenso | nessuno; scritto perché non si aprano due sedi |

---

## 5. Cosa deve fare il backend *(solo l'elenco: il piano è loro)*

| | Cosa | Perché |
| --- | --- | --- |
| **BE-1** ✅ | `crea_distinta`: `emittente_fiscale_id` **opzionale** nel payload (whitelist + `optional_positive_int`), passato a `get_or_create_distinta` → `p_emittente_fiscale_id` (chiamata nominata). ⛔ Il BE **non risolve** l'emittente dal profilo: lo fa il DB (livello 3), e un secondo risolutore sarebbe una seconda sede. Il 400 con `fields: ["emittente_fiscale_id"]` arriva dal trigger | il campo si accende da solo (`campiErrati`) |
| **BE-2** ✅ | `_DISTINTA_SELECT` + `DistintaRow`: `emittente_soggetto_ruolo_id`, `registro_id`, `anno` e l'emittente nelle **tre forme che `EmittenteFiscaleField` legge in edit** — `emittente_fiscale_id`, `emittente_fiscale_codice`, `emittente_ragione_sociale` (dalla vista `vw_soggetti_ruoli_dettaglio`, la sede del nome). ⚠️ Non `emittente_codice` come diceva questa riga: il nome lo fissa il BB del frontend e i documenti di vendite, e un quarto nome per la stessa cosa sarebbe il difetto che api.md §capability descrive. `LEFT JOIN emittenti_fiscali` su `soggetto_ruolo_id`, che è UNIQUE: nessuna riga duplicata | il drawer dice di chi è; la lista può filtrare (colonna a catalogo, non fatta: non chiesta) |
| **BE-3** ✅ | `genera_error_policies` rigenerato (**tre** codici entrano — anche `E_EMITTENTE_NON_RISOLTO` del BB parallelo — e tre passano in `CODICI_RITIRATI`; zero classi cambiate sugli esistenti) + tre ripieghi in `error_messages_fallback.py`; `test_ogni_codice_vivo_ha_un_messaggio_di_ripiego` e i due guardrail (terzo lato, codici ritirati nei call site) verdi. `ui_action`: nessun override sui tre — la famiglia `E_CONTABILE_*` è tutta sul default di classe, e `campiErrati` accende comunque il campo | cancello CI |
| **BE-4** ✅ | Il commento di `PagamentiRepository.list_distinte` riscritto: la RLS passa dalla colonna, forma di `rls_fatturazione_lotti_ef_whitelist` | un commento che dice il falso è peggio di nessuno |
| **BE-5** ✅ | Test: service (trasporta com'è / passa `None` senza dedurre / rifiuta `0`), DB provvisto (le sei colonne si proiettano, la madre accetta il parametro, e **la catena intera**: `crea_distinta` senza emittente nasce `DIS-<sigla>-<anno>-\d{7}` dell'operatore in sessione; con la PK esplicita arriva com'è e il *get or create* ridà lo stesso documento); `api_pagamenti.md` (campo nuovo, il codice, i due errori, le dipendenze) | |
| **BE-6** ✅ | Verificato: né `famiglie_repository` né il drawer FE cablano lo schema; `vw_famiglie_documento_lista` non filtra e `DISTINTA` compare con `pagamenti` e BA `NULL` (il drawer lo regge con `?? ''`) | la prima famiglia fuori da `vendite` |

---

## 6. Cosa deve fare il frontend *(solo l'elenco)*

| | Cosa | Perché |
| --- | --- | --- |
| **FE-1** ✅ | `ApriDistintaDialog`: `EmittenteFiscaleField` **visibile solo senza canale** — col canale scelto l'emittente è il suo, e sotto il canale una riga lo dice. Il payload porta `emittente_fiscale_id` solo se il campo è a video; `:invalid="campiErrati.includes(…)"` sul campo (prop `invalid` aggiunta al BB) e sul canale (`ente_incasso_id`). ⚠️ **Non «admin globale → Select»** come diceva questa riga: dal 2026-09-02 (decisione di Tid) il BB è **sempre in sola lettura** — l'emittente di lavoro si sceglie una volta dalla topbar, e chi sta in «tutti gli emittenti» vede l'avviso del BB e ha **Apri spento** (`canSave`): è il livello 4 del DB detto prima di premere, come su ogni documento | §2.4 livello 4: chi non ha un emittente in sessione deve sceglierlo — **dalla topbar** |
| **FE-2** ✅ | `DistintaDrawer` header: la **ragione sociale** dell'emittente accanto al codice, con la sigla nel tooltip e come ripiego. ⚠️ Non la sola sigla: sta già dentro `DIS-<SIGLA>-…`, e non è un nome; sul pregresso `VC_…` è l'unico posto in cui si legge di chi è | di chi è, a colpo d'occhio |
| **FE-3** ✅ | i18n `it`/`en` (`pagamenti.distinte.campo_emittente`, `emittente_aiuto`, `emittente_dal_canale`); `check_i18n_keys.py` verde | |
| **FE-4** ✅ | Nessun parsing del codice (ri-verificato il 17-09: solo commenti nominano `DIS-`/`VC_`) | resta così |

---

## 7. Il copione di collaudo — righe da aggiungere

In [collaudo-in-app-incassi-distinte-e-sistemazioni.md](../work-in-progress/collaudo-in-app-incassi-distinte-e-sistemazioni.md),
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
- ⛔ **`20260831-03` pretendeva ESATTAMENTE quattro famiglie ≠ FATTURA**
  (`sqlCheck expectedResult: 4`, `HALT`) e su un DB da zero gira **dopo** il
  mirror base delle famiglie. La sesta famiglia va in un CSV dedicato numerato
  dopo (§4-bis.11) — e la **settima** fa lo stesso, per la ragione del modello
  (nasce col catalogo completo). **Corretto il 2026-09-17** dopo la CI rossa:
  il cancello conta le quattro **per nome**. ⛔ La frase «su dev non si vede
  mai: ri-esegue solo se il suo file cambia» era **falsa**: in Liquibase 5.0.4
  un `runOnChange` con un change `dbms:` viene ri-eseguito **una volta**
  all'update successivo alla prima esecuzione (checksum calcolato dal filtro
  senza Database nello Scope ⇒ il change `dbms:` ne esce ⇒ il checksum salvato
  non torna) — su dbdev i 12 seed così fatti sono tutti `exectype = RERAN`, e
  in CI la ri-esecuzione cade nella seconda invocazione (`ci_apply`), **dopo**
  tutto il resto. Regola: un `sqlCheck` con `HALT` su **quante** righe ha oggi
  una tabella di catalogo è una fotografia che la riga dopo smentisce; si
  conta per nome ciò che il passo pretende, come fanno i laterali.
- ⛔ **Le policy dei satelliti hanno un ramo che nomina il modello vecchio.**
  Righe (`20260822-24`) e lotti (`20260910-18`) dicono «testata senza canale
  = di tutti» con un `EXISTS` sulla testata: dopo D3 è morto per costruzione
  ma il commento mente. Chi cambia il perimetro di una testata censisce i
  satelliti **dalle policy vive** (`pg_policy`), non dal changeSet che le ha
  create: qui il primo era stato riscritto due giorni dopo.
- Dichiarati, non fatti: (a) l'emittente di una riga resta **modificabile da
  SQL** dopo la nascita (nessun lock, come sulle sorelle) — se un giorno si
  decide un lock, vale per le sei famiglie; (b) `E_CONFIG_MANCANTE` è riusato
  da `fn_get_registro_documento` (già a catalogo) e la sua frase nomina la
  famiglia, non «distinta»: accettato, è la stessa frase per DDT e ordini.
- ⛔ **Una FK nuova verso `registri_fatturazione` è SEMPRE anche un motivo
  nuovo in `script.fn_check_registro_disattivabile`** *(aggiunto il 2026-09-18,
  dopo la chiusura)*. P-1 aveva previsto il `block_deact` che l'automazione
  monta sulla FK, e si era fermato lì: il guard rifiuta, la check anticipa, e
  se la check non conosce la figlia il cestino del registro resta acceso su un
  rifiuto certo. L'elenco delle figlie nella check è **scritto a mano** per
  scelta (ogni motivo porta una `reason_key` da tradurre) e tenuto da un
  presidio (`script/test-fn-check-registro-disattivabile-v1` §6) che dice la
  cosa **dopo** l'apply; chi scrive la FK può dirla **prima**: changeSet della
  check nello stesso giro, chiave i18n al FE nello stesso brief. ⚠️ E il guard
  non si vede al migrate: nasce a `ci_apply`, quindi su dev i pgTAP del giorno
  dell'apply erano verdi e quelli del giorno dopo no.

---

## 9. Registro

| Data | Cosa |
| --- | --- |
| **2026-09-18** (dopo la chiusura) | 🔴→✅ **Un'eredità che P-1 aveva previsto a metà.** La riga di P-1 dice che l'automazione monterà «il `block_deact` su `registri_fatturazione`» per la FK del registro — vero — ma non tira la conseguenza: `script.fn_check_registro_disattivabile` (la check che spegne il cestino dei registri) deve **imparare** ogni figlia nuova, o tooltip e rifiuto divergono. L'ha detto il pgTAP `script/test-fn-check-registro-disattivabile-v1` §6, rosso nella baseline del 18-09 (`have: …,vendite_contabili`); su dev il guard è comparso quando le automazioni sono girate dopo l'apply, non al migrate, ed è il motivo per cui i pgTAP del 17 erano verdi. Chiuso con `20260918-05` (motivo `HA_DISTINTE`, ottavo e ultimo, `_EXIST`, quarto valore `pagamenti.vendite_contabili` con lo schema — prima figlia fuori da `vendite`) e tre asserzioni che costruiscono il caso; 📮 chiave i18n `…disattiva_blocco.ha_distinte` al FE. Registrato nel cantiere aperto `brief-db-distinta-ricerca-rate` §9/§6. ⭐ Lezione per §8: **una FK nuova verso `registri_fatturazione` è SEMPRE anche un motivo nuovo nella check** — il presidio lo dice dopo, questa riga lo dice prima |
| **2026-09-17** (sera, dopo la chiusura) | 🔧 **Bonifica sistemica `dbms:` sui `runOnChange`, decisa da Tid dopo il censimento** — è la coda della riga «CI-Validate rossa» qui sotto, e vale oltre questo cantiere. Obiezione di Tid, giusta: il rischio (ripartire fuori ordine e sovrascrivere cose fatte dopo) è di `runOnChange` in sé; `dbms:` aggiunge solo una ri-esecuzione non chiesta. Quindi la domanda per ciascuno non era «ha `dbms:`?» ma «è convergente?». **Censimento**: 53 `runOnChange` con un change `dbms:` in tutto `db/changelog` — 25 legacy (`migrations/00_bootstrap/20250817-*`, `context: ddl`, filtrati in `ci_apply`: lasciati), 14 in `80_data`, 14 in `90_end` (13 + 1 in `ci_apply`). **Precisazione del meccanismo** (bytecode di `ValidatingVisitor`): `isCheckSumValid` gira per tutti i changeSet già eseguiti e con `validCheckSums: ANY` esce **senza** calcolare — solo allora il filtro resta a calcolare senza Database. Senza `ANY` la validazione calcola col Database e cacha: i 12 GRANT di `90_end` (senza `ANY`) sono `EXECUTED`, mai RERAN, e infatti in CI non erano nella seconda passata. Forma pericolosa = `runOnChange` + `dbms:` + `ANY`. **Fatto nuovo, più grave**: dopo la ri-esecuzione spuria Liquibase salva il checksum «di niente» (`9:d41d8cd9…` = MD5 della stringa vuota): su dbdev **175** righe `RERAN` lo portano (103 in `20_code`, 48 in `migrations_v2/`, 13 in `80_data`, 7 in `90_end`, 4 in `00_schema`) — da quel momento un edit dell'SQL di quei changeSet **non ri-esegue mai più**. **Misura** (render offline, SQL vero CSV compreso, snapshot + diff per PK dentro `BEGIN … RAISE EXCEPTION`, `setval` esclusi perché non transazionali): 13 dei 14 di `80_data` ri-eseguiti oggi su dbdev scrivono solo `data_update` (audit); **`20260415-01`** (backfill tipologia listino) aggiornerebbe **221 articoli** (NULL → PRODOTTI) + 191 righe di storico — un backfill una tantum con `runOnChange: true`, e con `validCheckSum` **singolare** (chiave ignorata). Statico: nessun REVOKE successivo sugli oggetti dei 12 GRANT; nessun pgTAP dipende dalla tipologia dei 5 articoli seminati. **Fatto**: (a) 27 changeSet senza `dbms:` (change e rollback, 42 righe) con una nota a ridosso di `runOnChange`; (b) `20260415-01` spento: `runOnChange: false` + `validCheckSums: ANY` (necessario: il checksum salvato è quello vuoto e tornerebbe vincolante), singolare tolto; (c) `guardrail_run_on_change.py`: seconda regola «nei runOnChange di `80_data`/`85_pgagent`/`90_end` nessun change `dbms:`», provata in positivo e in negativo; (d) nota nel passo di `ci-validate.yaml`; (e) `linee-guida-sql.md §11.1`: meccanismo corretto, seconda regola, corollario «convergente + precondizioni per nome, un backfill è una tantum»; (f) `20260831-03`: intestazione e `comment` aggiornati. YAML 28/28, sei guardrail, pre-commit, render offline: verdi. **Effetto al prossimo `make db-migrate`** (previsto e misurato): RERAN dei 13 di `80_data` con `ANY` (solo `data_update`) e di `20260829-34` (grant); `20260205-41` solo se Tid lancia `db-ci-apply`; i 12 GRANT senza `ANY` **non** ripartono (il loro checksum salvato è già quello col change dentro); `20260415-01` non riparte. **Residuo dichiarato**: 221 articoli su dbdev senza `listino_tipologia_id` (213 `titodb`, 5 `zeroerp_app`, 2 `pochi`, 1 `tid`) — non è di questo cantiere, ma il modello non lo impedisce; in CI i 5 articoli seminati restano NULL come su dev. **Aperto a Tid**: `make db-migrate`, rilancio CI, commit (31 file) |
| **2026-09-17** (sera, riconciliazione) | 🔧 Il commit `424d3ce89` («aggiornata documentazione», 16:57) era stato scritto sul brief in `work-in-progress/` **senza vedere la chiusura** delle 15:51: riconciliato nell'archivio al rebase. La riga della CI-Validate (sotto) entra al suo posto; lo stato e il riquadro «CHIUSO» prendono la terza mina di CI; la **decisione sistemica su `runOnChange` + `dbms:`** e la nota del guardrail escono dal brief verso `PROJECT_CONTEXT` §«Aperto — Media priorità» — un brief chiuso non tiene «aperto a Tid» |
| **2026-09-17** (sera) | ✅ **CHIUSO e archiviato in `work-done/`.** Collaudo in-app di Tid: la nuova numerazione funziona — **`DIS-PGTAPEF202-2026-0000001`, il primo numero emesso**. Riquadro «CHIUSO» in testa con ciò che esce: il residuo del fondo fattura fuori lotto (→ `PROJECT_CONTEXT`), le tre righe del copione ancora da provare a video (→ doc di collaudo, righe aggiunte oggi), la colonna «Emittente» in lista (dato, quando serve) |
| **2026-09-17** (pomeriggio, in parallelo alla chiusura) | 🔴→🔧 **CI-Validate rossa dopo il merge (PR #1598), corretta.** Job `validate`, passo «Liquibase CI apply (run automations)» = **seconda** invocazione di Liquibase (`--contexts=ci_apply`): `20260831-03-seed-registri-famiglie-per-emittente` ri-eseguito **dopo** `20260915-33` → `sqlCheck` «famiglie attive ≠ FATTURA» = **5**, atteso 4, `HALT`. Nella prima invocazione (5660 changeSet, ordine di timeline) era passato: il CSV dedicato di L11 aveva fatto il suo. **Perché si è ri-eseguito, letto nel jar di Liquibase 5.0.4** (`tools/liquibase/5.0.4`): `ChangeLogIterator.run` mette il `Database` nello `Scope` solo attorno alla `visit`, **non** attorno ai filtri; `ShouldRunChangeSetFilter.checksumChanged` ricalcola quindi il checksum senza Database, e `ChangeSet.generateCheckSum` (v9) **salta** ogni change con `dbms:` quando `DatabaseList.definitionMatches(dbms, null→"null")` è falso. Il checksum salvato alla prima esecuzione (con Database, change incluso) non torna ⇒ `RERAN` una volta, poi stabile (il RERAN salva il checksum «senza»). Prova su dbdev, sola lettura: i **12** seed `runOnChange` di `80_data` con un change `sql` + `dbms: postgresql` sono **tutti** `exectype = RERAN` (compreso `20260915-34`, RERAN alle 12:39 al secondo migrate), i **164** mirror puri `loadUpdateData` `EXECUTED`; il fenomeno è quello che il guardrail `runOnChange` di `ci-validate.yaml` descrive dal 06-08 («49 funzioni riportate indietro a ogni build») attribuendolo al solo `runOnChange`. Perimetro: 2.110 changeSet hanno un change `dbms:`; ne ri-eseguono fuori ordine i **28** `runOnChange` di `80_data`/`90_end`, tutti tolleranti tranne questo cancello. **Rimedio** (un file, `20260831-03`): (1) `sqlCheck` **per nome** — `codice_interno IN ('DDT','ORDINE','COMMESSA','RESO')` = 4, senza `attivo`, come i laterali; (2) corpo = `fn_provision_registri_famiglia` per ciascuna delle quattro (la copia dell'INSERT del 31-08, senza prefisso né lunghezza, si ritira); (3) precondizione `pg_proc` sulla primitiva, come `20260915-34`; (4) rollback ristretto alle quattro famiglie (`origine = C2-12` lo scrive la primitiva per chiunque); (5) intestazione con il meccanismo. `dbms: postgresql` **resta**: il rimedio è il cancello, non la scomparsa della ri-esecuzione. **Prova**: YAML + 6 guardrail statici + pre-commit verdi; SQL **estratto** dallo YAML in `BEGIN … ROLLBACK` su dbdev via Liquibase `execute-sql`: nuove preCondition = 4 e 1, vecchio cancello = **5** (sarebbe morto anche su dev al primo RERAN), corpo pulito, conteggio C2-12 invariato (10); render `update-sql` offline corretto. Su dev l'edit produce un RERAN innocuo (misurato: 2 emittenti, entrambi con i 4 registri). Aggiornati `vendite/manual/famiglie_documento.md` (rev 17-09) e questo brief (stato, §4-bis.0, L11, §8). **Aperto a Tid**: (a) `make db-migrate` (RERAN di `-03`, atteso «0 righe») e ri-lancio CI; (b) decisione **sistemica** — togliere `dbms:` dai 28 `runOnChange` di `80_data`/`90_end` (checksum deterministico, niente ri-esecuzione in `ci_apply`) o accettare la ri-esecuzione e censire i loro cancelli `HALT` su contenuto; (c) la nota del guardrail `runOnChange` in `ci-validate.yaml` nomina `runOnChange` come causa: la causa è `runOnChange` **+ `dbms:`** |
| **2026-09-17** (pomeriggio, dopo) | ✅ **Tid conferma i due scostamenti** della riga sotto: (1) il super admin in «tutti gli emittenti» **non apre** la distinta finché non sceglie l'emittente dalla topbar — *«quella scelta è legge»* (la decisione del 02-09 vale anche qui, nessuna Select nel form); (2) i tre nomi dei documenti di vendite (`emittente_fiscale_id/_codice`, `emittente_ragione_sociale`) al posto di `emittente_codice` |
| **2026-09-17** (pomeriggio) | ✅ **BE-1..6 e FE-1..4 fatti** (§5, §6) insieme alle quattro richieste BE del brief gemello `emittente-di-default-un-bb-solo` §11 — è la stessa rigenerazione. Policy: +3 codici, 3 ritirati, zero classi mosse; tre ripieghi; nessun override (decisione motivata accanto a `E_PREV_EMITTENTE_NON_RISOLTO`); sei commenti coi nomi morti riscritti. **Due scostamenti dal brief, entrambi sul modello FE già in vigore**: i nomi dei campi emittente seguono `EmittenteFiscaleField` (`emittente_fiscale_id/_codice`, `emittente_ragione_sociale`) e non `emittente_codice`; il campo in `ApriDistintaDialog` è in sola lettura (Tid, 02-09) e il super admin in «tutti» ha Apri spento invece di una Select. Presidi: 17 test policy, 7 guardrail, 20 DB-provvisti fra cui la catena intera dal service (`DIS-<sigla>-2026-\d{7}`, riuso entro l'emittente), 1301 verdi su `core`+`pagamenti`, vitest 28, build e guard FE, `DataTable` grezze 48 = 48. ⏳ Collaudo in-app (§7) e commit a Tid |
| **2026-09-17** | ✅ **Apply e baseline di Tid.** `make db-migrate` si è fermato su `-26` come previsto («Expected '0' got '2'»: 5730 e 5869, le due manuali senza canale né lotto né riga con fattura — le stesse della prova); `UPDATE … SET emittente_soggetto_ruolo_id = 72 WHERE id IN (5730, 5869)`; secondo `make db-migrate` fino a `-35` (e ai `-36…-46` del BB parallelo). **pgTAP verdi** su dbdev — come app, quindi con la RLS esercitata: i 9 rossi «solo RLS» della prova da owner erano davvero solo quello — e sullo scratch da zero. Sullo scratch un solo rosso ignoto, **non di questo cantiere**: `script/test-trgfn-default-emittente-fiscale-v1.sql` (BB emittente di default) moriva in fixture perché il suo SA era l'**unico** SUPER_ADMIN del database da zero e `fn_change_user_emittenti_scope` rifiuta il cambio di scope all'ultimo SA (`E_PROFILO_ULTIMO_SUPER_ADMIN`); corretto con un secondo SA in fixture (azienda Z, mai attore) — stessa famiglia dei tre `ERRORE_FIXTURE` già a registro nella baseline scratch che chiamano quella funzione. Restano: commit, BE/FE (§5/§6), la decisione sul residuo del fondo fattura |
| **2026-09-15** (notte) | 🔧 **Sviluppo DB scritto, L1–L17.** ChangeSet `20260915-21` (L1) `-22` (L2) `-23` (L3) `-24` (L4) `-25` (L5a) `-26` (L5b) `-27` (L6) `-28` (L7) `-29` (L8) `-30` (L10) `-31` (L9a) `-32` (L9b) `-33`/`famiglie_documento_distinta.csv` (L11) `-34` (L12) `-35`/`fk_index_policy_vendite_contabili_numerazione.csv` (L14); append ai CSV `codici_errore`/`messaggi_errore` (ids 1072, 1073 — L13); pgTAP nuovo `pagamenti/test-distinta-numerazione-registro-v1.sql` (plan 19, L15) e cinque ritoccati (perimetro 19, correzione 15, sistemazioni 14, lotti 11, prefisso — L16); doc di L17 (scheda `vendite_contabili`, `famiglie_documento`, guida numerazione, tre schede di `script`, guida pagamenti). Il BB parallelo di Tid ha preso `20260915-36…46`: nessuna collisione. **Prova §4-bis.18 fatta** su dbdev come `titodb` (il migratore di dev), tutto in `BEGIN … ROLLBACK`: i 12 changeSet estratti + il render offline di 33/34/35 applicano puliti; il backfill risolve 5720 righe → sr 72, residue **2** (5730, 5869), l'`UPDATE` a mano le chiude → `NOT NULL` passa; registri `DIS-72`/`DIS-159` con `anno_nel_numero`; numerazione `DIS-PGTAPEF202-2026-0000001/2`, secchi 2025/2026 separati, codice fornito rispettato, riuso della madre entro l'emittente, livelli 0/1/4 con le frasi giuste, il risolutore legge la colonna, solo le tre madri inseriscono distinte e nessuna passa `codice`. pgTAP nella stessa transazione, **da owner** (RLS non esercitata): nuovo 17/19 (18/19 = RLS), correzione 15/15, sistemazioni 14/14, lotti 11/11, prefisso 6/6, perimetro 10/19 (i nove rossi sono tutti RLS); con `FORCE ROW LEVEL SECURITY` diagnostico sulle tre tabelle: nuovo **19/19**, perimetro rossi solo artefatti del FORCE. Sei guardrail statici a zero. **Cinque correzioni in più** al brief (§4-bis.19, seconda tabella): niente indice sull'emittente, quarto file rosso (`test-rls-vendite-contabili-lotti`), test 8 del perimetro verde nel valore, test 16 in forma `col_not_null`, **residuo** `fn_sync_contabili_fondo_fattura` con fattura fuori lotto (livello 3 → admin globale «tutti» rifiutato) da decidere con Tid. **Restano a Tid**: `make db-migrate` (si ferma su `-26`) → `UPDATE pagamenti.vendite_contabili SET emittente_soggetto_ruolo_id = 72 WHERE id IN (5730, 5869) AND emittente_soggetto_ruolo_id IS NULL;` → `make db-migrate` → `scripts/pgtap-baseline.sh pagamenti rls vendite`; poi BE-1..6 (rigenerare `error_policies_generated.py` e i messaggi di ripiego per i due codici) e FE-1..4 |
| **2026-09-15** (sera, chiusura) | ✅ **Tid conferma le tre scelte del piano** come da consiglio: livello 0 (SR non emittente → TECNICO), lotto strict (lotto non leggibile → TECNICO), `UPDATE … SET emittente = NULL` rifiutato dal `NOT NULL`. Il piano è completo; resta il via allo sviluppo. Ordine di scrittura: L1 → L14, L15, L16, L17; poi la prova di §4-bis.18; apply e baseline di Tid |
| **2026-09-15** (sera, seconda correzione di Tid) | «Anche un processo batch ha sempre un utente, e uno user ha sempre l'emittente»: vero dal 2026-09-05 (R-2, utenti tecnici per processo × azienda). Corrette tre frasi stantie (§3.2 riga del ruolo batch, §4-bis.6, §4 P-12). La derivazione **dal lotto** resta per una ragione del modello e non per la sessione mancante: il giro di massa dell'admin globale in modalità «tutti gli emittenti» produce lotti di N aziende con una sessione che non risolve nessun emittente. Il ramo strict è un `IF` che Tid può togliere (§4-bis.6) |
| **2026-09-15** (sera, dopo il piano) | **Deciso da Tid**: 5730 e 5869 si assegnano a mano a «Gestore Test pgTAP» (sr 72) con un `UPDATE` per `id` fra il primo stop di L5b e il secondo lancio del migrate (§2.6, §4-bis.5). Il changeSet resta fail-closed. Livello 0 e lotto strict (§4-bis.2, §4-bis.6) spiegati in chat, in attesa di conferma |
| **2026-09-15** (sera) | **Piano di sviluppo DB scritto** (§4-bis): 17 lotti, verificati sul modello vivo (doc auto-gen, `pg_policy`, `pg_trigger`, `pg_proc`, i CSV e i loader di `80_data`). Otto correzioni al brief (§4-bis.19), fra cui due mine di CI: il ramo «senza canale = di tutti» nelle policy vive di righe e lotti (`20260822-24`, `20260910-18`), e `20260831-03` che pretende **esattamente 4** famiglie ≠ FATTURA — un append al CSV base farebbe morire il migrate su un DB da zero, invisibile su dev. D4 diventa una funzione (`fn_get_emittente_distinta`) chiamata da trigger e madre, perché la chiave di riuso vuole l'emittente prima dell'INSERT. Nessun changeSet scritto; aperto a Tid: l'ok al piano, la sorte di 5730/5869, e le due scelte del piano marcate «TECNICO» (livello 0 e lotto strict) |
| **2026-09-15** | Analisi in chat su richiesta di Tid («la numerazione del codice distinta deve rientrare nella numerazione standard, prefisso-anno-progressivo con reset anno, le 3 righe numerate restano così»). Verificato: nessuno storico sulla distinta; ogni creatrice conosce l'emittente; il ramo «di tutti» non ha chiamanti. **D1** (sigla) e **D3** (RLS sulla riga) decise da Tid; D2, D4, D5, D6 proposte senza obiezione. Brief scritto; **nessun changeSet**. Aperto a Tid: la sorte di 5730 e 5869 (§2.6) prima dell'apply di P-2 |
