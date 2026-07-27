# Brief DB — Emissione fattura mirata per gruppo fatturabile + simmetria `fatturazione_immediata`

> **Tipo**: brief operativo per il **team DB** · **Target**: `dev/db-tid` ·
> **Data**: 2026-07-27 · **Owner**: Tid · **Stato**: 🟢 **PERIMETRO DB
> COMPLETO — applicato e testato** (agg. 2026-07-27). Fase B e Fase A chiuse,
> rifiniture incluse; nessuna voce di piano aperta. Restano: **commit della
> Fase A**, rigenerazione doc auto-gen, e il rientro schedulato **P6**.
> · **Priorità**: 🟠 MEDIA (abilita un'esigenza operativa reale; additivo,
> nessun dato a rischio).
>
> **Conseguenza per BE/FE**: il prerequisito DB **non è più bloccante**. I punti
> 3-6 del perimetro in [analisi-emissione-fattura-ondemand.md](analisi-emissione-fattura-ondemand.md)
> §8 possono partire, con il contratto di **§8-bis** di questo brief.
>
> **Come leggere questo brief**: §1-§5 descrivono **cosa serve**. §6 riporta le
> decisioni implementative **prese** dopo l'analisi critica del 2026-07-27 (con
> le alternative scartate e il perché). §9 è il **piano di sviluppo a step
> aggiornabili**, §10 il piano di **test pgTAP**, §11 il **registro di cosa è
> stato fatto** — con il consuntivo in testa. §4 «Fatti verificati» è il
> contesto rilevato sul codice/DB vivo.
>
> **Origine**: [analisi-emissione-fattura-ondemand.md](analisi-emissione-fattura-ondemand.md),
> decisioni Tid 2026-07-26/27.
>
> **Contesto**: non siamo in produzione ([[project_no_produzione_solo_sviluppo]])
> → breaking secchi ammessi.
>
> ~~**Conseguenza**: BE e FE **attendono** questo lavoro
> ([[feedback_be_fe_attende_prerequisiti_db]]).~~ → **attesa terminata il
> 2026-07-27**: il perimetro DB è completo, applicato e testato.
>
> ---
>
> **⚡ Stato in testa (aggiornare qui a ogni avanzamento)**
>
> | Fase | Contenuto | Stato |
> |---|---|---|
> | **B** — simmetria flag | colonna su ordini/contratti/DDT (**no consumi**, D-6) + push fn + presidio | ✅ **CHIUSA e COMMITTATA** (`49eed89d0`) — `20260727-01..09`, pgTAP verde (plan 20), doc aggiornata |
> | **A** — emissione mirata | chiave gruppo, persistenza criterio, 4 funzioni, colonna `area`, **3 viste** | ✅ **CHIUSA, rifiniture incluse** — `20260727-10..19` + seed CSV applicati; pgTAP 17+10+5 verdi; doc completa. ⏳ **da committare** |
> | **T** — pgTAP | file nuovi + adeguamento esistenti | ✅ **4/4 verdi, 52 asserzioni**: simmetria flag (20), emissione mirata (17), viste gruppi+riepilogo (10), guardrail area (5) |
> | **D** — doc | manual dbzero + guida fatturazione + contratto BE | ✅ **completa** — 9 file Fase B + 10 Fase A (4 manuali nuovi, 6 aggiornati) |
>
> Le due fasi erano **indipendenti**: B non dipendeva da A. Entrambe chiuse il
> **2026-07-27**, rifiniture A9 e A7-ter incluse.
>
> **Decisioni: nessuna aperta.** P1 (consumi esclusi), P2 (mappa `area`),
> P3 (pgTAP vs guard B5), P4/D-9 (chiave di gruppo = `uid`) e P5 (doc sorgente
> polimorfa) chiusi il 2026-07-27.
>
> **Cosa resta**, in ordine:
>
> 1. **commit della Fase A** (`20260727-10..19` + pgTAP + doc) e rigenerazione
>    doc auto-gen `dbzero` — a cura di Tid;
> 2. **P6** — rientro concordato sui 9 pgTAP rossi per `E_SORG_FORMATO`, di cui
>    3 non censiti nel backlog di
>    [brief-db-bonifica-pgtap-sorgente-polimorfa](brief-db-bonifica-pgtap-sorgente-polimorfa.md)
>    (§10.4). **Non sono regressioni di questa slice**: verificato uno per uno;
> 3. **BE/FE** — punti 3-6 del perimetro, con il contratto di §8-bis.

---

## 1. Cosa serve, in una frase

Poter **fatturare su richiesta un sottoinsieme preciso di lavoro** — un singolo
documento sorgente, o gli oneri manuali di una commessa — invece che l'intero
mese, e poter **elencare** questi sottoinsiemi per mostrarli all'operatore.

---

## 2. I casi d'uso (concreti)

**UC-1 — «fattura questo preventivo, adesso»**
Il preventivo PRV-0012 del cliente Rossi è stato accettato oggi. L'operatore
vuole la fattura subito, **senza** trascinare dentro il contratto CTR-0007 dello
stesso cliente, che è nella stessa commessa e nello stesso mese.

**UC-2 — «fattura questa penale, adesso»**
Sulla commessa #42 è stato caricato un onere da 500 € (porta oneri). Non
appartiene ad alcun documento. L'operatore deve poterlo **vedere** e
**fatturare** deliberatamente, non aspettare che il giro mensile lo raccolga.

**UC-3 — «mostrami cosa posso fatturare»**
Prima di agire, l'operatore deve vedere l'elenco di ciò che è fatturabile nel
mese, raggruppato in unità su cui può decidere, con quante righe e quanto valore
ciascuna pesa.

**UC-4 — «questo cliente va sempre fatturato subito»**
Un ordine (non solo un preventivo) deve poter essere marcato come *fatturazione
immediata*, così da essere instradato automaticamente sulla corsia veloce.

---

## 3. Requisiti funzionali

### PARTE A — Emissione mirata

#### A1. Il concetto di **gruppo fatturabile**

L'unità su cui l'operatore decide **non è la commessa** (contiene lavoro di
origini diverse) e **non è sempre un documento** (gli oneri non ne hanno).

Un **gruppo fatturabile** è:

- un **documento sorgente** — preventivo, ordine, contratto, DDT, consumo
  (identificato da tipo + identificativo del documento); **oppure**
- l'insieme delle **righe manuali/oneri di una commessa** — righe senza
  documento sorgente, il cui unico contenitore naturale è la commessa.

Serve che il DB sappia esprimere **entrambe** le forme come criterio di
selezione. È il requisito centrale del brief.

#### A2. Fatturare un perimetro ristretto a uno o più gruppi

Deve essere possibile eseguire il giro di fatturazione limitandolo a **uno o più
gruppi fatturabili** scelti, ottenendo che:

1. vengano fatturate **solo** le righe di quei gruppi;
2. **nessun'altra riga** dello stesso cliente/commessa/mese venga trascinata
   dentro, nemmeno se idonea;
3. le righe non richieste restino **integre e ancora fatturabili** dopo
   l'operazione (nessun effetto collaterale sul loro stato);
4. l'operazione si fermi allo stato **EMESSA** (la numerazione resta un atto
   separato) — coerente col gate fiscale già in vigore.

**Multi-selezione**: il criterio deve accettare **N gruppi in un colpo**, non
solo uno ([[feedback_concentrico_no_yagni]]): l'operatore selezionerà
ragionevolmente più documenti insieme.

#### A3. Elencare i gruppi fatturabili

Serve poter **ottenere l'elenco** dei gruppi fatturabili di un perimetro
(mese di competenza, eventualmente ristretto per cliente/utility/emittente), con
per ciascun gruppo almeno:

| Informazione | Perché serve |
|---|---|
| identificativo del gruppo | per poterlo poi passare come criterio di A2 |
| tipo di gruppo (quale documento, oppure «oneri di commessa») | etichetta a video |
| riferimento leggibile (numero/codice documento, o commessa) | l'operatore lo riconosce |
| cliente | colonna di lista |
| **numero di righe/attività** | dice il *peso* di ciò che si sta per fatturare |
| **valore** | idem |
| commessa di appartenenza | per l'aggancio alle viste esistenti |

⚠️ **Oggi questo elenco non esiste in nessuna forma**: la discovery attuale
lavora a livello di raggruppamento del lotto, non di gruppo fatturabile. È il
dato che alimenta la nuova lista del cockpit.

#### A4. Ripetibilità

Due emissioni mirate **successive** sullo stesso cliente, stesso mese, stessi
parametri di perimetro ma **gruppi diversi** (es. prima il preventivo, poi il
contratto) devono poter **convivere**: la seconda non deve fallire né
interferire con la prima.

> ~~Questo è il punto tecnicamente più delicato: oggi il contenitore di
> fatturazione è identificato da una combinazione che non include il gruppo,
> quindi due giri mirati sullo stesso perimetro ricadrebbero sullo stesso
> contenitore.~~
>
> ✅ **RETTIFICA 2026-07-27 — il timore era infondato** (fatto F7): non esiste
> alcun vincolo di unicità dimensionale su `fatturazione_lotti`, e
> `fn_get_or_create_lotto` senza `p_lotto_id`/`p_lock_batch_id` **crea sempre un
> lotto nuovo**. Due giri mirati successivi producono già oggi due lotti
> distinti: **A4 non richiede lavoro dedicato**, basta non introdurre un
> vincolo che oggi non c'è. Resta però da coprire con test (G7).
>
> ⚠️ **Il rischio vero è un altro e sta a valle** (fatto F8): il lotto è
> ripetibile, ma il *contenuto* no — il secondo giro rastrellerebbe le attività
> fatturabili residue del primo gruppo. Vedi G12 e D-2/D-3 in §6.

#### A5. Aggregati per la riga di totali *(rifinitura, priorità bassa)*

Utile poter avere, insieme all'elenco A3, i **totali del perimetro** (numero
gruppi, numero attività, valore complessivo) per mostrare una riga di
riconciliazione. **Voce separabile**: se complica, si rimanda senza bloccare il
resto.

### PARTE B — Simmetria di `fatturazione_immediata`

#### B1. Il fatto

Il flag decide su quale corsia finisce il lavoro:

| Flag | Corsia | Arriva a | Cadenza |
|---|---|---|---|
| `true` | immediata | **DEFINITIVA** (numera da sola) | ogni 2 min |
| `false` | differita | **EMESSA** | mensile |

Ma **il dato esiste solo per i preventivi**: le altre sorgenti restituiscono un
valore fisso `false` al push. Di fatto **solo un preventivo può essere fatturato
subito**, e non per una scelta di dominio ma per un buco di modello.

