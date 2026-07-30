# Brief DB — Generazione del piano rate della fattura (scadenze)

> 🔴 **REVISIONE 2026-07-30 — questo brief è SUPERATO IN PARTE SOSTANZIALE.**
> Il documento operativo di riferimento è
> **[piano-db-satelliti-fattura.md](piano-db-satelliti-fattura.md)**.
> **Non lavorare da questo brief senza aver letto quel piano.**
>
> **La causa è una sola decisione, D-I: un solo meccanismo per le condizioni di
> pagamento.** Le colonne `clienti.tipo_gg_scadenza_ft` / `nr_giorni_scadenza` e
> `fatture.giorni_pagamento` / `fine_mese` **si eliminano**; resta solo
> `termine_pagamento_id`, e `config.termini_pagamento` prende una forma piatta
> (giorni + booleano `fine_mese`). Cade così tutto l'impianto del «percorso
> legacy» che occupa buona parte di questo brief.
>
> | § di qui | Esito | Rif. |
> |---|---|---|
> | **D-2, D-3, D-4** | ❌ **eliminate**: non c'è più una coppia legacy a cui dare precedenza, di cui definire la semantica, né un'ambiguità da presidiare | D-I |
> | **§4.3** (guard mutua esclusione) | ❌ **eliminato**, con il suo codice errore. La bonifica dei 2 clienti resta ma come **migrazione verso il catalogo** | D-I |
> | **§4.4-bis** (la «contraddizione risolta») | ❌ **eliminata**: serviva solo a rappresentare il percorso legacy in testata | D-I |
> | **§5.5** | 🔄 **si ribalta**: le due colonne si deprecano davvero — era la risposta della prima stesura, tornata giusta | D-I |
> | **§6 punti 4, 5, 6-bis** | ❌ **eliminati**: presidiavano il percorso legacy | D-I |
> | §4.2 | 🔄 L'elemento di chiave è la **coppia** `(termine_pagamento_id, modalita_pagamento_id)` — la **modalità entra in chiave** con lo stesso argomento del termine, e la tripla con `giorni_pagamento`/`fine_mese` non serve più | D-B, C-9 |
> | §4.1 + §4.2 | ⚠️ Una **sola** implementazione della catena: se `fn_resolve_termini_pagamento` resta in piedi e non chiamata, il secondo risolutore torna a esistere | C-13 |
> | §4.4 | ➕ La **formula** del generatore va scritta (il brief non la contiene). Un solo ramo, nessun caso speciale | C-5 |
> | §4.5 | 🔄 `totale_a_pagare` **0 o negativo non è un errore**: nessuna rata, e log non critico sul negativo. Errore solo su NULL | D-D, C-4 |
> | §4.6 | ✅ Verificato: durante la tappa EMESSA le fatture sono **ancora DRAFT** (il sync è dopo i task). Il rerun → il wrapper salta, la per-fattura solleva | D-F, C-8 |
> | §4.8 | ⚠️ L'invariante pgTAP citato copre **solo DEFINITIVA**: la divergenza della corsia giornaliera resterebbe muta. Corsia 2 **allineata** e invariante **esteso** | D-C, C-7 |
> | §5.2-5.4 | 🔄 Non sono domande aperte: `tipo_offset` → booleano `fine_mese`, `unita_intervallo` eliminata, `ripartizione` ristretta a `UGUALI` **nel dominio**, non solo a runtime | D-E |
>
> **Sei lavori che questo brief non prevede** e che il piano ha aggiunto:
> guard di coerenza in `fn_assign_numero_fattura` prima di consumare il
> progressivo (D-K) · ambito arrotondamenti da allineare alla chiave, che D-7
> altrimenti rende non riproducibile (D-N) · ritorno del lotto a DRAFT (Fase 6) ·
> estrazione di una fattura da lotto EMESSA verso ANNULLATA (D-N-bis) ·
> eliminazione del flag dormiente `esclusa` (D-M) · rinomina delle funzioni di
> reset e correzione dell'over-free del `lock_batch_id` (D-L).
>
> **Destinatario:** team DB (`dev/db-tid`)
> **Richiedente:** BE (`dev/backend-tid`) — Tid ha approvato disegno e precedenze il 2026-07-29
> **Stato:** superato dal piano unificato (vedi sopra)
> **Vincolo:** il BE non procede fino all'apply di questo brief (regola prerequisiti DB)
> **Fratello:** [brief-db-snapshot-indirizzi-fattura.md](brief-db-snapshot-indirizzi-fattura.md) — stesso cantiere, step DRAFT
> **Lavoro applicativo a valle:** [piano-be-fe-satelliti-fattura.md](piano-be-fe-satelliti-fattura.md) — include gli **smoke di accettazione** che collaudano questo brief
>
> **Revisione 2026-07-29 (seconda passata).** Rilettura critica prima di
> consegnare al team DB. Esito: **una contraddizione interna trovata e
> risolta** (§4.4-bis), il «punto più delicato» del brief **chiuso** senza
> bisogno di inventare rappresentazioni (§4.2), §5.5 non è più una domanda
> aperta, e i numeri di §2-bis rendono concreto ciò che era ipotetico —
> in particolare la bonifica di D-4, che riguarda **2 clienti reali**.

---

## 1. Scopo

Far generare alla pipeline di fatturazione il **piano rate** di ogni fattura in
`vendite.fatture_scadenze`, e valorizzare in testata le condizioni di pagamento
(`modalita_pagamento_id`, `termine_pagamento_id`, `termine_pagamento_snapshot`)
che oggi restano NULL.

## 2. Il problema, in numeri

Verificato sul DB di sviluppo il 2026-07-29:

| Fatto | Misura |
| --- | --- |
| Righe in `vendite.fatture_scadenze` | **0** su 7 fatture |
| Fatture con `termine_pagamento_id` valorizzato | **0** su 7 |
| Fatture con `modalita_pagamento_id` valorizzato | **0** su 7 |
| Occorrenze di `termine_pagamento_snapshot` nel repo | 2 (la migration che la crea + la doc): **mai scritta, mai letta** |

**Non è un bug: è un produttore che non è mai stato scritto.** Tutto il resto
della catena esiste e funziona — trigger di audit/storico/scope, 2 policy RLS,
grant `iud` al ruolo batch, lettore `list_fattura_scadenze`, `_shape_scadenza`
del contesto PDF, endpoint di dettaglio, BB frontend `ScadenzeSintesi`.

Conseguenze già visibili o imminenti:

1. il **PDF** non stampa il piano rate (la sezione esiste nel template);
2. il blocco **`2.4 DatiPagamento` della FatturaPA non è generato** — ricerca di
   `DatiPagamento`/`DataScadenzaPagamento`/`ModalitaPagamento` su tutto il repo:
   zero risultati. È un requisito di **completezza fiscale**, non un abbellimento;
3. il **portale clienti** ha in piano `GET /api/portale/scadenze/`, oggi vuoto;
4. nel drawer fattura i campi «Modalità di pagamento» e «Termine» sono
   sistematicamente vuoti.

## 2-bis. Su quali dati atterra questo lavoro (misurato 2026-07-29)

La catena di precedenza di §4.2 ha tre livelli. Questi sono i dati che oggi la
alimentano — e cambiano la percezione del rischio di D-7 e della bonifica D-4:

| Livello della catena | Dato reale |
| --- | --- |
| 1 — termine sul **documento sorgente** | `vendite.ordini`: **0 righe in totale**; `vendite.preventivi`: **0 righe in totale** |
| 2a — coppia legacy sul cliente (`G`/`F` + giorni) | **2** clienti su 21 |
| 2b — `clienti.termine_pagamento_id` | **3** clienti su 21 |
| ⚠️ **2a e 2b insieme** (contraddittori, D-4) | **2** clienti — cioè **tutti** quelli con la coppia legacy |
| 3 — default `TP_1RATA` | **18** clienti su 21 non hanno né l'uno né l'altro |
| gerarchia `parent_account_id` | **0** BA figli |

Tre conseguenze operative:

1. **D-7 oggi ha raggio d'azione nullo.** Il termine può far nascere fatture
   separate solo attraverso il livello 1 (§4.2), e di documenti sorgente con un
   termine esplicito **non ce n'è nessuno** — non ci sono proprio ordini né
   preventivi. La chiave va comunque cambiata adesso, perché è l'unico momento
   in cui costa poco; ma **nessuna frammentazione è attesa sui dati attuali**,
   e questo va detto a chi teme un'esplosione di fatture.
2. **La bonifica di D-4 non è un'ipotesi: sono 2 clienti**, e sono il 100% di
   quelli con la coppia legacy. Il guard di §4.3 **non è accendibile** prima di
   averli sistemati — vedi §4.3.
3. **Il ramo 1 non ha dati su cui appoggiarsi**: i test pgTAP di §6 punto 1
   devono costruirsi le fixture da zero (un ordine e un preventivo con termine).
   È esattamente il ramo che oggi è rotto (§4.1) e mai eseguito: la fixture è
   parte del lavoro, non un dettaglio.

---

## 3. Decisioni prese (Tid, 2026-07-29)

| # | Decisione |
| --- | --- |
| D-1 | Il task di generazione va **in coda allo step EMESSA**, dopo `ricalcola_iva_lotto` |
| D-2 | **Precedenza alla coppia legacy** `clienti.tipo_gg_scadenza_ft` + `nr_giorni_scadenza`: se valorizzate vincono su `clienti.termine_pagamento_id` |
| D-3 | Semantica coppia legacy: `nr_giorni_scadenza` si **somma alla data fattura**; se il tipo è fine-mese la data risultante si **sposta a fine mese**; altrimenti conteggio giorni puri |
| D-4 | Sul cliente i due modi diventano **mutuamente esclusivi**: se sono indicati i giorni non si deve poter selezionare un termine di pagamento (guard DB) |
| D-5 | **Lock post-numerazione** sulle scadenze: approvato |
| D-6 | Vanno corrette le anomalie segnalate in §5 |
| D-7 | **Il termine di pagamento entra nella CHIAVE DI AGGREGAZIONE della fattura.** Avendo permesso di scegliere il termine sul documento, quel termine va rispettato: attività con termini diversi generano **fatture diverse**, non una fattura con un termine arbitrario (§4.2) |

> 🔴 **Rev. 2026-07-30 — D-2, D-3 e D-4 sono ELIMINATE.** Con D-I le colonne
> `clienti.tipo_gg_scadenza_ft` e `nr_giorni_scadenza` non esistono più: non c'è
> una coppia legacy a cui dare precedenza (D-2), di cui definire la semantica
> (D-3), né un'ambiguità da presidiare con un guard (D-4). Chi ha condizioni
> particolari usa un **termine dedicato nel catalogo**.
> **D-1, D-5, D-6 e D-7 restano valide.**

### Perché EMESSA e non DRAFT (D-1)

I totali della fattura (`totale_doc`, `totale_a_pagare`) **non esistono in
DRAFT**: li scrive `ricalcola_iva_lotto` → `fn_ricalcola_totali_fattura`, che
vive nello step EMESSA (pipeline id 3). Un task in DRAFT ripartirebbe un totale
NULL. La coda di EMESSA è anche **prima** di `stampa_documenti_lotto` (step
DEFINITIVA), quindi il PDF trova le rate già scritte.

> La `fatturazione-roadmap.md:36` ipotizzava «task post-DEFINITIVA»: è più tardi
> del necessario e rischia di cadere **dopo** la stampa, che nello stesso step
> segue immediatamente `numera_fatture`.

---

## 4. Cosa serve al DB