#### B2. Cosa serve

Che **ordini, contratti e DDT** possano portare l'indicazione «questo va
fatturato subito», e che tale indicazione **arrivi effettivamente** al push e
quindi all'instradamento in corsia.

> ✅ **Perimetro chiuso il 2026-07-27**: i **consumi restano esclusi** (D-6). Un
> consumo è una misura, non un accordo commerciale: la corsia la decide il
> contratto che lo governa.

Nessun'altra modifica: la propagazione alla commessa e il funzionamento delle
corsie **funzionano già** e non vanno toccati.

#### B3. Vincolo semantico da preservare

L'indicazione si stabilisce **prima** che il lavoro entri in commessa. Non deve
diventare un attributo modificabile su lavoro già lavorato: il caso «cambio idea
dopo» è coperto dall'emissione mirata (Parte A), non dal flag.

Se ritenete utile un presidio che lo renda esplicito (impedire la modifica su
documento già pushato), è benvenuto: meglio una regola scritta che una
disciplina affidata alle persone.

---

## 4. Fatti verificati (contesto, per evitarvi l'indagine)

Rilevati sul codice/DB vivo il 2026-07-26/27, **rivisti e integrati il
2026-07-27** con l'analisi critica (§4-bis). Sono **fatti**, non indicazioni
implementative.

1. **La traccia del documento d'origine esiste già riga per riga** su
   `vendite.commesse_attivita` (`sorgente_tipo_id` + `sorgente_uid`, quest'ultimo
   **TEXT** per la convenzione `key_selector`: `uid` per preventivo/offerta,
   `id::text` per il resto — [[reference_sorgente_polimorfa_key_selector]]). Il
   CHECK `chk_commesse_attivita_sorgente_pair` garantisce che la coppia sia
   **tutta NULL o tutta valorizzata**: il gruppo è quindi sempre ben definito.
2. **A valle il legame si assottiglia**: su `vendite.attivita_fatturabili`
   `sorgente_tipo_id`/`sorgente_uid` sono **rioccupati** (sorgente `COMMESSA` +
   `sorgente_uid` uuid = hash md5 della `segment_key`), resta
   `sorgente_origine_tipo_id` = il **tipo** di origine ma **non
   l'identificativo**. ⚠️ **Precisazione importante**: sopravvive però
   `attivita_fatturabili.commessa_attivita_id` **NOT NULL** → l'identità del
   documento **è recuperabile con un join**, non è perduta. Questo cambia la
   decisione «serve una colonna nuova su AF?» → vedi D-2 in §6.
3. **Gli oneri sono sourceless per progetto**: la porta oneri crea righe con
   sorgente nulla e `segment_key` con prefisso `MAN:<commessa_id>:<n>`,
   discriminate da `tipo_movimento = 'ONERE'`. È **voluto** (brief porta oneri) e
   non va cambiato: è la ragione per cui il criterio deve avere due forme (A1).
4. **La commessa non isola il documento**: è multi-sorgente (`ROOT` + N
   `COLLEGATO`), e un documento è legato a **una sola commessa per sempre**.
   Quindi «filtra per commessa» **non** soddisfa UC-1.
5. **`tipo_doc_fiscale_id` sta sulla RIGA** (`commesse_attivita`), non sulla
   testata del documento. Normalmente tutte le righe di un documento lo
   condividono (deriva dalla configurazione della sorgente), ma **non c'è nulla
   che lo imponga**: se cambia la configurazione fra due push, un singolo gruppo
   può avere righe con tipo doc diverso → **finisce in lotti diversi** (la terna
   di lotto include il tipo doc). Conseguenza sul contratto BE: §8.
6. Il flag `fatturazione_immediata` è oggi **colonna reale solo su preventivi**;
   le altre sorgenti lo espongono nel contratto ma con valore costante `FALSE`.

### 4-bis. Fatti aggiunti dall'analisi critica del 2026-07-27

Rilevati leggendo il codice vivo. **Correggono o completano** quanto sopra e
sono la ragione delle decisioni di §6.

- **F7.** **⚠️ Il nodo di §A4 (ripetibilità) NON esiste come descritto.**
  `vendite.fatturazione_lotti` ha UNIQUE **solo** su `codice` (generato da
  sequenza via `script.fn_generate_codice`) e su `lock_batch_id` (default
  `uuidv7()`): **nessun vincolo sulla combinazione dimensionale**
  (competenza, tipo_doc, utility, BA, emittente).
  `fn_get_or_create_lotto` fa «get» **solo** se riceve `p_lotto_id` o
  `p_lock_batch_id`; altrimenti il CASO 3 **crea sempre un lotto nuovo**. Il
  driver non passa mai `lock_batch_id`
  (`fatturazione_driver_service.py`, chiamata a `run_lotto_pipeline_until_done`).
  → **Due giri mirati successivi producono già oggi due lotti distinti.** G7 è
  sostanzialmente gratuito e il punto aperto §6.1 dell'analisi è **chiuso: nessun
  conflitto di identità.**
- **F8.** **⚠️ La vera falla è sul SELECT delle attività fatturabili.**
  `fn_select_attivita_fatturabili` filtra su
  `(approvato, non fatturato, non sospesa, non lockata, posticipa_al,
  competenza ≤ M, tipo_doc, BA, utility, emittente, valuta, area)` e blocca con
  `FOR UPDATE ... SKIP LOCKED`: **non ha alcuna nozione di sorgente/gruppo**.
  Quindi un lotto mirato al gruppo A **rastrella qualunque AF già esistente e
  non ancora consumata** del gruppo B nello stesso perimetro. Le AF residue
  esistono in casi reali: giro precedente interrotto fra pull e generazione
  righe, reset-a-bozza, giro schedulato che ha fatto pull ma non ha completato.
  → **Filtrare solo il pull non basta**: G2/G3 si romperebbero *per perdita*.
  È il requisito tecnico centrale, aggiunto come **G12**.
- **F9.** **⚠️ Il criterio deve viaggiare SUL LOTTO, non sulla chiamata.**
  `PipelineStepExecutor` riceve solo `lotto_id` e ricostruisce tutto dal
  `LottoContext` (= riga del lotto):
  `_handle_pull_attivita_da_commessa_task` chiama `fn_list_commesse_emittibili`
  con i campi del contesto, e `run_select_attivita_task`
  (`pipeline_repository.py`) passa a `fn_select_attivita_fatturabili` **solo**
  valori del contesto + i params JSON della pipeline. **I parametri della
  chiamata API non arrivano agli step.** Se il criterio non è **persistito sul
  lotto**, il design non parte.
  Corollario non banale: i verbi **Rerun step / Avanza step** del `LottoDrawer`
  ri-eseguono lo step su un lotto esistente → senza persistenza
  **allargherebbero silenziosamente il perimetro** di un lotto mirato. Aggiunto
  come **G11**.
- **F10.** **⚠️ Il pull è per-commessa e «tutto o niente».**
  `fn_emit_attivita_fatturabili_da_commessa(p_commessa_id, p_only_approved,
  p_dry_run)` cicla **tutte** le righe `NON_EMESSA` (+ `APPROVATA` se
  `p_only_approved`) della commessa, crea/aggiorna l'AF e mette
  `stato_emissione = 'EMESSA'` su **ognuna**. Senza filtro *dentro* la
  funzione, un giro mirato porta fuori dalla card «Da emettere» anche le righe
  del gruppo B, lasciandole come AF orfane: **A2.3 violato**. Aggiunto come
  **G13**.
- **F11.** **⚠️ Parte B — accoppiamento nascosto con `prezzo_bloccato`.**
  In `fn_list_preventivi_da_pushare` il flag fa **doppio lavoro**:
  `prezzo_bloccato = COALESCE(p.fatturazione_immediata, false)`. Nelle altre
  sorgenti lo stesso slot è una costante indipendente (es. `TRUE` su ordini).
  → «basta leggere la colonna» **non è simmetrico**: si estende **solo** la
  semantica di *instradamento*; `prezzo_bloccato` resta con la sua regola
  per-sorgente. Da scrivere nel commento delle funzioni, altrimenti qualcuno
  copierà la riga del preventivo e cambierà silenziosamente il pricing.
- **F12.** **Il presidio B3 non è un «di più»: senza, il FE espone un campo inerte.**
  `vendite.commesse_sorgenti` ha UNIQUE **globale** su
  `(sorgente_tipo_id, sorgente_uid)` e il flag è **parte della chiave di dedup**
  di `fn_get_or_create_commessa`. Dopo il push, modificare il flag **non sposta
  nulla**: è già inerte, può solo ingannare l'operatore. → B3 promosso a
  **obbligatorio** (D-7).
- **F13.** **Aggiungere un parametro a una funzione `RETURNS TABLE` richiede DROP.**
  Con l'overload a 3 e a 4 argomenti entrambi presenti e default in coda, le
  chiamate che omettono l'argomento falliscono con *function is not unique*.
  Serve `DROP FUNCTION IF EXISTS` della vecchia firma nello stesso changeSet
  ([[feedback_pg_returns_table_drop_required]]). Superficie d'impatto misurata:
  **16 file pgTAP** e **5 moduli BE** chiamano le 4 funzioni interessate.
- **F15.** **`sorgente_uid` non ha una convenzione sola: dipende da CHI scrive.**
  Rettificato il 2026-07-27 dopo lettura della guida
  [sorgente-polimorfa](../../guide/sorgente-polimorfa.md) (una prima stesura di
  questo punto era **sbagliata**: dava per non-canonica anche
  `commesse_sorgenti`).

  | Dove | Tipo | Contenuto reale | Chi lo garantisce |
  |---|---|---|---|
  | `pratiche_sorgenti.sorgente_uid` | TEXT | chiave **canonica** per `key_selector` | guard polimorfo + BE |
  | `commesse_sorgenti.sorgente_uid` | TEXT | chiave **canonica** per `key_selector` (`id::text` per ordini/contratti/DDT) | **`fn_link_commessa_sorgente` normalizza in scrittura** |
  | `commesse_attivita.sorgente_uid` | TEXT | **quello che passa il push, cioè `<tabella>.uid::text` per tutte le sorgenti** | **nessuno** — `fn_upsert_commessa_attivita` scrive grezzo |
  | `attivita_fatturabili.sorgente_uid` | UUID | `md5(segment_key)` con sorgente `COMMESSA` | meccanismo interno, non polimorfo |
  | `ddt.sorgente_uid`, `resi.sorgente_uid` | UUID | uid del padre | colonna tipizzata diretta, fuori dal meccanismo |

  **Il punto che conta per questa slice**: `commesse_sorgenti` è canonica,
  `commesse_attivita` **no**. Sono due tabelle vicine, scritte nello stesso
  push, che per lo stesso documento contengono **valori diversi**
  (`id::text` la prima, `uid::text` la seconda) quando `key_selector = 'id'`.

  **Conseguenze operative**:

  - il guard B5 interroga `commesse_sorgenti` → risolve la chiave via
    `key_selector`, come fa `fn_link_commessa_sorgente` (corretto in corso
    d'opera: la prima stesura usava `uid::text` e non avrebbe **mai** trovato
    il link — no-op silenzioso);
  - la chiave di gruppo di **D-1 legge `commesse_attivita`**, quindi oggi
    dovrebbe usare `uid::text`. → **decisione DA PRENDERE**, vedi D-9.

  ⚠️ **Errore nella documentazione esistente**:
  [brief-db-guard-sorgente-polimorfa.md](../work-done/brief-db-guard-sorgente-polimorfa.md)
  §1d — la tabella «i tre usi di sorgente_uid NON vanno confusi» attribuisce a
  `commesse_attivita.sorgente_uid` il contenuto «hash md5(segment_key)», che è
  invece di `attivita_fatturabili.sorgente_uid`. È esattamente la riga che
  serve a questa slice, ed è quella sbagliata. Da correggere in quel brief.

- **F14.** **`vw_dash_competenza_attivita` è già l'ancora giusta per l'elenco A3.**
  È `security_invoker=on`, applica già `script.fn_get_emittenti_scope_sr_ids`
  (vincolo 2 gratis), è a grana **riga di commessa**
  (`commessa_attivita_id`) e calcola già `stadio` (`DA_EMETTERE`, …),
  `valore`, `cliente_display`, `commessa_codice`. Derivare A3 da qui garantisce
  **per costruzione** che i conteggi coincidano con la card (G8); una query
  parallela divergerebbe.

---

## 5. Vincoli non negoziabili

1. **Retro-compatibilità totale.** Il giro schedulato (corsie immediata e
   differita) e il verbo di massa «fattura il mese» **non devono cambiare
   comportamento**. Assenza di criterio = esattamente ciò che accade oggi.
2. **Scope emittente invariato.** Nessun allentamento del perimetro RLS: un
   operatore non deve poter raggiungere, tramite i nuovi criteri, righe che oggi
   non vede.
3. **Nessun effetto collaterale sulle righe non richieste** (A2.3): ciò che non
   si è chiesto di fatturare deve restare esattamente com'era.
4. **Il gate fiscale resta.** L'emissione mirata si ferma a EMESSA; la
   numerazione è un atto separato, con il suo permesso.

---

## 6. Decisioni implementative — PRESE (2026-07-27)

Erano «decisioni che spettano a voi»; l'analisi critica del 2026-07-27 le ha
chiuse. Ognuna riporta **cosa si è deciso**, **perché**, e **cosa si è
scartato** — così una revisione futura sa cosa rimettere in discussione.

### D-1 · Forma della chiave di gruppo → **una sola stringa TEXT**

`gruppo_key TEXT`, costruita da un'unica funzione di verità
`vendite.fn_build_gruppo_fatturabile_key(p_sorgente_tipo_id, p_sorgente_uid,
p_commessa_id)`:

| Caso | Chiave |
|---|---|
| riga con documento sorgente | `'<codice_interno_sorgente>:<sorgente_uid>'` (es. `ORDINE_VENDITA:9f3a…`) |
| riga sourceless (oneri, F3) | `'MAN:<commessa_id>'` |

**Perché**: una sola colonna scalare si passa come `text[]` per la
multi-selezione (A2), si mostra come identificativo nell'elenco (A3) e si
confronta senza mapping fra DB, BE e FE — chiudendo il rischio che «la chiave
dell'elenco» e «la chiave del criterio» divergano (G8). Il prefisso per
`codice_interno` (non per `codice`) segue la regola già adottata in
`fn_emit_attivita_fatturabili_da_commessa` (rev 2026-06-28): il codice interno è
immutabile.

**Scartato**: criterio a coppia `(sorgente_tipo_id BIGINT, sorgente_uid TEXT)` +
terzo campo per gli oneri → tre colonne da propagare in quattro funzioni e un
array di record da costruire lato BE, per zero valore aggiunto.

**Nota**: la chiave **non** va derivata a stringhe da `segment_key` (che è
`ORD:<uid>:R:<n>`, `MAN:<commessa>:<n>`, …). I prefissi lì sono una convenzione
di leggibilità per-sorgente, non un contratto: derivarne il gruppo con
`split_part` creerebbe un accoppiamento fragile.

⚠️ **`<sorgente_uid>` è l'UID, non l'id** — deciso in **D-9** (2026-07-27).
Quello che sta in `commesse_attivita.sorgente_uid` è `<tabella>.uid::text` per
**tutte** le sorgenti, anche dove `config.sorgenti.key_selector` dice `id`
(fatto **F15**). La chiave di gruppo si ancora a **quella** forma, che è ciò che
si sta filtrando. Ancorarla a `key_selector` produrrebbe un filtro che non
filtra, in silenzio.

### D-2 · Dove filtrare le AF → **join su `commesse_attivita`, nessuna denormalizzazione**

`fn_select_attivita_fatturabili` filtrerà unendo `attivita_fatturabili` a
`vendite.commesse_attivita` via `commessa_attivita_id` (NOT NULL, fatto F2) e
applicando la chiave di D-1.

**Perché**: nessuna colonna nuova su una tabella calda, nessun backfill, nessuna
possibilità di drift fra il valore memorizzato e la sorgente ([[feedback_docs_first]]
— la logica non si duplica). Il join è su FK indicizzata; `FOR UPDATE OF a` con
`SKIP LOCKED` resta valido perché blocca solo l'alias `a`.

**Scartato (per ora)**: propagare `gruppo_key` come colonna su
`attivita_fatturabili`, sul modello di `tipo_movimento` (rev 2026-07-17). È la
via da riaprire **solo** se un `EXPLAIN` sul volume reale mostra che il join
pesa: allora si aggiunge la colonna + indice, mantenendo `fn_build_…` come unica
fonte del valore.

### D-3 · Dove vive il criterio → **tabella figlia del lotto**, non `meta` jsonb

Nuova `vendite.fatturazione_lotti_gruppi (lotto_id, gruppo_key, …)`.

**Perché** (fatto F9): gli step leggono solo il lotto. Serve persistenza, e
serve che sia **relazionale**: `fn_select_attivita_fatturabili` costruisce SQL
dinamico e un `JOIN`/`= ANY(...)` su tabella è naturale e indicizzabile. In più
il criterio diventa **auditabile** (audit + `tx_id` come le altre) e il rerun
di uno step riproduce lo stesso perimetro (G11).

**Scartato**: `fatturazione_lotti.meta` jsonb. È già il canale di *configurazione*
della pipeline (`fatturazione_immediata`); metterci dentro dati di *perimetro*
sovraccarica la semantica e rende il filtro un `jsonb` da destrutturare dentro
SQL dinamico.

**Convenzione**: assenza di righe in `fatturazione_lotti_gruppi` per un lotto =
**nessuna restrizione** = comportamento odierno (vincolo 1, G1).

### D-4 · Forma dell'elenco A3 → **viste derivate da `vw_dash_competenza_attivita`**

Due viste, sul modello già in uso per il backlog
(`vw_dash_backlog_documenti` + `vw_dash_backlog_riepilogo`):

- `vendite.vw_dash_competenza_gruppi` — una riga per gruppo fatturabile;
- `vendite.vw_dash_competenza_gruppi_riepilogo` — gli aggregati di A5.

**Perché** (fatto F14): la vista di partenza è già `security_invoker=on` e già
applica lo scope emittente → **vincolo 2 e G14 gratis**; è già a grana riga di
commessa e calcola già `stadio` e `valore` → **G8 per costruzione**. Costruire
una query parallela significherebbe due formule che divergono nel tempo (stessa
lezione di [[project_riepilogo_iva_snapshot_vs_live]]).

⚠️ **Prerequisito**: `vw_dash_competenza_attivita` **non espone oggi**
`sorgente_tipo_id`/`sorgente_uid`/`tipo_movimento` → va estesa (step A6). È un
`CREATE OR REPLACE VIEW`: ricordarsi di **ri-specificare `WITH
(security_invoker=on)`**, che PostgreSQL azzera altrimenti.

### D-5 · Riferimento leggibile del gruppo → **colonna `area` su `config.sorgenti`** ✅ *(decisa da Tid, 2026-07-27)*

L'elenco A3 vuole «PRV-0012», non la chiave. Il numero leggibile esiste già in
`vendite.vw_dash_fatturazione_documenti`, che espone
`(area, documento_id, documento_uid, codice)` per tutte le sorgenti.

**Il disallineamento**: quella vista etichetta i documenti per `area`
(`PREVENTIVI`, `ORDINI`, `CONTRATTI`, `DDT`, `OFFERTE`, `COMMESSE`), il gruppo
per `sorgente_tipo_id` (`PREVENTIVO`, `ORDINE_VENDITA`, …). Due vocabolari per
le stesse cose.

⚠️ **Fatto rilevato durante la decisione**: il vocabolario `area` **non esiste
come dato**. La stringa è scritta a mano dentro ciascuna delle **6 viste
per-sorgente** (`'PREVENTIVI'::varchar AS area` in
`vw_dash_fatturazione_preventivi`, e così via). Non stiamo scegliendo dove
*leggere* una mappa esistente: stiamo scegliendo se **crearla**.

**Deciso: opzione (a)** — nuova colonna `area` su `config.sorgenti`, accanto a
`codice_interno`, `codice`, `categoria`, `target_table`, `key_selector`, che
descrivono già ogni sorgente. La mappa vive in **un solo posto** e chiunque ne
abbia bisogno domani la trova lì.

**Perché**: la regola di casa estrae un valore ripetuto alla **seconda**
occorrenza ([[feedback_regola_del_2_estrai_bb]]); qui siamo a **sei**. Non si
aggiunge lavoro, si raccoglie un disordine già presente — stessa famiglia di
problema di `analisi-hardcoded-codice` (rev 2026-06-28, che ha spostato la
risoluzione delle sorgenti su `codice_interno` immutabile).

**Scartate**:

- (b) traduzione scritta dentro la nuova vista → resta nascosta lì; al secondo
  consumatore viene copiata e da lì in poi le copie divergono;
- (c) rinvio (esporre il codice grezzo in prima consegna) → accettabile come
  ripiego, ma non necessario visto il costo di (a).

**Mappa da seedare** (10 sorgenti, 6 con area; le altre restano NULL perché non
sono documenti sfogliabili):

| `codice_interno` | `area` |
|---|---|
| `PREVENTIVO` | `PREVENTIVI` |
| `ORDINE_VENDITA` | `ORDINI` |
| `CONTRATTO` | `CONTRATTI` |
| `DDT_VENDITA` | `DDT` |
| `OFFERTA_COMMERCIALE` | `OFFERTE` |
| `COMMESSA` | `COMMESSE` |
| `ATTIVITA`, `ATTIVITA_CONSUMI`, `FATTURA`, `RESO_VENDITA` | `NULL` |

**Perimetro**: la colonna + il seed sono **obbligatori** (step A7-bis, prerequisito
di A8). La **bonifica delle 6 viste** che oggi scrivono il letterale è una
**rifinitura separata** (step A7-ter): utile, ma non blocca la consegna e tocca
viste già in uso dalle dashboard.

### D-6 · Flag `fatturazione_immediata` sui consumi → **NO** ✅ *(confermato da Tid, 2026-07-27)*

Si estende a **ordini, contratti, DDT**. **Non** ai consumi.

**Perché**: un consumo è una lettura, non un accordo commerciale; la scelta di
corsia appartiene al contratto che lo governa, non alla singola misura. Metterci
un flag creerebbe due luoghi dove decidere la stessa cosa. In
`fn_list_consumi_da_pushare` la costante `FALSE` resta, ma va **commentata come
scelta di dominio**, non lasciata sembrare una dimenticanza.

> Questa decisione si discostava da [analisi-emissione-fattura-ondemand.md](analisi-emissione-fattura-ondemand.md)
> §5.3, che diceva «tutte le sorgenti (… consumi)». ✅ **Confermata da Tid il
> 2026-07-27: sui consumi NO.** Il perimetro della Fase B è quindi definitivo:
> ordini, contratti, DDT. Reversibile a costo basso: se domani servisse, la
> colonna si aggiunge con lo stesso pattern di B1.

### D-7 · Presidio di B3 → **obbligatorio, non opzionale**

Guard su `UPDATE OF fatturazione_immediata`: se il documento ha già una riga in
`vendite.commesse_sorgenti`, la modifica è respinta.

**Perché** (fatto F12): dopo il push il flag è **già inerte** — non può spostare
righe. Senza guard, il FE (punto 5 del perimetro) esporrà un campo editabile che
non produce alcun effetto: il peggiore dei mondi, perché *sembra* funzionare.
Meglio una regola scritta che una disciplina affidata alle persone.

### D-8 · Il lotto mirato **non** viene forzato per billing account

`billing_account_id` sul lotto resta **NULL** anche nell'emissione mirata: la
segregazione la fa il criterio-gruppo, e la testata fattura è comunque per
cliente dentro il lotto (`fatture_righe_service._build_group_key`). Selezionare
gruppi di clienti diversi produce **una fattura per cliente** nello stesso
lotto, che è il comportamento corretto.

### D-9 · Su quale forma di `sorgente_uid` si ancora la chiave di gruppo → **l'`uid`, come in `commesse_attivita`** ✅ *(decisa da Tid, 2026-07-27)*

Emersa dal fatto **F15**: `commesse_sorgenti` contiene la chiave **canonica**
(`id::text` dove `key_selector='id'`), `commesse_attivita` contiene invece
**l'uid grezzo** passato dal push, per tutte le sorgenti. Nessuno normalizza la
seconda.

La chiave di gruppo (D-1) si legge da **`commesse_attivita`**, quindi la forma
andava decisa esplicitamente. **Deciso: opzione (a)** — la chiave usa l'`uid`,
cioè la forma già presente in quella tabella.

| | Cosa si fa | Pro | Contro |
|---|---|---|---|
| **(a)** ✅ **scelta** | La chiave di gruppo usa la forma **presente in `commesse_attivita`**: `<codice_interno>:<sorgente_uid così com'è>` = l'`uid` | funziona subito, zero rischio, nessun dato da toccare | perpetua la divergenza: due tabelle sorelle con chiavi diverse per lo stesso documento |
| **(b)** | **Normalizzare `commesse_attivita.sorgente_uid`** come fa `fn_link_commessa_sorgente` (in `fn_upsert_commessa_attivita`) + bonifica dei dati esistenti | una sola convenzione in tutto il modello; il guard polimorfo diventa agganciabile anche qui | tocca il percorso di push, richiede bonifica dati, va fuori dal perimetro di questa slice |

**Raccomandazione: (a)** — e non solo per convenienza. Verificato il
2026-07-27 che la convenzione di `commesse_attivita` ha **già consumatori vivi**:
`vw_dash_fatturazione_contratti` e `vw_dash_fatturazione_documenti` fanno
`JOIN ... AND ca.sorgente_uid = c.uid::text`. Normalizzare la colonna
**romperebbe quei join**. Quindi (b) non è «più pulito a costo zero»: è una
bonifica che tocca push, dati e viste di dashboard, per un beneficio solo
estetico. La forma va **documentata** nel `COMMENT` di
`fn_build_gruppo_fatturabile_key`, non cambiata.

**Il terzo argomento, emerso in fase di decisione**: il riferimento leggibile
di D-5 si aggancia a `vw_dash_fatturazione_documenti`, che è indicizzata per
`documento_uid` = `<tabella>.uid::text` per **tutte** le sorgenti (verificato su
ordini, contratti, preventivi, DDT). Con la forma `uid` il join è
un'uguaglianza diretta (`d.documento_uid = ca.sorgente_uid`); con la forma `id`
servirebbe normalizzare la colonna per ottenerlo e poi **ri-tradurre all'uid**
per fare questo join — lavoro in più per tornare al punto di partenza.

**Tre argomenti indipendenti, stessa direzione**:

1. la chiave **non esce mai** dal mondo di `commesse_attivita` (produttore A8 e
   consumatori A3/A4/A5/A6 leggono tutti quella tabella): non deve combaciare
   con `commesse_sorgenti`, non si incontrano mai;
2. normalizzare romperebbe i join vivi delle dashboard;
3. il riferimento leggibile si aggancia direttamente all'`uid`.

L'unico vantaggio della forma `id` è estetico (chiave più corta, convenzione
unica nel modello) e costa una bonifica su push, dati e viste.

✅ **Documentazione già corretta** (2026-07-27): manuale di `commesse_attivita`
(sezione dedicata), guida `sorgente-polimorfa` §4a, e §1d di
`brief-db-guard-sorgente-polimorfa` (che era **errato**).

**Vincolo per lo step A1**: il `COMMENT` di `fn_build_gruppo_fatturabile_key`
deve dire **quale forma** usa e **perché**, così nessuno la "corregge" in
futuro per farla assomigliare a `commesse_sorgenti`.

⚠️ Qualunque sia la scelta, la chiave **non** va costruita "per analogia" con
`commesse_sorgenti`: sono due convenzioni diverse e la somiglianza dei nomi è
proprio ciò che induce l'errore.

---

---

## 7. Garanzie attese a fine lavoro

Non «come testare», ma **cosa deve risultare vero**. Da coprire con pgTAP.

| # | Deve essere vero | Origine |
|---|---|---|
| G1 | Senza criterio, il risultato è **identico** a oggi (non-regressione del giro schedulato) | iniziale |
| G2 | Chiedendo il documento A, vengono fatturate **solo** le righe di A | iniziale |
| G3 | Se la commessa contiene anche il documento B, le righe di B restano **intatte e ancora fatturabili** | iniziale |
| G4 | Chiedendo gli **oneri** di una commessa, vengono fatturate solo quelle righe (e sono raggiungibili, cioè non invisibili al criterio) | iniziale |
| G5 | Chiedendo più gruppi insieme, vengono fatturati **tutti e soli** quelli | iniziale |
| G6 | Un criterio che non corrisponde a nulla → **zero righe, nessun errore** | iniziale |
| G7 | Due emissioni mirate successive sullo stesso cliente/mese con gruppi diversi → **entrambe riescono**, nessuna interferenza | iniziale |
| G8 | L'elenco A3 mostra **sia** i documenti **sia** gli oneri, e i suoi conteggi/valori corrispondono a ciò che l'emissione poi fattura | iniziale |
| G9 | Un ordine/contratto/DDT marcato «fatturazione immediata» viene instradato sulla corsia immediata (B) | iniziale |
| G10 | Documenti con flag diverso, stesso cliente/utility/periodo → restano su corsie separate (invariante attuale preservato) | iniziale |
| **G11** | **Rerun / Avanza step** su un lotto mirato **non allarga il perimetro**: il criterio è persistito, non ricalcolato | F9 |
| **G12** | Un giro mirato **non consuma AF pre-esistenti fuori dai gruppi richiesti** (residui di giri precedenti, reset, giro schedulato interrotto) | F8 |
| **G13** | Le righe `commesse_attivita` non richieste restano `stato_emissione = 'NON_EMESSA'` (non solo «fatturabili»: proprio non toccate) | F10 |
| **G14** | Una chiave di gruppo **fuori dallo scope emittente** dell'operatore → zero righe sia nell'elenco sia nell'emissione (vincolo 2 verificato, non solo dichiarato) | vincolo 2 |
| **G15** | Un gruppo con righe di **tipo doc fiscale diverso** produce N lotti, e **tutti** vengono restituiti al chiamante | F5 |
| **G16** | L'aggiunta della colonna flag **non cambia la corsia dei documenti già esistenti** (backfill `false` = comportamento odierno) | F11 |
| **G17** | Il flag **non è modificabile** su un documento già pushato in commessa (presidio D-7) | F12 |
| **G18** | Estendere il flag **non altera `prezzo_bloccato`** su ordini/contratti/DDT | F11 |

---

## 8. Contratto atteso per BE/FE

Al termine il BE deve poter chiedere:

- *«dammi i gruppi fatturabili del mese M»* (con eventuale restrizione
  cliente/utility/emittente) → per costruire la lista del cockpit;
- *«fattura i gruppi X, Y»* → e ottenere che vengano fatturati solo quelli,
  fermandosi a EMESSA;
- e conoscere **quale contenitore/lotto** è stato prodotto, per portare
  l'operatore direttamente lì a numerare.

### 8-bis. Precisazioni dopo l'analisi (2026-07-27)