### 4.1 Correggere `vendite.fn_resolve_termini_pagamento` (bug bloccante)

La funzione esiste dal 2025-10-19, **non è chiamata da nessuno** e **non è
eseguibile** sui rami 1 e 2: usa `termini_pagamento_id` (**plurale**) dove le
tabelle hanno `termine_pagamento_id` (**singolare**).

| Punto | Scritto | Reale |
| --- | --- | --- |
| ramo 1 — `vendite.fatture` | `f.termini_pagamento_id` | `fatture.termine_pagamento_id` |
| ramo 2 — `vendite.ordini` | `o.termini_pagamento_id` | `ordini.termine_pagamento_id` |
| ramo 2 — `vendite.preventivi` | `p.termini_pagamento_id` | `preventivi.termine_pagamento_id` |
| ramo 2 — `vendite.contratti` | `c.termini_pagamento_id` | **la colonna non esiste affatto** |
| ramo 3 — `anagrafiche.clienti` | `cl.termine_pagamento_id` | ✅ corretto |

Essendo plpgsql, i rami 1 e 2 solleverebbero `42703 column does not exist` alla
prima esecuzione. Il difetto è identico in tutte e tre le versioni in migration
(`20251019-02`, `20260217-09`, `20260331-23`) e non è emerso perché il pgTAP
`test-fattura-utils-critical-termini.sql:288-315` **esercita solo il ramo 4**
(fallback `TP_1RATA`) e la guard sui parametri.

> È la stessa forma del difetto `fn_generate_fatture_righe` (funzione mai
> eseguita su cui erano stati scritti due requisiti) e della stampa fattura rotta
> trovata dallo smoke C-9: **test verdi su codice morto**. I test nuovi devono
> coprire i rami 1, 2 e 3, non solo il fallback.

**Sul ramo `CONTRATTO`**: il livello «documento sorgente» **resta** (con D-7 è il
primo della catena, §4.2), ma limitato a **ordine e preventivo**, che la colonna
ce l'hanno. Il ramo contratto va **rimosso**: `vendite.contratti` non ha
`termine_pagamento_id` e non va aggiunta ora — nessun processo la popolerebbe. Le
attività che vengono da contratto scendono quindi al livello cliente. Se in futuro
il contratto dovrà dettare le condizioni, si aggiunge allora, insieme al suo
popolamento e all'ingresso in chiave.

### 4.2 Dove vive la risoluzione: **nella chiave di aggregazione**, non nel generatore

Con D-7 la catena di precedenza si sposta **a monte**, in `fn_build_fattura_key`:
è lì che il termine determina *quante* fatture nascono, e da lì viene scritto in
testata da `fn_get_or_create_fattura_header`. Il generatore delle scadenze
(§4.4) **legge** il termine dalla testata e non ri-risolve nulla — un solo punto
di verità per fattura.

La catena, applicata **per attività** durante la costruzione della chiave, è al
punto 1 di «Cosa comporta, concretamente» qui sotto.

### ⚠️ Il termine entra nella CHIAVE DI AGGREGAZIONE (D-7) — cambia `fn_build_fattura_key`

Le condizioni di pagamento sono un **attributo unico della testata fiscale**
(`fatture.termine_pagamento_id`): la fattura ne ha **uno**. Ma una fattura
**aggrega N attività** che possono venire da documenti con termini **diversi**.
Un valore unico che riceve N valori diversi è irriducibile: non si può scegliere,
non si possono tenere entrambi.

Due soli disegni coerenti — e **si adotta (a)**:

| Disegno | Conseguenza |
| --- | --- |
| **(a) ✅ SCELTO** — il termine entra nella **chiave di aggregazione** | attività con termini diversi generano **fatture separate**: il termine diventa un discriminante come valuta, registro o utility |
| (b) — il termine si prende solo dal cliente | l'aggregazione resta invariata, ma **il termine scelto sul documento viene ignorato** |

**Motivazione della scelta (Tid):** il sistema **permette** di scegliere un
termine di pagamento sul documento (`vendite.ordini.termine_pagamento_id`,
`vendite.preventivi.termine_pagamento_id`). Avendolo permesso, quel termine
**deve** essere rispettato in fattura: ignorarlo produrrebbe fatture con
condizioni diverse da quelle pattuite. La conseguenza — più fatture quando i
termini divergono — è il comportamento **corretto**, non un effetto collaterale.

### Cosa comporta, concretamente

**1. `vendite.fn_build_fattura_key` deve includere il termine.**
Oggi ritorna 7 elementi: `billing_account_id` (⚠️ il **padre** se presente:
`COALESCE(ba.parent_account_id, a.billing_account_id)`), `tipo_doc_fiscale_id`,
`valuta_id`, `emittente_soggetto_ruolo_id`, `reseller_soggetto_ruolo_id`,
`utility_id`, `registro_id`. Va aggiunto **`termine_pagamento_id`**, risolto per
la singola attività con questa catena:

```text
1. termine del DOCUMENTO SORGENTE dell'attività (ordine / preventivo)
2. cliente del BA:  2a. coppia legacy tipo_gg_scadenza_ft + nr_giorni_scadenza (D-2/D-3)
                    2b. clienti.termine_pagamento_id
3. default config.termini_pagamento.codice_interno = 'TP_1RATA'
```

⚠️ La coppia legacy (2a) **non è un `termine_pagamento_id`**: è una condizione
espressa in modo diverso, e va comunque rappresentata in chiave.

**✅ Risolto (revisione 2026-07-29): non serve inventare nessun token.** La
prima stesura proponeva un jsonb normalizzato e lasciava la scelta al team DB.
Non serve, perché la rappresentazione **esiste già** ed è quella che finisce in
testata (§4.4-bis): la condizione risolta è la **tripla**

```text
(termine_pagamento_id, giorni_pagamento, fine_mese)
```