Il contratto reale è più preciso di così, e in due punti **diverso**:

1. **Il criterio non è un parametro di chiamata: è uno stato del lotto** (D-3,
   fatto F9). Il BE deve **scrivere le righe di
   `vendite.fatturazione_lotti_gruppi` alla creazione del lotto**, prima di far
   partire la pipeline. Non esiste un modo di passare i gruppi «allo step».
   Impatto BE: `LottoContext` va esteso a portare i gruppi, e il driver deve
   creare il lotto e popolare la tabella **nella stessa transazione**
   ([[feedback_atomicita_madre_db]] — o una madre DB, o `transaction.atomic()`
   esplicito).
2. **L'esito è una LISTA di lotti, non un lotto** (fatto F5, G15): un gruppo con
   righe di tipo doc fiscale diverso produce lotti diversi. L'array `esiti` del
   driver espone già `lotto_id` per terna: il FE deve gestire *N* «vai al
   lotto», non uno. Se N=1 (caso normale) il comportamento è quello previsto
   dall'analisi §5.2.
3. **La fermata a EMESSA non richiede lavoro DB**: è già il parametro
   `fino_a_stato` del core condiviso `esegui_giro_fatturazione` (default della
   corsia differita). A2.4 è coperto oggi.
4. **Nessun `billing_account_id` forzato sul lotto** (D-8).

**Firme che il DB consegnerà** (dettaglio negli step di §9): un parametro
`p_gruppi text[]` su quattro funzioni + due viste di elenco + una funzione
costruttrice della chiave. Assenza/`NULL` = comportamento odierno.

---

## 9. Piano di sviluppo (step aggiornabili)

> **Come si usa**: ogni step ha uno stato ⬜ (da fare) · 🟡 (in corso) · ✅ (fatto
> e testato) · ⛔ (bloccato) · ⏭️ (rinviato). Aggiornare **qui** e nel blocco
> «Stato in testa». Uno step si dichiara ✅ solo quando: migration applicata +
> pgTAP verdi + doc auto-gen rigenerata.
>
> **Convenzioni di changeSet**: `db/changelog/migrations_v2/`, naming
> `YYYYMMDD-NN-<tipo>-<descrizione>.yaml`, un changeSet per file, sempre
> `logicalFilePath`. La numerazione `NN` è una **sequenza globale per data** fra
> tutte le cartelle ([[feedback_liquibase_numerazione_globale_per_data]]) → i
> numeri qui sotto sono **relativi**, si assegnano al momento della scrittura.
> `runOnChange: false` nello stato committato
> ([[feedback_runonchange_false_in_finale]]).
>
> **Regola trasversale — da dove si copia cosa** (⚠️ le due metà hanno fonti
> **diverse**, sbagliarle è un errore silenzioso):
>
> | Pezzo | Fonte | Perché |
> |---|---|---|
> | **corpo** della funzione | doc auto-gen `docs/it/dbzero/<schema>/funzioni/*.md` | riflette l'oggetto **vivo**; lo YAML originale è superato dai `runOnChange` successivi |
> | **firma + `RETURNS TABLE`** | **ultimo YAML** che definisce la funzione | l'auto-gen **scioglie i `%TYPE`** in tipi nudi ([[feedback_autogen_firma_perde_type]]) |
> | `COMMENT ON FUNCTION` | tipi **risolti** (bigint, uuid…) | la firma nel COMMENT non accetta `%TYPE` |
>
> **`%TYPE` è lo standard, non un'opzione**: parametri, `DECLARE`, `RETURNS` /
> `RETURNS TABLE` — ovunque una variabile rifletta una colonna
> (linee-guida-sql §5b). Array espliciti (`text[]`, `bigint[]`):
> `colonna%TYPE[]` non esiste in PostgreSQL
> ([[feedback_pg_type_array_syntax]]). Nei contesti DDL puri
> (`ALTER TABLE ADD COLUMN`) `%TYPE` **non è valido**
> ([[feedback_type_ddl_contexts]]).
>
> **Commenti sempre**: scopo e regole principali nei blocchi non banali della
> funzione, header esteso nel changeSet (cosa cambia, perché, cosa NON tocca).

### Fase B — Simmetria `fatturazione_immediata` *(indipendente, si parte da qui)*

Nessuna dipendenza dalla Fase A. Sblocca il punto 5 del perimetro FE.

| # | Stato | Cartella | Contenuto | Garanzie |
|---|---|---|---|---|
| **B1** | ✅ | `00_schema` | Colonna `fatturazione_immediata BOOLEAN NOT NULL DEFAULT false` su `vendite.ordini`, `vendite.contratti`, `vendite.ddt`. Un changeSet per tabella. ⚠️ `%TYPE` non è valido in `ALTER TABLE ADD COLUMN` ([[feedback_type_ddl_contexts]]) | G16 |
| **B2** | ✅ | `80_data` | Nuovo codice errore `E_FATT_IMMEDIATA_NON_MODIFICABILE` — **solo append al CSV** dei messaggi, nessun nuovo loader ([[feedback_messaggi_errore_no_new_loader]]) | G17 |
| **B3** | ✅ | `20_code` | `fn_list_ordini_da_pushare`, `fn_list_contratti_da_pushare`, `fn_list_ddt_da_pushare`: sostituire la costante `FALSE` con la colonna. ⚠️ **NON toccare lo slot `prezzo_bloccato`** (fatto F11) — annotarlo nel commento della funzione | G9, G18 |
| **B4** | ✅ | `20_code` | `fn_list_consumi_da_pushare`: la costante `FALSE` resta, ma si **commenta come scelta di dominio** (D-6). Solo commento, nessun cambio di comportamento | D-6 |
| **B5** | ✅ | `20_code` | Guard `trgfn_guard_fatturazione_immediata_immutabile()` + trigger `trg_<tab>_a10_guard_fatt_immediata_upd` (`BEFORE UPDATE OF fatturazione_immediata`) su ordini/contratti/DDT **e preventivi**: respinge se esiste `commesse_sorgenti` per `(sorgente_tipo_id, sorgente_uid)` del documento. ⚠️ Guard restrittivo → **grep dei pgTAP esistenti prima** ([[feedback_guard_breaks_existing_tests]]) | G17 |
| **B6** | ✅ | `db/pgtap` | `test-fatturazione-immediata-simmetria-sorgenti-v1.sql` (§10) | G9, G10, G16, G17, G18 |
| **B7** | ✅ | docs | `docs/it/dbzero/vendite/manual/` delle 4 fn + guida `fatturazione.md`. La doc auto-gen la rigenera Tid ([[feedback_no_hand_edit_autogen_docs]]) | — |

### Fase A — Emissione mirata per gruppo fatturabile

Ordine vincolato: A1 → A2 → (A3, A4, A5, A6 in parallelo) → A7 → **A7-bis** → A8.
A7-ter e A9 sono rifiniture a valle, fuori dal cammino critico.

| # | Stato | Cartella | Contenuto | Garanzie |
|---|---|---|---|---|
| **A1** | ✅ | `20_code` | `vendite.fn_build_gruppo_fatturabile_key(p_sorgente_tipo_id bigint, p_sorgente_uid text, p_commessa_id bigint) RETURNS text` **STABLE** (legge `config.sorgenti.codice_interno`). Unica fonte di verità della chiave (D-1). Guard sui parametri ID: errore se `<= 0`, non normalizzare in silenzio | D-1 |
| **A2** | ✅ | `00_schema` + `90_end` | Tabella `vendite.fatturazione_lotti_gruppi`: `id INTEGER GENERATED BY DEFAULT AS IDENTITY`, `lotto_id` FK → `fatturazione_lotti` (ON DELETE CASCADE), `gruppo_key TEXT NOT NULL`, UNIQUE `(lotto_id, gruppo_key)`, colonne audit + `tx_id`, trigger `trgfn_audit_data_user_generic` + `trgfn_tx_id_managed`. ⚠️ Indice FK **opt-in**: serve seed esplicito `consentito=true` in `dbops.fk_index_policy` ([[reference_fk_index_policy_optin]]) | D-3, G11 |
| **A3** | ✅ | `20_code` | `fn_emit_attivita_fatturabili_da_commessa` + `p_gruppi text[] DEFAULT NULL`: filtra il loop `FOR v_row IN` con `fn_build_gruppo_fatturabile_key(...) = ANY(p_gruppi)`. ⚠️ **`DROP FUNCTION IF EXISTS` della firma a 3 arg nello stesso changeSet** (fatto F13) | G2, G3, G13 |
| **A4** | ✅ | `20_code` | `fn_select_attivita_fatturabili` + `p_gruppi text[] DEFAULT NULL`: nel SQL dinamico, `JOIN vendite.commesse_attivita ca ON ca.id = a.commessa_attivita_id` + predicato sulla chiave. ⚠️ `FOR UPDATE OF a` deve restare **solo su `a`**. **È lo step che chiude la falla F8** | **G12**, G2, G5 |
| **A5** | ✅ | `20_code` | `fn_list_emittibili_lane` + `p_gruppi text[] DEFAULT NULL` → la discovery restituisce **solo le terne dei gruppi selezionati** (altrimenti il driver creerebbe lotti vuoti per le altre terne). `DROP` + `CREATE` (RETURNS TABLE) | G15, G6 |
| **A6** | ✅ | `20_code` | `fn_list_commesse_emittibili` + `p_gruppi text[] DEFAULT NULL` → il pull visita solo le commesse che contengono almeno un gruppo selezionato. `DROP` + `CREATE` | G2 |
| **A7** | ✅ | `20_code` | **Estendere `vw_dash_competenza_attivita`** con `sorgente_tipo_id`, `sorgente_uid`, `tipo_movimento`, `gruppo_key` (da A1). ⚠️ `CREATE OR REPLACE VIEW` **deve ri-specificare `WITH (security_invoker=on)`** | prereq. G8/G14 |
| **A7-bis** | ✅ | `00_schema` + `80_data` | **Colonna `area varchar` su `config.sorgenti`** (nullable) + seed della mappa di D-5. ⚠️ Il seed va **nel CSV esistente** `80_data/sql/config/sorgenti.csv` **estendendo in place** il loader `20251002-21-upsert-config-sorgenti-table.yaml` (già `runOnChange: true` + `validCheckSums: ANY` = mirror vivo del CSV): **non creare un nuovo loader** ([[feedback_seed_80_data_csv]], [[feedback_messaggi_errore_no_new_loader]]). Valutare se aggiungere `area` alle colonne lock del trigger `trg_sorgenti_a10_upd_lock_columns` — se sì, su DB esistenti serve DROP+rigenera ([[feedback_automation_lock_columns_create_if_not_exists]]) | prereq. A8 |
| **A7-ter** | ✅ *(come guardrail)* | `db/pgtap` | **Decisione 2026-07-27: NON si riscrivono le 6 viste**, si presidia la coerenza con `test-sorgenti-area-coerenza-viste-v1.sql` (5 casi, verde). Motivo: sei `CREATE OR REPLACE` su viste in uso dalle dashboard per un output **identico** = rischio reale, guadagno solo di igiene. In più la bonifica **non eliminerebbe** il letterale, lo sposterebbe da `'PREVENTIVI'` (area, mutabile) a `'PREVENTIVO'` (`codice_interno`, immutabile). Il guardrail non impedisce la divergenza ma la **intercetta**, a rischio zero. Riscrittura rimandata a quando una di quelle viste verrà toccata per motivi suoi. ~~Bonifica delle **6 viste** `vw_dash_fatturazione_{preventivi,ordini,contratti,ddt,offerte,commesse}`~~ | pulizia D-5 |
| **A8** | ✅ | `20_code` | Vista elenco `vendite.vw_dash_competenza_gruppi`: una riga per `(competenza_mese, gruppo_key)` con tipo gruppo, **riferimento leggibile** (join `config.sorgenti.area` → `vw_dash_fatturazione_documenti`, D-5), cliente, commessa, `n_attivita`, `valore`. Filtro `stadio = 'DA_EMETTERE'` applicato dal consumatore, non cablato | G8, G14, A3 |
| **A9** | ✅ | `20_code` | *(A5 del brief — separabile)* Vista `vendite.vw_dash_competenza_gruppi_riepilogo` con gli aggregati di perimetro. Da fare **solo dopo** che A8 è verde | A5 |
| **A10** | ✅ | `db/pgtap` | `test-emissione-mirata-gruppi-fatturabili-v1.sql` + `test-vw-dash-competenza-gruppi-v1.sql` (§10) | G1-G8, G11-G15 |
| **A11** | ✅ | `db/pgtap` | **Adeguamento dei test esistenti** alle firme cambiate: 16 file toccano le 4 funzioni. Elenco in §10.3 | non-regressione |
| **A12** | ✅ | docs | Manual dbzero delle fn/viste nuove + guida `fatturazione.md` §Fase 3 + comunicazione del contratto §8-bis al BE | — |

### Punti da chiudere prima di partire

| # | Cosa | Chi | Stato |
|---|---|---|---|
| **P1** | ~~Conferma **D-6** (consumi esclusi dal flag)~~ | Tid | ✅ **chiuso 2026-07-27 — sui consumi NO** |
| **P2** | ~~Chiusura **D-5** (dove vive la mappa `area ↔ sorgente`)~~ | Tid | ✅ **chiuso 2026-07-27 — colonna `area` su `config.sorgenti`** (step A7-bis) |
| **P4** | ~~**Chiusura D-9**: forma di `sorgente_uid` per la chiave di gruppo~~ | Tid | ✅ **chiuso 2026-07-27 — si usa l'`uid`** (opzione a). P4 e D-9 erano lo stesso punto: P4 = riga di tracciamento, D-9 = registrazione della decisione |
| **P6** | **Rientro concordato (2026-07-27)**: i 9 pgTAP rossi per `E_SORG_FORMATO` appartengono tutti al perimetro di [brief-db-bonifica-pgtap-sorgente-polimorfa](brief-db-bonifica-pgtap-sorgente-polimorfa.md) — 3 non sono nel suo backlog (§10.4). Da riprendere **dopo** la chiusura di questo brief | Tid+DB | ⬜ **schedulato** |
| **P5** | ~~Correggere §1d di `brief-db-guard-sorgente-polimorfa.md`~~ | DB | ✅ **chiuso 2026-07-27** — §1d corretto (4 righe invece di 3), + nota nel manuale `commesse_attivita` e nuova §4a della guida `sorgente-polimorfa` |
| **P3** | ~~Verifica che nessun pgTAP esistente si rompa con il guard B5~~ | DB | ✅ **chiuso 2026-07-27 — nessun test rotto** (le 20 occorrenze pgTAP sono `p_fatturazione_immediata =>`, parametro di `fn_get_or_create_commessa`, non scritture sulla colonna). Unico percorso applicativo che scrive il flag: `preventivi_service.cambia_stato`, che gira **prima** del push |

### Cosa NON è in questo piano (e perché)

- **Ripetibilità A4**: nessuno step. Il fatto F7 mostra che funziona già; resta
  solo il test G7 (in A10).
- **Fermata a EMESSA (A2.4)**: già coperta da `fino_a_stato`.
- **Colonna `gruppo_key` su `attivita_fatturabili`**: scartata in D-2, da
  riaprire solo su evidenza di `EXPLAIN`.
- **BE e FE**: fuori perimetro DB. Riprendono dai punti 3-6 di
  [analisi-emissione-fattura-ondemand.md](analisi-emissione-fattura-ondemand.md) §8.

---

## 10. Piano test pgTAP

Percorso `db/pgtap/vendite/`. Regole: indice dei test nei commenti in testa al
file, `BEGIN;` + rollback, codici fiscali validi fissi, evitare collisioni
UNIQUE ([[feedback_pgtap_patterns]]).

### 10.1 `test-emissione-mirata-gruppi-fatturabili-v1.sql` ✅ *(scritto e verde, `plan(17)`)*

Fixture: 1 emittente, 1 BA, 1 commessa multi-sorgente con **tre gruppi** —
un preventivo (2 righe), un contratto (2 righe), un onere `MAN:` (1 riga) —
tutte `APPROVATA + NON_EMESSA`, stesso mese, stesso tipo doc.

| # | Caso | Garanzia |
|---|---|---|
| 1 | `fn_build_gruppo_fatturabile_key` su riga con sorgente → `'<codice_interno>:<uid>'` | D-1 |
| 2 | idem su riga sourceless → `'MAN:<commessa_id>'` | D-1 |
| 3 | guard: `p_sorgente_tipo_id <= 0` → errore, non NULL silenzioso | D-1 |
| 4 | `fn_emit_…` **senza** `p_gruppi` → emette tutte e 5 le righe (identico a prima) | **G1** |
| 5 | `fn_emit_…` con il gruppo del preventivo → 2 AF create | **G2** |
| 6 | dopo il caso 5: le righe del contratto e dell'onere hanno ancora `stato_emissione = 'NON_EMESSA'` | **G13** |
| 7 | dopo il caso 5: nessuna AF esiste per contratto/onere | **G3** |
| 8 | `fn_emit_…` con il gruppo `MAN:` → 1 sola AF, ed è quella con `tipo_movimento = 'ONERE'` | **G4** |
| 9 | `fn_emit_…` con **due** gruppi → 4 AF, tutte e sole | **G5** |
| 10 | `fn_emit_…` con chiave inesistente → `total_candidate = 0`, **nessun errore** | **G6** |
| 11 | `fn_select_attivita_fatturabili` con `p_gruppi` = preventivo, **avendo in tabella AF residue del contratto non fatturate** → ritorna solo le 2 del preventivo, e quelle del contratto restano `lock_in_fatturazione = false` | **G12** ⭐ |
| 12 | `fn_select_…` **senza** `p_gruppi` → ritorna tutte (non-regressione) | **G1** |
| 13 | `fn_list_emittibili_lane` con `p_gruppi` → solo le terne dei gruppi richiesti | G15 |
| 14 | `fn_list_commesse_emittibili` con `p_gruppi` → solo le commesse coinvolte | G2 |
| 15 | Due chiamate successive `fn_emit_…` con gruppi diversi → entrambe riescono, conteggi indipendenti | **G7** |
| 16 | `fatturazione_lotti_gruppi`: UNIQUE `(lotto_id, gruppo_key)` respinge il duplicato; CASCADE sul delete del lotto | D-3 |
| 17 | Lotto **senza** righe in `fatturazione_lotti_gruppi` = nessuna restrizione | **G1**, G11 |

> Il caso **11** è il più importante del file: è l'unico che copre la falla F8,
> ed è quello che si romperebbe se qualcuno «semplificasse» filtrando solo il
> pull.

### 10.2 `test-vw-dash-competenza-gruppi-v1.sql` ✅ *(scritto e verde, `plan(9)`)*

> **Due cose imparate scrivendolo**, entrambe annotate nel file:
>
> 1. **La vista base è fail-closed senza GUC.**
>    `script.fn_get_emittenti_scope_sr_ids(NULL)` restituisce l'array **vuoto**,
>    non `NULL`, e la clausola è `sr_ids IS NULL OR emittente = ANY(sr_ids)`:
>    senza `app.current_user_id` **nessuna riga passa**. È il comportamento
>    voluto, ma un test che non imposta la sessione misurerebbe zero *per il
>    motivo sbagliato* — verde o rosso senza dire nulla sul filtro. Il file
>    impersona quindi un operatore whitelistato sull'emittente della fixture, e
>    al caso 8 sposta la whitelist su un altro emittente.
> 2. **Il caso 14 del file 10.1 era debole** nella prima stesura: verificava
>    solo «gruppo inesistente → 0», che sarebbe passato anche con il filtro
>    completamente rotto (bastava che la commessa non fosse emittibile). Ora
>    confronta **filtrato vs non filtrato** sulla stessa commessa, e la
>    transizione a `PRONTA_FATTURAZIONE` è esplicita: entrambe le discovery
>    filtrano prima di tutto su `stati_commessa.emittibile`.
>
> **Limite dichiarato in testa al file**: il caso 8 copre lo scope in
> **lettura** (la vista). Lo scope in **emissione** — passare a `fn_emit` la
> chiave di un gruppo fuori perimetro — è presidiato dalla RLS su
> `vendite.commesse`, che pgTAP **non può esercitare** perché gira come owner e
> la bypassa. Serve un test applicativo con il ruolo `zeroerp_app`.

Stessa fixture. Il test gira **due volte**: senza GUC utente (scope aperto) e
con `app.current_user_id` di un operatore limitato a un altro emittente.