— le tre colonne che `vendite.fatture` **ha già**. L'elemento di chiave è quella
tripla, e coincide esattamente con ciò che `fn_get_or_create_fattura_header`
scriverà in testata. Vantaggi, tutti pratici:

- è **confrontabile e stabile** fra esecuzioni (tre scalari, nessun jsonb da
  normalizzare, nessun ordine di chiavi da garantire);
- è **la stessa cosa** in chiave, nel `WHERE` del lookup e in testata → la regola
  «ogni elemento della chiave compare nel lookup» (punto 3) si verifica sulle
  stesse tre colonne, invece che su un token da un lato e colonne dall'altro;
- non introduce nessuna rappresentazione nuova da mantenere.

> **E i livelli 2 e 3 non discriminano nulla, oggi.** La chiave contiene già il
> billing account, e l'invariante «1 BA → 1 istanza → 1 cliente» (più sotto)
> rende i livelli 2a/2b/3 **funzione del solo BA**: a parità di BA danno sempre
> la stessa risposta. Ne segue che, finché la gerarchia `parent_account_id` non
> è attiva (0 BA figli), **solo il livello 1 può far nascere fatture separate** —
> ed è il motivo per cui D-7 oggi non frammenta niente (§2-bis). La tripla in
> chiave resta comunque la scelta giusta: è ciò che rende il comportamento
> corretto **anche** quando la gerarchia verrà accesa, senza doverci tornare.

**2. `fn_get_or_create_fattura_header` va allineata su DUE fronti:**

- il **lookup** della fattura esistente deve filtrare **anche** sul termine,
  altrimenti la chiave discrimina ma il lookup aggrega → attività con termini
  diversi finirebbero comunque nella stessa fattura;
- l'**INSERT** deve scrivere `termine_pagamento_id` (e `modalita_pagamento_id`)
  in testata: oggi non li valorizza affatto.

**3. 🐛 Disallineamento chiave/lookup già presente su `utility_id` — da correggere
nello stesso intervento.** `fn_build_fattura_key` mette `utility_id` in chiave,
ma il lookup di `fn_get_or_create_fattura_header` filtra su lotto, BA, tipo doc,
valuta, emittente, reseller, registro: **`utility_id` non è nel WHERE**.

Oggi non morde, per due ragioni che vanno entrambe scritte: (a) `billing_account`
ha una sola `utility_id`, quindi il BA la determina; (b) la gerarchia
`parent_account_id` **non è usata** (0 BA figli, verificato 2026-07-29). Ma la
chiave usa il BA **padre** e la utility del **figlio**: appena la gerarchia venisse
attivata, il lookup troverebbe la fattura del padre per una utility diversa e
aggregherebbe righe di utility differenti nello stesso documento.

> **Regola da fissare** (e da presidiare con un test): *ogni elemento della chiave
> logica deve comparire nel `WHERE` del lookup*. È l'invariante che rende
> l'aggregazione prevedibile, e vale sia per la utility (oggi) sia per il termine
> (con questo brief).

**4. «Ogni utility la sua fattura» è già garantito** (richiesta di Tid): `utility_id`
è già in chiave, e `billing_account.utility_id` è unica per BA. Serve solo la
correzione del punto 3 perché resti vero anche con la gerarchia attiva.

### L'invariante «1 BA = 1 istanza = 1 cliente» è garantito da vincoli DB

Non serve nessun presidio applicativo contro «più righe cliente per BA con
condizioni diverse»: il caso **non può esistere**. Fonte: guida
[gestione-delle-istanze-utility](../../guide/gestione-delle-istanze-utility.md)
§«Istanza e billing account: relazione 1:1 per utility», che lo dichiara
invariante fondamentale, con i vincoli che lo impongono:

- `billing_account.istanza_utility_id` **FK singola NOT NULL** → un BA, una istanza;
- `UNIQUE (istanza_utility_id, utility_id)` su `billing_account`;
- `UNIQUE` su `clienti.istanza_utility_id` → **un'istanza ospita al massimo un cliente**.

Dati coerenti: 21 BA / 21 istanze / 21 clienti, zero condizioni discordanti
(2026-07-29). La risoluzione del cliente dal BA è quindi **univoca per
costruzione**.

⚠️ **Resta da correggere** il `LIMIT 1` senza `ORDER BY` del ramo cliente: con
l'invariante sopra il risultato è comunque unico, ma un `LIMIT 1` non vincolato
è un invito al non-determinismo se il modello evolvesse. Meglio filtrare
esplicitamente per l'istanza del BA (`cl.istanza_utility_id = ba.istanza_utility_id`).

⚠️ **Unico caso residuo, oggi teorico**: la gerarchia `parent_account_id`. La
chiave usa il BA **padre**, quindi una fattura intestata al padre potrebbe
aggregare attività di **BA figli diversi** — ognuno con la propria istanza e
quindi il proprio cliente, con condizioni potenzialmente diverse. Con `termine` in
chiave (D-7) il conflitto si risolve da sé: termini diversi → fatture diverse.
Da tenere presente quando la gerarchia verrà attivata.

### 4.3 ~~Guard di mutua esclusione su `anagrafiche.clienti` (D-4)~~ — ELIMINATO

> 🔴 **Rev. 2026-07-30.** Sezione superata da D-I: con le due colonne eliminate,
> **l'ambiguità non è più rappresentabile per costruzione**. Niente guard, niente
> `E_CLIENTI_CONDIZIONI_PAGAMENTO_AMBIGUE`, niente ordine obbligato di
> accensione. Dei 2 clienti resta la **migrazione al catalogo** (piano, 3a.4):
> si ripuntano al termine equivalente, creandolo se manca. Sono dati di test,
> si sistemano al momento. Il testo sotto è conservato solo come storia.

Oggi **nessun vincolo** impedisce di avere insieme `tipo_gg_scadenza_ft IN ('G','F')`
(con giorni) **e** `termine_pagamento_id` valorizzato: due condizioni di pagamento
contraddittorie sulla stessa riga.