| # | Caso | Garanzia |
|---|---|---|
| 1 | La vista espone 3 righe: preventivo, contratto, **oneri di commessa** | **G8** |
| 2 | `n_attivita` per gruppo = 2 / 2 / 1 | **G8** |
| 3 | `valore` per gruppo = `SUM(prezzo_snapshot * quantita)` delle sue righe | G8 |
| 4 | La somma dei gruppi coincide con il conteggio `DA_EMETTERE` di `vw_dash_competenza_attivita` sulla stessa commessa | **G8** ⭐ |
| 5 | Le chiavi esposte dalla vista sono **accettate** da `fn_emit_…` come `p_gruppi` (nessun mapping) | D-1, G8 |
| 5-bis | `config.sorgenti.area` è valorizzata per le 6 sorgenti-documento e il **riferimento leggibile** del gruppo coincide con il `codice` di `vw_dash_fatturazione_documenti` per lo stesso documento | D-5 |
| 5-ter | Gruppo `MAN:` → riferimento = la commessa, `area` NULL, **nessuna riga persa** dall'elenco per join mancante (LEFT JOIN, non INNER) | D-5, G4 |
| 6 | Con operatore fuori scope emittente → 0 righe nella vista | **G14** |
| 7 | Con operatore fuori scope, passando la chiave **direttamente** a `fn_emit_…` → 0 righe emesse | **G14** ⭐ |
| 8 | `vw_dash_competenza_attivita` conserva `security_invoker = on` dopo la `CREATE OR REPLACE` di A7 (`pg_class.reloptions`) | vincolo 2 |
| 9 | *(solo se A9 fatto)* Il riepilogo A5 coincide con la somma dell'elenco | A5 |

### 10.3 `test-fatturazione-immediata-simmetria-sorgenti-v1.sql` ✅ *(scritto e verde, `plan(20)`)*

> Realizzato con **20 casi** invece dei 10 previsti: ai 10 di piano si sono
> aggiunti i controlli di schema (colonne, NOT NULL, default), la presenza dei
> 4 trigger, e soprattutto la copertura di **entrambi i rami di `key_selector`**
> nel guard (casi 14-17 su ordini = ramo `id`, casi 18-20 su preventivi = ramo
> `uid`). Provarne uno solo avrebbe lasciato scoperto proprio il ramo su cui è
> facile sbagliare (fatto F15).

| # | Caso | Garanzia |
|---|---|---|
| 1 | Le colonne esistono su ordini/contratti/DDT, `NOT NULL DEFAULT false` | B1 |
| 2 | Documento esistente prima della migration → flag `false`, corsia invariata | **G16** |
| 3 | `fn_list_ordini_da_pushare` su ordine con flag `true` → ritorna `true` (non più costante) | **G9** |
| 4 | idem contratti, idem DDT | G9 |
| 5 | `fn_list_consumi_da_pushare` → resta `false` (D-6 verificata come scelta, non dimenticanza) | D-6 |
| 6 | `prezzo_bloccato` di ordini/contratti/DDT **invariato** al variare del flag | **G18** ⭐ |
| 7 | Due documenti stesso BA/utility/periodo con flag diverso → `fn_get_or_create_commessa` produce **due commesse** (corsie separate) | **G10** |
| 8 | `UPDATE` del flag su documento **non ancora pushato** → riesce | G17 |
| 9 | `UPDATE` del flag su documento **già pushato** (riga in `commesse_sorgenti`) → `E_FATT_IMMEDIATA_NON_MODIFICABILE` | **G17** |
| 10 | Il guard non blocca `UPDATE` di altre colonne dello stesso documento | G17 |

### 10.4 Test esistenti da verificare (firme cambiate) — ✅ *eseguito 2026-07-27*

> **Esito**: **nessuna regressione da A1-A6**. Dei 17 file eseguiti, 6 verdi e
> 11 rossi — **tutti e 11 già rossi prima**, per guard introdotti a luglio e
> indipendenti da questa slice:
>
> | Causa del rosso | File | Nota |
> |---|---|---|
> | `E_SORG_FORMATO` (guard sorgente polimorfa, 2026-07-18) | 9 | 6 già censiti in [brief-db-bonifica-pgtap-sorgente-polimorfa](brief-db-bonifica-pgtap-sorgente-polimorfa.md), **3 no**: `test-sorgente-origine-tipo-doc-fiscale-v1`, `test-tipo-movimento-colonna-v1`, `test-trigger-af-commessa-aware-v1` → **da aggiungere a quel backlog** |
> | guard `tipo_doc_emittibile` | `test-fn-list-commesse-emittibili-fatturazione-immediata-v1` | muore nella **fixture** (riga 132), la funzione modificata è chiamata a riga 175: non ci arriva mai |
> | guard AF commessa-aware | `test-fatturazione-draft` | fixture, non correlato |
>
> Prova che nessun rosso è attribuibile alla slice: **nessun errore menziona
> «function is not unique» o una firma inesistente**, che sarebbero i sintomi
> del `DROP`+`CREATE`. Tutti falliscono in fase di **fixture**, prima di
> chiamare le funzioni modificate.
>
> **Smoke test delle firme nuove** (8 asserzioni, verde): funzione A1 presente e
> `STABLE`, entrambe le forme di chiave corrette, i 2 guard che sollevano,
> tabella A2 con la sua UNIQUE, e — il controllo che conta — **le 4 funzioni
> esistono in una sola versione**, cioè il `DROP` della vecchia firma ha
> funzionato e non c'è overload ambiguo.
>
> **Non-regressione Fase B**: `test-fatturazione-immediata-simmetria-sorgenti-v1`
> ancora verde (20/20) dopo l'applicazione di A1-A6.

Il `DROP`+`CREATE` di 4 funzioni tocca **16 file**. Da rieseguire e adeguare
dove chiamano posizionalmente:

```text
test-attivita-guardrail-commessa-v1.sql          test-fn-list-emittibili-lane.sql
test-commesse-core-functions-v1.sql              test-porta-oneri-contatore-cieco-v1.sql
test-commesse-stati-commessa-v1.sql              test-porta-oneri-giro-completo-v1.sql
test-commesse-transizioni-stati-v1.sql           test-sorgente-origine-tipo-doc-fiscale-v1.sql
test-fatturazione-draft.sql                      test-tipo-movimento-colonna-v1.sql
test-fn-emit-attivita-propaga-audit-pricing-v1.sql   test-trigger-af-commessa-aware-v1.sql
test-fn-list-commesse-emittibili-fatturazione-immediata-v1.sql   test-vw-contatore-merce-v1.sql
test-fn-list-ddt-da-pushare-contatore-v1.sql     test-vw-dash-backlog-resi-v1.sql
test-vw-resi-da-accreditare-contatore-v1.sql
```

Lato BE, i moduli che chiamano le stesse funzioni (da allineare alla release
DB): `commesse_repository.py`, `pipeline_repository.py`, `commesse_service.py`,
`fatturazione_driver_service.py`, `fatturazione_giro_handler.py`, più
`types.py` per `LottoContext`.

> ⚠️ Nel repo risultano già **~60 pgTAP rossi preesistenti**
> ([[project_contatore_merce_status]]): prima di attribuire un rosso a questa
> slice, confrontare con il baseline.

---

## 11. Registro attività svolte

> Cronologia di cosa è stato **effettivamente fatto**, con gli artefatti
> prodotti. Serve a chi riprende in mano il brief per sapere dove si è
> arrivati senza ricostruirlo dal git log.

### Consuntivo della slice

| | Prodotto |
|---|---|
| **Migration** | 19 changeSet `20260727-01..19` + estensione del seed `config.sorgenti` |
| **Oggetti DB nuovi** | 1 funzione, 1 trigger function + 4 trigger, 1 tabella, 2 viste, 2 colonne su 4 tabelle, 1 codice errore |
| **Funzioni modificate** | 8 (4 push `fn_list_*_da_pushare`, 4 della catena di emissione) |
| **pgTAP** | 4 file nuovi, **52 asserzioni**, tutte verdi |
| **Documentazione** | 19 file: 7 manuali nuovi, 10 aggiornati, 2 guide |
| **Decisioni registrate** | D-1…D-9, ognuna con l'alternativa scartata e il perché |
| **Garanzie** | da 10 (G1-G10 iniziali) a 18 (G11-G18 dall'analisi critica) |
| **Punti aperti** | P1…P5 chiusi · **P6 schedulato** (pgTAP sorgente polimorfa) |

**Correzioni fuori perimetro**, emerse strada facendo e sistemate:

1. §1d di [brief-db-guard-sorgente-polimorfa](../work-done/brief-db-guard-sorgente-polimorfa.md)
   attribuiva a `commesse_attivita.sorgente_uid` l'hash md5, che è di
   `attivita_fatturabili.sorgente_uid` — ed era proprio la riga che serviva a
   questa slice;
2. la [guida sorgente polimorfa](../../guide/sorgente-polimorfa.md) non diceva
   **chi sta fuori** dal meccanismo → nuova §4a;
3. `commesse_attivita.sorgente_uid` non era documentata affatto → sezione
   dedicata nel manuale della tabella.

### 2026-07-27 · Analisi critica e chiusura decisioni

- Analisi critica del brief sul codice/DB vivo → **8 fatti nuovi** (F7-F15) in
  §4-bis, di cui due che hanno cambiato il piano:
  - **F7** — il nodo di ripetibilità (§A4) **non esisteva**: nessun vincolo di
    unicità dimensionale su `fatturazione_lotti`. Step dedicato eliminato.
  - **F8** — la falla vera è su `fn_select_attivita_fatturabili`, che non ha
    nozione di sorgente → garanzia **G12** aggiunta, step **A4** è il punto
    critico della Fase A.
- Garanzie da 10 a **18** (G11-G18), ognuna con il fatto d'origine.
- Decisioni **D-1…D-9** chiuse (§6); punti aperti **P1-P5** tutti chiusi.
- Allineata l'analisi committente
  [analisi-emissione-fattura-ondemand.md](analisi-emissione-fattura-ondemand.md)
  sui due punti superati (§6.1 e §5.3).

### 2026-07-27 · Bonifica documentale «sorgente polimorfa»

Emersa scrivendo il guard B5: una prima stesura del guard cercava la chiave
sbagliata e **non avrebbe bloccato nulla, in silenzio**. La causa era
documentale, non di codice.

| File | Intervento |
|---|---|
| [guide/sorgente-polimorfa.md](../../guide/sorgente-polimorfa.md) | **nuova §4a** — quali tabelle stanno *fuori* dal meccanismo e non seguono `key_selector`; la regola «la convenzione la determina chi scrive, non chi chiama» |
| [work-done/brief-db-guard-sorgente-polimorfa.md](../work-done/brief-db-guard-sorgente-polimorfa.md) §1d | **corretta**: attribuiva a `commesse_attivita.sorgente_uid` l'hash md5, che è di `attivita_fatturabili.sorgente_uid`. Da 3 a 4 righe |
| [dbzero/vendite/manual/commesse_attivita.md](../../dbzero/vendite/manual/commesse_attivita.md) | **nuova sezione**: la colonna non era documentata affatto |

**Esito**: nessuna bonifica di dati. Le due convenzioni sono entrambe corrette e
hanno consumatori vivi (`vw_dash_fatturazione_contratti` si appoggia a quella di
`commesse_attivita`): mancava solo che fossero scritte. Vedi **F15** e **D-9**.

### 2026-07-27 · Fase B — simmetria `fatturazione_immediata` ✅

**Migration applicate** (`db/changelog/migrations_v2/`):

| # | File | Step |
|---|---|---|
| `20260727-01..03` | `00_schema/vendite/` — colonna su ordini, contratti, DDT | B1 |
| `20260727-04..06` | `20_code/vendite/` — le 3 `fn_list_*_da_pushare` leggono la colonna | B3 |
| `20260727-07` | `20_code/vendite/` — `fn_list_consumi_da_pushare`: nota di dominio D-6 | B4 |
| `20260727-08` | `20_code/vendite/` — `trgfn_guard_fatturazione_immediata_immutabile` | B5 |
| `20260727-09` | `20_code/vendite/` — guard armato su 4 sorgenti | B5 |
| — | `80_data/sql/config/messaggi_errore.csv` — `E_FATT_IMMEDIATA_NON_MODIFICABILE` (561), **solo append** | B2 |

**Test** — `db/pgtap/vendite/test-fatturazione-immediata-simmetria-sorgenti-v1.sql`,
`plan(20)`, **verde**. Copre G9, G10, G16, G17, G18 + D-6. Casi 14-17 sul ramo
`key_selector='id'` (ordini), casi 18-20 sul ramo `'uid'` (preventivi): i due
rami del guard sono entrambi coperti da un controllo positivo. Casi 9-10
(contratti/DDT) sono **data-dependent con skip** — limite dichiarato in testa al
file.

**Documentazione** (9 file): nuovo manuale del guard, sezione sulla colonna su
`manual/{ordini,contratti,ddt}.md`, nota «dalla costante alla colonna» sulle 3
`fn_list_*_da_pushare`, spiegazione di D-6 su `fn_list_consumi_da_pushare`, e
nuova sezione «Su quale corsia finisce il lavoro» in
[guide/fatturazione.md](../../guide/fatturazione.md).

**Verifiche fatte, esito negativo (nessun intervento necessario)**:

- **P3** — nessun pgTAP aggiorna `fatturazione_immediata` su alcuna delle 4
  tabelle: il guard non può romperne nessuno. L'intersezione fra «test che fanno
  `UPDATE vendite.preventivi`» (8 file) e «test che collegano un preventivo a
  una commessa» (19 file) è **vuota**.
- I test Django dei preventivi sono `unittest.TestCase` con repository mockato:
  non raggiungono il trigger.

**Chiusura**: migration applicate, pgTAP verde, doc auto-gen rigenerata e
**commit eseguito** (`49eed89d0`).

### 2026-07-27 · Fase A — emissione mirata per gruppo fatturabile ✅

**Migration applicate** (`db/changelog/migrations_v2/`):

| # | File | Step |
|---|---|---|
| `20260727-10` | `20_code/vendite/` — `fn_build_gruppo_fatturabile_key` | A1 |
| `20260727-11` | `00_schema/vendite/` — tabella `fatturazione_lotti_gruppi` | A2 |
| `20260727-12` | `fn_emit_attivita_fatturabili_da_commessa` + `p_gruppi` | A3 |
| `20260727-13` | `fn_select_attivita_fatturabili` + `p_gruppi` ⭐ | A4 |
| `20260727-14` | `fn_list_emittibili_lane` + `p_gruppi` | A5 |
| `20260727-15` | `fn_list_commesse_emittibili` + `p_gruppi` | A6 |
| `20260727-16` | `vw_dash_competenza_attivita` + colonne di gruppo | A7 |
| `20260727-17` + CSV | `config.sorgenti.area` + seed della mappa | A7-bis |
| `20260727-18` | vista `vw_dash_competenza_gruppi` | A8 |

**Test** — 3 file nuovi, tutti verdi:
`test-emissione-mirata-gruppi-fatturabili-v1.sql` `plan(17)`,
`test-vw-dash-competenza-gruppi-v1.sql` `plan(10)` (il caso 10 arriva con A9) e
`test-sorgenti-area-coerenza-viste-v1.sql` `plan(5)` (guardrail A7-ter).
Più la verifica di non-regressione sui 17 file toccati dal cambio firma (§10.4).

**Due difetti trovati nei test stessi, non nel codice**:

- il caso 13 falliva perché entrambe le discovery filtrano *prima di tutto* su
  `stati_commessa.emittibile`, e la commessa fixture era in BOZZA;
- più importante, il **caso 14 passava per la ragione sbagliata**: verificava
  solo «gruppo inesistente → 0», il che sarebbe stato verde anche col filtro
  completamente rotto. Riscritto per confrontare **filtrato vs non filtrato**
  sulla stessa commessa.

**Limite dichiarato**: lo scope in **emissione** (passare a `fn_emit` la chiave
di un gruppo fuori perimetro) è presidiato dalla RLS su `vendite.commesse`, che
pgTAP **non può esercitare** perché gira come owner. Serve un test applicativo
con il ruolo `zeroerp_app`. Annotato in testa al file.

**Documentazione** (10 file): 4 manuali nuovi
(`fn_build_gruppo_fatturabile_key`, `fatturazione_lotti_gruppi`,
`vw_dash_competenza_gruppi`, `vw_dash_competenza_gruppi_riepilogo`),
5 aggiornati (le 4 funzioni con `p_gruppi` + `vw_dash_competenza_attivita`),
`config/manual/sorgenti.md` per la colonna `area`, e nuova sezione «Fatturare un
documento preciso: l'emissione mirata» nella
[guida fatturazione](../../guide/fatturazione.md).

**Deviazioni dal piano, motivate**:

- **A2 senza seed `fk_index_policy`**: la `UNIQUE (lotto_id, gruppo_key)` ha
  `lotto_id` come prefisso e copre già l'unico accesso previsto. Un indice FK
  dedicato sarebbe ridondante (`dbops.vw_duplicate_indexes`). Registrato con
  `consentito = false`, che è il default della policy opt-in.
- **A7-bis ha richiesto di cambiare `nullValue` del loader CSV** da `""` a
  `"NULL"` per poter esprimere `area = NULL`. Verificato prima: nel CSV non
  esiste alcuna cella vuota né alcuna contenente la stringa `NULL` → modifica
  **inerte** per le 15 colonne preesistenti.
- **A9 e A7-ter restano ⏭️ rifiniture**, come da piano.

### 2026-07-27 · Rifiniture A9 e A7-ter — chiuse

**A9 · vista di riepilogo** (`20260727-19`, applicata):
`vw_dash_competenza_gruppi_riepilogo` — `n_gruppi`, `n_attivita`, `valore`,
`n_gruppi_oneri`, per `(competenza, stadio, emittente)`. **Aggrega** la vista di
dettaglio, non ricalcola: i due numeri non possono divergere. Coperta dal caso
10 di `test-vw-dash-competenza-gruppi-v1.sql`.

*Motivo per cui non è stata rinviata*: senza aggregati dal DB il frontend
sommerebbe le righe della **pagina corrente**, mostrando un parziale che sembra
un totale — e nessuno somma a mano più pagine per accorgersene.

**A7-ter · deciso il guardrail al posto della bonifica.** Le 6 viste
`vw_dash_fatturazione_*` continuano a scrivere il letterale `area` a mano; la
coerenza con `config.sorgenti.area` è presidiata da
`test-sorgenti-area-coerenza-viste-v1.sql` (5 casi, verde), che legge le
**definizioni** (`pg_get_viewdef`) e non i dati.

Le due ragioni della scelta:

1. sei `CREATE OR REPLACE` su viste **in uso dalle dashboard** per un output
   **identico** = rischio reale, guadagno di sola igiene;
2. la bonifica **non eliminerebbe** il letterale: lo sposterebbe da
   `'PREVENTIVI'` (area, vocabolario mutabile) a `'PREVENTIVO'`
   (`codice_interno`, immutabile). Miglioramento vero — è la regola di
   linee-guida-sql §6d — ma non il salto da hardcoded a non-hardcoded.

Il guardrail non impedisce la divergenza, la **intercetta**: 90% del valore,
0% del rischio. Riscrittura rimandata a quando una di quelle viste verrà
toccata per motivi suoi.

**⚠️ Reperto emerso dal guardrail**: `config.sorgenti` contiene **15 righe, non
10**. Il seed CSV ne copre 10; le altre cinque (`PREVENTIVO_RIGA`,
`CONTRATTO_RIGA`, `ORDINE_VENDITA_RIGA`, `DDT_VENDITA_RIGA`, `FATTURA_RIGA`,
`scope = ROW_VALIDATOR`) arrivano da `20260225-44`. Il seed dell'area ha
funzionato correttamente — quelle righe non essendo nel CSV hanno mantenuto
`NULL` — ma **`sorgenti.csv` non è lo specchio completo della tabella**: chi
ragiona sul seed sta vedendo due terzi delle righe.

**Aperto**: commit e rigenerazione doc auto-gen `dbzero` (a cura di Tid).

### Prossimo passo

Chiusa la Fase A **con le rifiniture**, il perimetro DB del brief è
**completo**: non restano voci ⬜ né ⏭️. Restano:

1. **P6** — rientro sui pgTAP rossi della sorgente polimorfa (concordato);
2. **BE/FE** — punti 3-6 del perimetro in
   [analisi-emissione-fattura-ondemand.md](analisi-emissione-fattura-ondemand.md) §8,
   con il contratto di §8-bis di questo brief.

---

## 12. Riferimenti

- Analisi committente: [analisi-emissione-fattura-ondemand.md](analisi-emissione-fattura-ondemand.md)
  (§5.1-bis commessa≠documento · §5.3 flag · §5.5 design UI e gruppo fatturabile)
- Porta oneri (righe sourceless): [brief-db-immutabilita-quantita-e-porta-oneri.md](brief-db-immutabilita-quantita-e-porta-oneri.md)
- Commessa multi-sorgente: [brief-db-commesse-multi-sorgente.md](../work-done/brief-db-commesse-multi-sorgente.md)
- Guida processo: [fatturazione.md](../../guide/fatturazione.md)