Serve un guard che le renda mutuamente esclusive. Il posto naturale è
**estendere il trigger già esistente** `anagrafiche.trgfn_clienti_normalize_giorni_scadenza`
(che oggi fa: tipo NOT IN ('G','F') → azzera `nr_giorni_scadenza`; tipo IN ('G','F')
con giorni NULL/≤0 → `E_CLIENTI_GIORNI_SCADENZA_OBBLIGATORI`), aggiungendo il
ramo: `tipo IN ('G','F') AND termine_pagamento_id IS NOT NULL` → errore
(codice nuovo, proposta `E_CLIENTI_CONDIZIONI_PAGAMENTO_AMBIGUE`).

> Pattern «normalize + guard simmetrico» già in uso nel progetto per le coppie
> flag/valore.

🔴 **La bonifica non è un'ipotesi: sono 2 clienti, ed è bloccante.** La prima
stesura scriveva «se qualche riga ha entrambi valorizzati». Misurato il
2026-07-29:

| Misura | Valore |
| --- | --- |
| Clienti con la coppia legacy (`G`/`F` + giorni) | 2 su 21 |
| Clienti con `termine_pagamento_id` | 3 su 21 |
| **Clienti con ENTRAMBI** | **2** — cioè **il 100%** di quelli con la coppia legacy |

Acceso così com'è, il guard **rifiuterebbe qualunque UPDATE** su quelle 2 righe,
comprese modifiche che non c'entrano nulla con le condizioni di pagamento.

**Ordine obbligato**, da concordare con Tid perché è una decisione di dominio e
non una pulizia tecnica: per ciascuno dei 2 clienti va deciso **quale delle due
condizioni è quella vera** (la coppia legacy vince per D-2, ma questo dice come
si risolve il conflitto a runtime, **non** quale delle due l'operatore intendeva
davvero), si azzera l'altra, e **solo dopo** si accende il guard.

### 4.4 Funzione madre di generazione

Proposta: **`vendite.fn_genera_scadenze_fattura(p_fattura_id bigint)`**
→ `RETURNS TABLE(deleted_rows int, inserted_rows int)`
più il wrapper di lotto **`vendite.fn_genera_scadenze_lotto(p_lotto_id bigint, p_batch_size int DEFAULT 1000)`**
→ `RETURNS TABLE(fatture_count int, deleted_rows int, inserted_rows int)`.

È **la stessa coppia** (per-fattura + wrapper batched di lotto) di
`fn_ricalcola_riepilogo_iva_fattura` / `fn_ricalcola_riepiloghi_iva_lotto`: il BE
può clonare handler e wrapper senza inventare nulla.

> ⚠️ **Con D-7 il generatore NON risolve più nulla.** Il termine è già stato
> risolto a monte, nella chiave di aggregazione, e **scritto in testata** da
> `fn_get_or_create_fattura_header` (§4.2). Il generatore **legge**
> `fatture.termine_pagamento_id` e si limita a calcolare le date e gli importi:
> se lo ri-risolvesse, due punti del sistema potrebbero dare risposte diverse
> sulla stessa fattura. Se al momento del task il termine in testata è NULL, è un
> errore di ordine dei passi (`E_SCADENZE_TERMINE_MANCANTE`), non un caso da
> sanare indovinando.

Comportamento richiesto:

1. **legge** `fatture.termine_pagamento_id` (+ la coppia legacy se la chiave l'ha
   usata) e **scrive** `termine_pagamento_snapshot`: jsonb con i parametri
   effettivamente applicati (numero rate, tipo offset, intervallo, primo offset,
   ripartizione, arrotondamento — oppure `{tipo_gg_scadenza_ft, nr_giorni_scadenza}`
   per il percorso legacy) e l'indicazione di **da dove** è stato risolto. È lo
   snapshot che rende la fattura indipendente da modifiche successive al catalogo
   dei termini;
2. **genera le rate** in `vendite.fatture_scadenze`, `DELETE + INSERT` per
   `fattura_id` (idempotenza: il task può essere rieseguito), `numero_rata`
   progressivo da 1;
3. **base di ripartizione = `fatture.totale_a_pagare`** (vedi §5.1);
4. **`Σ importo` deve quadrare** con la base: la differenza da arrotondamento va
   **sull'ultima rata**;
5. **popola `meta`** con almeno `{"modalita_codice": "...", "termini_codice": "..."}`
   — ⚠️ **contratto d'interfaccia**: `meta.modalita_codice` è già letto dal
   contesto PDF (`fattura_document_context_builder._shape_scadenza`);
6. per il percorso **coppia legacy** (2a): **una sola rata**, data =
   `fatture.data + nr_giorni_scadenza`, spostata a **fine mese** se il tipo è
   fine-mese, importo = intera base;
7. errori di dominio via `script.fn_log_and_raise_error` con codici
   distinguibili (vedi §4.5).

### 4.4-bis ~~Come la testata rappresenta il percorso legacy~~ — ELIMINATA

> 🔴 **Rev. 2026-07-30.** Questa sezione esisteva **solo** per rappresentare il
> percorso legacy in testata. Con D-I il percorso legacy non c'è più: la
> contraddizione che risolveva **non può più nascere**, e
> `fatture.giorni_pagamento` / `fine_mese` si eliminano insieme a lei.
> Il generatore ha **un solo ramo**: legge `termine_pagamento_id`, e se è NULL
> è `E_SCADENZE_TERMINE_MANCANTE` senza ambiguità da distinguere.
> Il testo sotto è conservato come storia — resta un buon esempio di
> contraddizione trovata in revisione.

**Difetto trovato nella revisione del 2026-07-29, nella prima stesura di questo
brief.** Due sue affermazioni non stanno insieme:

- §4.4 punto 6 e la catena di §4.2 prevedono il **percorso coppia legacy**, in cui
  la condizione **non è** un `termine_pagamento_id`;
- §4.5 prescrive `E_SCADENZE_TERMINE_MANCANTE` quando
  `fatture.termine_pagamento_id` è NULL.

Sul percorso legacy quella colonna è NULL **legittimamente**. Preso alla lettera,
il guard avrebbe fatto fallire **ogni fattura di un cliente con la coppia legacy**
— cioè, sui dati attuali, tutte quelle dei 2 clienti di §2-bis. La prima stesura
diceva che il generatore legge «`fatture.termine_pagamento_id` (+ la coppia legacy
se la chiave l'ha usata)», ma **non diceva da dove**: senza una rappresentazione in
testata, il generatore non ha modo di leggerla, e `NULL` è ambiguo fra «percorso
legacy» e «termine non risolto».

**Soluzione — e chiude anche §5.5.** `vendite.fatture` **ha già** le due colonne
che servono, verificate nella doc auto-generata:

| Colonna | Tipo |
| --- | --- |
| `giorni_pagamento` | `smallint` |
| `fine_mese` | `boolean` |

`fn_get_or_create_fattura_header` le **valorizza** quando la risoluzione ha preso
il percorso legacy (esattamente come valorizza `termine_pagamento_id` quando ha
preso quello strutturato). La testata porta così la condizione **completa e non
ambigua**, e il generatore trova tutto ciò che gli serve in un posto solo:

| Stato della testata | Significato | Comportamento del generatore |
| --- | --- | --- |
| `termine_pagamento_id` NOT NULL | percorso strutturato | N rate secondo `config.termini_pagamento` |
| `termine_pagamento_id` NULL **e** `giorni_pagamento` NOT NULL | percorso legacy | **una** rata (§4.4 punto 6), `fine_mese` decide lo spostamento |
| **entrambi NULL** | termine davvero non risolto a monte | `E_SCADENZE_TERMINE_MANCANTE` |

⚠️ **Chi scrive è la testata, non il generatore.** È il principio già stabilito in
§4.4: il generatore **legge e non risolve**. `giorni_pagamento`/`fine_mese` sono
input per lui, non output — se li scrivesse lui, tornerebbero a esistere due punti
che rispondono sulla stessa fattura.

> Nota di coerenza: la stessa tripla `(termine_pagamento_id, giorni_pagamento,
> fine_mese)` è l'elemento aggiunto alla chiave di aggregazione (§4.2). Chiave,
> `WHERE` del lookup e testata parlano quindi **la stessa lingua**, che è ciò che
> rende verificabile l'invariante «ogni elemento della chiave compare nel lookup».

### 4.5 Conflitti e casi che devono FALLIRE (non indovinare)

Il task gira per lotto ma il BE lo eseguirà **per fattura** dove serve la
granularità: un conflitto deve produrre un errore **della singola fattura**, così
il lotto prosegue sulle altre e l'operatore vede quali fatture sono bloccate.
> 🔄 **Rev. 2026-07-30 — due righe della tabella cambiano.**
>
> - **`totale_a_pagare` NULL o ≤ 0**: l'errore vale **solo su NULL**. I fondi
>   sono «addebiti/**accrediti**» e si sottraggono, quindi `= 0` (fattura coperta
>   da acconti) e `< 0` (saldo a favore) sono **documenti legittimi** → nessuna
>   rata, nessun errore, e un log **non critico** sul negativo. Prove: la
>   funzione dei totali tratta esplicitamente il caso negativo in ogni ramo di
>   arrotondamento, e `CHECK (importo >= 0)` su `fatture_scadenze` ha già deciso
>   che un documento a credito non si rateizza. Un errore critico qui bloccherebbe
>   il lotto al primo cliente con acconto capiente. Rif. D-D, C-4.
> - **Fattura già numerata**: lo scenario **non è raggiungibile** dal giro
>   automatico (il runner riparte dallo step corrente o dal successivo, mai
>   indietro). Il presidio si fa comunque, ma **diviso**: il **wrapper di lotto
>   filtra e salta** con log non critico, la **funzione per-fattura solleva**.
>   Rif. D-F, C-8.
> - `numero_rate < 1` è già impedito da `chk_termini_pag_numero_rate_pos`: quel
>   ramo di `E_SCADENZE_TERMINE_INVALIDO` è codice morto. Rif. C-5.

Codici proposti (da registrare come da convenzione):

| Caso | Comportamento |
| --- | --- |
| `termine_pagamento_id` **e** `giorni_pagamento` **entrambi** NULL in testata (§4.4-bis) | errore `E_SCADENZE_TERMINE_MANCANTE` — sintomo di passi fuori ordine, non da sanare indovinando. ⚠️ Il test **non** è sul solo `termine_pagamento_id`: sul percorso legacy quella colonna è NULL legittimamente |
| `totale_a_pagare` NULL o ≤ 0 al momento del task | errore `E_SCADENZE_BASE_NON_PRONTA` (sintomo di task fuori ordine) |
| `numero_rate` del termine < 1 o parametri incoerenti | errore `E_SCADENZE_TERMINE_INVALIDO` |
| Fattura già numerata (lock §4.6) | errore `E_SCADENZE_FATTURA_BLOCCATA` |

### 4.6 Lock post-numerazione (D-5)

`fatture_scadenze` **non ha** un guard di congelamento (a differenza di
`fatture_righe`, protetta da `trgfn_fatture_righe_guard_congelamento`): oggi le
rate di una fattura DEFINITIVA sono tecnicamente riscrivibili.

Serve un trigger `_a10_` su `vendite.fatture_scadenze` che blocchi
INSERT/UPDATE/DELETE quando la fattura è **oltre EMESSA** (cioè numerata /
definitiva / inviata / registrata), sul modello del guard delle righe, **con lo
stesso bypass** per il percorso di reset (`fn_cleanup_fatture_by_ids` /
`fn_reset_lotto_draft`, che oggi si appoggia alla GUC
`zeroerp.maintenance_reset_lotto_draft`).

⚠️ **Conseguenza sull'ordine**: con il lock attivo, il task **deve** stare in
EMESSA (D-1). In DEFINITIVA la generazione sarebbe rifiutata dal trigger.

> Nota: le FK dei satelliti verso `vendite.fatture` sono **CASCADE** (verificato
> il 2026-07-29 su `fatture_scadenze`, `fatture_indirizzi`, `fatture_righe`),
> quindi il reset di un lotto rimuove le rate insieme alle fatture senza
> orfani e senza violazioni. `fn_cleanup_fatture_by_ids` non le nomina: va bene,
> ci pensa la CASCADE — ma il **lock** deve prevedere quel percorso.

### 4.7 Seed: registrazione del task nella pipeline

Solo **append a CSV esistenti** (loader `runOnChange` + `loadUpdateData`, nessun
changeset loader nuovo):

| File | Riga da aggiungere |
| --- | --- |
| `80_data/sql/dbops/pipeline_task_registry.csv` | task `genera_scadenze_lotto`, `dominio_id = 1` (FATTURAZIONE) — ultimo id occupato: 18 |
| `80_data/sql/dbops/pipeline_task_registry_impl.csv` | `implementation_key = default` → `handler_code = genera_scadenze_lotto_default`, `is_default = true` |
| `80_data/sql/vendite/fatturazione_pipeline.csv` | append all'array `processi` dello step **EMESSA**, **dopo** `ricalcola_iva_lotto`: `{"task":"genera_scadenze_lotto","fase":"Generazione piano rate","params":{"implementation_key":"default","batch_size":1000}}` |
| `80_data/sql/vendite/fatturazione_pipeline_task_policy.csv` | una riga **per pipeline_id** coinvolto: `annullabile = t`, `resume_mode = RESUME_STEP` — ultimo id occupato: 16. ⚠️ **senza questa riga il task non ha task_run né resume** |

### 4.8 ⚠️ Buco indipendente che questo lavoro intercetta: la corsia GIORNALIERO

Il seed di `fatturazione_pipeline` ha **`processi = []` sulla riga id 2
(GIORNALIERO / EMESSA)**. La corsia giornaliera quindi **non esegue** né i fondi
né **`ricalcola_iva_lotto`**: le sue fatture non avrebbero riepilogo IVA né
totali. Verificato sui dati: esistono **solo lotti MASSIVO** (29), nessun lotto
giornaliero è mai stato eseguito → **il difetto è latente, non ancora emerso**.

Impatta questo brief perché il task scadenze va in EMESSA: sulla corsia
giornaliera non girerebbe mai. Inoltre esiste un invariante pgTAP che pretende
processi **non divergenti** fra le due corsie
(`db/pgtap/vendite/test-pipeline-definitiva-numerazione-stampa-v1.sql:16`).

**Va deciso** se allineare la riga id 2 alla id 3 (fondi + IVA + scadenze) o se
la corsia giornaliera salta EMESSA per disegno — nel secondo caso va scritto
**dove** calcola i totali, perché oggi non lo fa nessuno.

---

## 5. Anomalie da correggere (D-6)

### 5.1 Base di ripartizione: `totale_a_pagare`, non `totale_doc`

La doc concettuale `docs/it/dbzero/vendite/manual/fatture_scadenze.md` prescrive
`Σ importo == totale_doc`. **È sbagliato**: con fondi/acconti applicati
`totale_doc` e `totale_a_pagare` divergono, e il residuo
(`pagamenti.fn_get_saldo_fattura`) è calcolato su `totale_a_pagare`. Ripartire
`totale_doc` significherebbe chiedere al cliente più di quanto deve.
→ correggere la doc insieme all'implementazione.

### 5.2 `config.termini_pagamento.unita_intervallo` è morta

Duplica `tipo_offset`, nessun CHECK la usa, e nel seed è incoerente
(`unita_intervallo='G'` su righe con `tipo_offset='F'/'N'`). Il generatore deve
leggere **`tipo_offset`**. → deprecare/rimuovere la colonna, o allineare il seed
e documentare quale delle due è autoritativa.

### 5.3 Semantica `tipo_offset = 'M'` non decisa

`docs/it/dbzero/config/manual/termini_pagamento.md:90` lascia aperto se per i
mesi si fa clamp a fine mese o si tiene lo stesso giorno del mese. Va deciso
**prima** di scrivere il generatore (es. 31/01 + 1 mese = 28/02 o errore?).

### 5.4 `ripartizione = 'LIBERA'` non è rappresentabile

Non esiste tabella figlia per percentuali/date per singola rata: oggi un piano
«30% subito + saldo a 60 giorni» non è esprimibile. → dichiararlo **fuori scope**
oppure modellare `config.termini_pagamento_rate`.

### 5.5 `fatture.giorni_pagamento` / `fatture.fine_mese` — 🔄 SI DEPRECANO DAVVERO

> 🔴 **Rev. 2026-07-30 — questa sezione si ribalta.** Con D-I le due colonne
> tornano inutili e **si eliminano**: era la risposta della prima stesura, ed è
> tornata quella giusta. Servivano solo a rappresentare il percorso legacy, che
> non esiste più (§4.4-bis). La domanda originale — «valorizzarle o
> deprecarle?» — era la domanda giusta: aveva solo bisogno che il percorso
> legacy sparisse per avere una risposta netta.
>
> Il testo sotto è conservato come storia.

#### ~~✅ RISOLTO, non si deprecano~~

Scalari di testata pre-esistenti al modello termini, **mai popolati da nulla**.
La prima stesura chiedeva se valorizzarli «per compatibilità» o deprecarli.

**Nessuna delle due: sono il pezzo mancante di §4.4-bis.** Sono la
rappresentazione in testata del **percorso legacy** — senza di loro
`termine_pagamento_id IS NULL` è ambiguo fra «coppia legacy» e «termine non
risolto», e il guard `E_SCADENZE_TERMINE_MANCANTE` respingerebbe fatture valide.

Non sono quindi un residuo da compatibilità: sono **input del generatore**,
scritti da `fn_get_or_create_fattura_header`. La domanda di §5.5 era la domanda
giusta — aveva solo bisogno di essere collegata al problema che risolveva.

---

## 6. Test pgTAP attesi

> 🔄 **Rev. 2026-07-30.** I punti **4, 5 e 6-bis si eliminano**: presidiavano il
> percorso legacy, che con D-I non esiste. Il punto 1 perde il ramo 2a. In
> compenso il piano ne aggiunge tre che qui mancano: **idempotenza del ricalcolo
> totali** (stesso totale *e* stessa scomposizione), **due fatture stesso BA con
> termini diversi → saldi d'arrotondamento distinti**, e il rifiuto della
> **numerazione incoerente** senza consumare il progressivo.

1. `fn_resolve_termini_pagamento`: un test **per ciascun ramo** della catena §4.2
   — 1 (documento sorgente), 2a (coppia legacy del cliente), 2b (termine
   strutturato del cliente), 3 (default `TP_1RATA`, oggi l'unico coperto).
   ⚠️ Il ramo 1 **non ha dati** da cui partire (0 ordini e 0 preventivi in
   totale, §2-bis): la fixture va costruita da zero. È lo stesso ramo che oggi è
   rotto e mai eseguito — scriverla è il lavoro, non il contorno.
2. **Aggregazione (D-7), i test che contano**: due attività dello stesso BA con
   termini **diversi** → **due fatture**; con termine **uguale** → **una**. Più un
   test che la **riesecuzione** del giro non crei una terza fattura (chiave e
   lookup allineati, §4.2 punto 2).
3. **Chiave ↔ lookup**: un test che asserisca che ogni elemento della chiave
   logica compare nel `WHERE` del lookup — incluso `utility_id` (bug §4.2 punto 3).
4. Precedenza D-2: cliente con **entrambi** i modi impossibile dopo §4.3; cliente
   con solo giorni → rata unica; cliente con solo termine → N rate.
5. Semantica D-3: giorni puri; fine mese (incluso un caso a cavallo d'anno);
   `nr_giorni = 0` respinto dal guard esistente.
6. `fn_genera_scadenze_fattura`: quadratura `Σ importo == totale_a_pagare`;
   ribilanciamento sull'ultima rata (caso non divisibile, es. 100,00 / 3);
   `numero_rata` progressivo; `meta.modalita_codice` popolato.
6-bis. **Testata legacy (§4.4-bis)**: fattura con `termine_pagamento_id` NULL e
   `giorni_pagamento` valorizzato → **una rata**, *nessun* errore. È il test che
   presidia la contraddizione trovata in revisione: senza di esso il guard
   `E_SCADENZE_TERMINE_MANCANTE` può tornare a respingere fatture valide.
   Speculare: entrambi NULL → errore.
7. **Idempotenza**: due esecuzioni consecutive → stesso risultato, nessun
   duplicato (`uq_fatture_scadenze_nr` non violato), `deleted_rows` coerente.
8. Lock §4.6: scrittura su fattura numerata → errore; percorso di reset →
   ammesso.
9. Conflitti §4.5: un test per codice di errore.
10. Seed: presenza e **posizione** del task in `processi` (dopo
    `ricalcola_iva_lotto`) + presenza della task_policy, sul modello di
    `test-pipeline-definitiva-numerazione-stampa-v1.sql`.

⚠️ Le rate generate scatenano `trg_fatture_scadenze_z90_storico_upd_dlt`: ogni
rigenerazione lascia righe in `storico.fatture_scadenze_id`. Atteso, ma da tenere
presente nei test di idempotenza (il conteggio dello storico cresce).

---

## 7. Cosa fa il BE dopo l'apply

Nessuna logica di calcolo in Python. Solo cablaggio, sul modello esatto di
`ricalcola_iva_lotto`:

1. handler `_handle_genera_scadenze_lotto_task` in `pipeline_step_executor.py`
   (+ entry nel `handler_registry`);
2. wrapper `run_genera_scadenze_lotto_task(*, lotto_id, batch_size)` in
   `pipeline_repository.py`;
3. voce in `ALLOWED_TASK_FUNCTIONS` → `vendite.fn_genera_scadenze_lotto`;
4. test unitari dell'handler (run + dry-run) e del wrapper;
5. smoke sul percorso reale (le rate esistono davvero, quadrano, il PDF le
   stampa) — modello: `backend/scripts/tests/smoke-fatturazione-render-stampa.py`.

Il frontend **non richiede lavoro**: il BB `ScadenzeSintesi` e il campo
«Prossima rata» del drawer fattura sono già in esercizio e mostrano `—` finché
le rate non arrivano.

---

## 8. Fuori scope (da tracciare, non da fare qui)

- **Riconciliazione rata ↔ incasso**: `pagamenti.vendite_movimenti` è legato a
  `fattura_id` e **non** a una scadenza; `fatture_scadenze` non ha stato di
  pagamento; lo schema `contabilita` è vuoto. Finché resta così **«quale rata è
  stata pagata» non è una domanda a cui il modello può rispondere**, e nessun
  stato «insoluta/scaduta» va derivato dalle sole date (già documentato nel BB
  `useScadenzeSintesi`). È il prerequisito di solleciti e scadenzario.
- Generazione del blocco `2.4 DatiPagamento` nel payload SDI (abilitata da
  questo brief, ma è lavoro del cantiere SDI).
- `GET /api/portale/scadenze/` del portale clienti.
