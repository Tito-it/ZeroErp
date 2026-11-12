# Brief DB — Dove si addebita il trasporto di un ordine fatturato alla conferma

## ⏭️ Chi riparte — aggiornato al 2026-11-12 (sera)

**Riparte: Tid**, col commit del giro DB 8-septies (`20261112-40`…`-42` e CSV: applicati alle 18:36, corsa pgTAP verde, 2026-11-12); poi BE/FE (§9.10, elenco chiuso) e l'archiviazione.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ DB | analisi delle strade sul modello (2026-11-03) | §5 | — |
| 2 | ✅ Tid | T-4: sì, e prima del trasporto (2026-11-03) | §6.1 | — |
| 3 | ✅ Tid | forma (ii): righe del documento (2026-11-03) | §7.1 | — |
| 4 | ✅ DB | censimento dei lettori di `ordini_righe`, `ddt_righe` e del push (2026-11-03) | §8 | — |
| 5 | ✅ Tid | K-1…K-10 come da proposta, e via allo sviluppo (2026-11-03) | §8.4 | — |
| 6 | ✅ DB | giro 1 scritto e provato prima dell'apply (2026-11-03) | §9 | — |
| 6-bis | ✅ Tid | apply `-16`…`-42`; P-1, P-2 decisi (2026-11-03) | §9.5 | — |
| 6-ter | ✅ DB | P-1, P-2 scritti e provati: `-43`…`-46` | §9.6 | — |
| 6-quater | ✅ Tid | apply `-43`…`-46` (12:03), corsa pgTAP verde (2026-11-03) | §9.6 | — |
| 6-quinquies | ✅ Tid | P-3…P-6 come proposti («procedi», 2026-11-03) | §9.5 | — |
| 7 | ✅ BE | causale dell'onere nel push, ordine delle righe dalla sezione, codici nuovi (2026-11-03) | §9.3, §9.8, §9.9 | — |
| 8 | ✅ FE | chiavi i18n, date e evasione sull'onere (2026-11-03) | §9.4, §9.9 | — |
| 8-bis | ✅ DB | `e_onere` e `causale_onere_id` in `vw_articoli_dettaglio` (`-53`, 2026-11-03) | §9.9 | — |
| 8-ter | ✅ BE / FE | colonne nel picker e nel dettaglio; date spente sulla riga nuova; P-6 (2026-11-03) | §9.9 | — |
| 8-quater | ✅ BE / FE | rilettura critica del codice del giro: tre correzioni, due estrazioni (regola del 2, ok Tid), il perché sull'interruttore magazzino (2026-11-03) | §9.9 | — |
| 8-quinquies | ✅ DB | `onere_in_bolla` in `vw_ordini_righe_dettaglio` (`-65`, applicato, su `Tito-dev`, 2026-11-03) | §9.9 | — |
| 8-sexies | ✅ FE | «Genera DDT»: oneri da passare e già partiti, ognuno nella sua nota (2026-11-03) | §9.9 | — |
| 9 | ✅ DB | giro 2: seed TRASPORTO, guide, T-1…T-3 riletti (2026-11-03) | §10 | — |
| 10 | ✅ Tid | T-3 bis come da proposta; migrate dei seed (2026-11-03) | §10.2 | — |
| 11 | ✅ DB | T-3 bis: `-47`, `-48`, pgTAP, guide; applicati (12:33) | §10.2 | — |
| 12 | ✅ Tid / DB | corsa pgTAP del giro 2 verde (Tid); commit dei giri 1 e 2 (2026-11-03) | §10.4 | — |
| 12-bis | ✅ DB / Tid | richiesta BE §9.8: `-49`…`-52`, applicati, pgTAP verdi, committati (2026-11-03) | §9.8 | — |
| 13 | ✅ Tid | commit di BE e FE del §9.9 (`67aafefe87`, PR #28, 2026-11-03) | — | — |
| 14 | ✅ Tid | 8-septies: la causale nella vista; A-10 resta («bloccata se usato») (2026-11-04) | §9.10 | — |
| 14-bis | ✅ Tid | C-1 come da proposta, e via allo sviluppo (2026-11-12) | §9.10 | — |
| 15 | ✅ DB | `causale_onere_codice_interno` e `causale_onere_descrizione` in coda a `vw_articoli_dettaglio`: `20261112-40` scritto e provato (2026-11-12) | §9.10 | — |
| 15-bis | ✅ Tid | C-2, C-3 come da proposta; il picker dal lookup generico (2026-11-12) | §9.10 | — |
| 15-ter | ✅ DB | C-2 `-41` (vista per il lookup) + seed `tabelle_gestibili`; C-3 `-42` (guard) + codice; scritti e provati (2026-11-12) | §9.10 | — |
| 15-quater | ✅ Tid | apply di `-40`…`-42` e dei CSV (18:36), corsa pgTAP verde (2026-11-12) | §9.10 | — |
| 15-quinquies | Tid | commit del giro DB su `dev/db-tid` | — | — |
| 16 | BE / FE | le due colonne nominate; JOIN del picker oneri ritirato; causale nel form articolo (libera in inserimento, spenta se bloccata), picker delle sole causali libere | §9.10 | 15-quater |
| 17 | Tid | archiviazione del brief | — | 16 |

Decisioni aperte di Tid: nessuna. Lavoro da committare: `20261112-40`…`-42`; CSV `codici_errore`, `messaggi_errore` (id 1482), `tabelle_gestibili` (id 94); pgTAP `catalogo/test-vw-articoli-dettaglio-e-onere-v1` (esteso) e `catalogo/test-causale-onere-assegnabile-v1` (nuovo); manual di `vw_articoli_dettaglio`, `vw_causali_onere_assegnabili` (nuova), `trgfn_articoli_guard_onere_natura`; questo brief.

> **Chi scrive:** team DB (`dev/db-tid`), 2026-10-13. **A chi:** Tid, poi il team DB.
> **Origine:** decisione A-9 di Tid (2026-10-12) in
> [brief-db-articoli-ammessi-per-documento](../work-done/brief-db-articoli-ammessi-per-documento.md) §8.6:
> il caso esce da quel brief e si progetta qui.

## 1. Il caso

Un ordine di vendita si fattura in due modi (`vendite.ordini.fatturazione_trigger`):

* **alla consegna**: la bolla porta la merce in una commessa (`vendite.fn_ddt_push_diagnosi`), e
  in commessa si aggiungono servizi e addebiti, compreso il trasporto, con la porta degli oneri
  (`vendite.fn_aggiungi_onere_commessa`);
* **alla conferma**: si fattura dall'ordine, e la commessa non c'è (`DDT_FATTURA_DA_ORDINE`: la
  bolla non transita mai in commessa).

Con le regole del brief d'origine (D-1, D-2) l'ordine e la bolla ammettono **solo merce**. Nel
secondo caso, quindi, un trasporto da far pagare al cliente non ha un posto.

## 2. I fatti di struttura (2026-10-13)

* **Il trasporto sulla bolla è un dato di testata**, non una riga: `vendite.ddt.causale_trasporto_id`,
  `vendite.ddt.modalita_addebito_trasporto_id`.
* **Fra le causali onere non c'è il trasporto** (seed `80_data/sql/config/causali_onere.csv`:
  senza contratto, trasferta, urgenza, spese amministrative, penale).
* **L'articolo-onere** (`catalogo.articoli.causale_onere_id`, 1:1 con la causale) ha la natura di
  default, che è `MERCE` (`natura_vendita_id NOT NULL DEFAULT 1`), con `e_cessione_beni = true`.
  Nessun vincolo lo impedisce. Il vincolo «un articolo-onere non è MERCE» lo introduce il brief
  d'origine (A-9); questo brief lo dà per fatto.

## 3. Le strade (da valutare, nessuna scelta qui)

| | Forma | A favore | Contro |
| --- | --- | --- | --- |
| **a** | articoli-onere ammessi sulle righe d'ordine, come eccezione a «solo merce» | nessun dato nuovo | porta gli oneri su un documento che oggi non li conosce; la riga d'ordine si evade a magazzino, l'onere no |
| **b** | importo (o articolo) di trasporto sulla testata dell'ordine, aggiunto dalla fatturazione | il trasporto è un dato di testata anche sulla bolla | tocca testata, totali e fattura |
| **c** | l'ordine con trasporto si fattura alla consegna (via commessa) | nessuna modifica al modello | è un limite operativo, non una soluzione: va almeno scritto in guida |

## 4. Da decidere (Tid)

| # | Domanda |
| --- | --- |
| **T-1** | Quale delle strade del §3 (o un'altra)? |
| **T-2** | La causale onere «trasporto» va aggiunta al catalogo? |
| **T-3** | La modalità di addebito del trasporto della bolla (franco, assegnato…) deve guidare l'addebito anche sull'ordine? |

> Il §5 riformula le domande: le risposte vanno date lì (§5.4).

## 5. Analisi sul modello (team DB, 2026-11-03)

### 5.1 La premessa del §1 non regge

Il §1 dice che nell'ordine fatturato alla conferma «la commessa non c'è». Il contratto dice il
contrario:

* `vendite.fn_list_ordini_da_pushare` gestisce **solo** gli ordini con
  `fatturazione_trigger = 'CONFERMATO'`, e porta le loro righe in `commesse_attivita` (segmento
  `ORD:<uid>:R:<riga>`, commessa da `vendite.fn_get_or_create_commessa`, legame in
  `vendite.commesse_sorgenti`). Gli ordini `SPEDITO`/`CONSEGNATO` li porta la bolla
  (`fn_list_ddt_da_pushare`).
* `DDT_FATTURA_DA_ORDINE` (`fn_ddt_push_diagnosi`, motivo 6) dice che **la bolla** non transita in
  commessa, perché l'ordine ci è già passato (regola XOR). Non dice che l'ordine non ha commessa. La
  guida [cruscotti-fatturazione](../../guide/cruscotti-fatturazione.md) §4.1 lo scrive già così: «il
  DDT segue l'ordine».

Quindi **in entrambi i modi di fatturazione** la vendita arriva in una commessa, e la porta degli
oneri (`vendite.fn_aggiungi_onere_commessa`, endpoint `commesse/<id>/oneri/`) è disponibile allo
stesso modo. Il caso del §1 non è un buco del modello: il trasporto ha già un posto.

### 5.2 Il buco vero, ed è comune ai due modi

L'onere è **di commessa, non di documento** (sourceless per progetto: gruppo fatturabile
`MAN:<commessa_id>`, `fn_build_gruppo_fatturabile_key`). Ne seguono, **sia alla conferma sia alla
consegna**:

* l'emissione mirata di `ORD-xxxx` (o della bolla) **non** prende il suo trasporto: va scelto anche
  il gruppo «Oneri · commessa #n» ([fatturazione](../../guide/fatturazione.md), «L'unità di
  decisione»);
* le origini della fattura non dicono a quale ordine il trasporto appartiene;
* la commessa `AUTO` è condivisa fra i documenti dello stesso BA e perimetro: «il trasporto di
  quell'ordine» non è un dato, è una nota (`meta.motivo_onere`);
* l'onere si aggiunge solo **dopo** il push dell'ordine (prima la commessa non esiste); con
  `fatturazione_immediata` le righe dell'ordine possono essere già fatturate, e il trasporto va in
  una fattura successiva.

Il secondo modo (bolla → commessa) ha gli stessi limiti, già accettati con D-2 del brief d'origine
(Tid, 2026-10-13: «servizi e addebiti passano dalla commessa»). Legare un onere a un documento è
quindi un **tema trasversale** (tutti i documenti che alimentano la commessa), e non si apre senza
l'ok di Tid (AGENTS.md, «Un tema, un brief»).

### 5.3 Le strade del §3, rilette

| | Esito |
| --- | --- |
| **a** (oneri sulle righe d'ordine) | ⛔ è una **revoca** di D-1 (Tid, 2026-10-13: ordine solo MERCE, da ogni sorgente). Da scartare |
| **b** (trasporto in testata d'ordine) | risolve il legame col documento, ma solo per l'ordine: la bolla resterebbe con l'onere di commessa, e con trigger `SPEDITO`/`CONSEGNATO` non si sa quale bolla lo addebiti (spedizioni parziali). Tocca testata, totali, PDF di conferma e push. Sproporzionata rispetto al buco, che è comune ai due modi |
| **c** (fatturare alla consegna) | non serve: il §5.1 mostra che non c'è un limite operativo da aggirare |
| **d** (nuova, **già in servizio**) | il trasporto è un onere della commessa dell'ordine, come per la bolla. Nessuna modifica al modello |

### 5.4 Proposte per Tid

| # | Domanda | Proposta del team DB |
| --- | --- | --- |
| **T-1** | Quale strada? | **d**: l'onere di commessa, in entrambi i modi. Il brief si chiude con la correzione della premessa, un presidio pgTAP e la guida |
| **T-2** | Causale onere «trasporto» a catalogo? | **Sì**, `TRASPORTO` in `80_data/sql/config/causali_onere.csv` (catalogo di sistema). L'articolo-onere (prezzo, IVA, natura non MERCE per A-9) resta anagrafica dell'azienda, non seed |
| **T-3** | La modalità d'addebito guida l'addebito? | **No.** Sta sulla bolla, l'ordine di vendita non ce l'ha; e non dice se il trasporto si rifattura: `FRANCO` = lo paga il mittente (che può rifatturarlo o no), `ASSEGNATO` = lo paga il destinatario al vettore. Al più `ASSEGNATO` + onere `TRASPORTO` è un'incoerenza, ma l'onere è di commessa e non vede la bolla: un controllo oggi non ha dove agganciarsi (vedi T-4) |
| **T-4** (nuova) | Un onere si può legare a un documento della commessa (gruppo e origini = quel documento)? | **Non in questo brief.** È il buco del §5.2, comune a tutti i documenti che alimentano la commessa, e rompe l'invariante «ONERE è sourceless» (`chk_commesse_attivita_sorgente_pair`, gruppo `MAN:`, lettori di `sorgente_*` da censire). Se Tid lo vuole: brief a parte, con il censimento dei lettori di `sorgente_*` |

### 5.5 Piano (se T-1 = d, T-4 = no) — un giro DB, nessun passaggio BE

| Passo | Cosa | Dove |
| --- | --- | --- |
| 1 | Riga `TRASPORTO` nel CSV delle causali onere (upsert esistente, nessun changeSet nuovo) | `80_data/sql/config/causali_onere.csv` |
| 2 | pgTAP di presidio che **costruisce** il caso: ordine `CONFERMATO` → push → commessa → `fn_aggiungi_onere_commessa` con un articolo-onere `TRASPORTO` (non MERCE) → la riga è `ONERE`, sourceless, gruppo `MAN:<commessa>`, e ha la stessa chiave di fattura delle righe dell'ordine (stesso BA, tipo documento, natura) | `db/pgtap/` (BB `dbops.fn_pgtap_crea_ordine_con_righe`) |
| 3 | Guide: [gestione-ordini](../../guide/gestione-ordini.md) («il trasporto si addebita come onere della commessa, nei due modi»; l'onere dopo il push; l'emissione mirata che va chiesta anche per il gruppo oneri) e [fatturazione](../../guide/fatturazione.md) (rimando) | `docs/it/guide/` |
| 4 | Correzione del §1 e archiviazione del brief | `work-done/` |

BE/FE: la porta (`commesse/<id>/oneri/`) c'è già. Resta da chiedere al team, **solo se Tid lo
vuole**, un accesso dal drawer dell'ordine alla commessa (letta da `commesse_sorgenti`): è
comodità, non modello.

## 6. Giro 1 — l'onere legato a un documento (Tid, 2026-11-03)

### 6.1 La decisione

**T-4: sì, e si fa prima** (Tid, 2026-11-03): non siamo in produzione, si sistema il modello e poi il
trasporto si gestisce più semplicemente. Resta in **questo** brief come giro 1: il trasporto ne è il
primo consumatore, e due brief sugli stessi oggetti si pesterebbero i piedi.

### 6.2 Che cosa si revoca (con le date)

È una **revoca parziale** di due decisioni, e va detto:

| Data | Decisione | Dove | Cosa cambia |
| --- | --- | --- | --- |
| 2026-07-21 | la riga onere è **sourceless** (`DIRECT_ENTRY` non serve) | [porta oneri](../work-done/brief-db-immutabilita-quantita-e-porta-oneri.md) §4c.8 | l'onere **può** portare un documento; senza documento resta lecito (onere di commessa puro) |
| 2026-07-28 | **«manuale» = `sorgente_tipo_id IS NULL`**: l'operatore annulla solo le righe senza sorgente; per quelle con sorgente «il rimedio è a monte, sul documento» | [annullamento righe manuali](../work-done/brief-annullamento-righe-manuali-commessa.md) §4c; guard di `vendite.fn_annulla_commessa_attivita` | il criterio va riscritto: «chi ha scritto la riga» e «a che documento si riferisce» diventano **due assi** distinti |

Il punto di fondo: oggi una sola colonna (`sorgente_*`) risponde a due domande, «da dove viene
questa riga» (push del documento) e «a chi si riferisce» (per fatturarla e citarla). L'onere legato
è il primo caso in cui le due risposte divergono: lo scrive l'operatore, ma è *di* un documento.

### 6.3 C-1 — come si corregge un onere legato (decisione di Tid)

| | Forma | Come si corregge | Che cosa costa |
| --- | --- | --- | --- |
| **C-1a** | **eccezione sugli oneri**: l'onere resta una riga scritta dall'operatore, con in più il documento a cui si riferisce | come oggi: annulla l'onere e ne scrivi uno giusto (porta oneri) | riscrivere il criterio «manuale» su `tipo_movimento = 'ONERE'` (o sulla porta che l'ha scritta), non su `sorgente IS NULL`; censire chi oggi usa «sourceless» come sinonimo di «manuale» |
| **C-1b** | **l'onere segue il documento**: il trasporto è un dato del documento (testata), e il push lo porta in commessa come le righe | correggi il documento e il re-push corregge la riga in commessa (finché non è emessa) | un campo trasporto sulla testata di **ogni** documento che lo addebita (ordine, bolla…), nel push, nei totali, nella stampa; con spedizioni parziali va deciso quale bolla lo porta. È la strada **b** del §3 |

**Proposta del team DB: C-1a.** Tiene un solo modo di scrivere un addebito (la porta oneri) e
cambia solo l'etichetta della riga. C-1b sposta il trasporto nel documento, e allora servirebbe per
ogni altro addebito (montaggio, urgenza…): una colonna per causale, che è ciò che le causali onere
hanno evitato. Le due non si escludono per sempre: C-1b si può aggiungere dopo, per il solo
trasporto, sopra C-1a.

### 6.4 Il censimento (prossimo passo DB, dopo C-1)

> ⚠️ **Fotografia del 2026-11-03 (nota del 2026-11-08).** Dopo il giro C.3 di `brief-db-sorgente-documento-e-riga` la
> riga di commessa porta la chiave del documento tipizzata (`sorgente_id` per i tipi a chiave id, `sorgente_uid` uuid
> per gli altri) e la riga in `sorgente_riga`; i lettori sono passati alle colonne del modello. Il censimento che
> segue va riletto su quella struttura prima di riprenderlo.

Gli oggetti che leggono `sorgente_tipo_id`/`sorgente_uid` di `vendite.commesse_attivita` sono circa
35 (doc auto-gen, 2026-11-03). Per ciascuno: che cosa deve succedere a un onere legato. I primi tre
già visti:

| Lettore | Oggi, con un onere legato | Da decidere |
| --- | --- | --- |
| `vendite.fn_ritira_commessa_attivita_da_sorgente` (annullo del documento) | ritirerebbe anche l'onere ancora da emettere | se annullo l'ordine, il suo trasporto se ne va? (probabile sì) |
| `vendite.fn_annulla_commessa_attivita` (guard sulla sorgente) | rifiuterebbe l'annullo dell'onere: «il rimedio è a monte» | C-1 |
| `script.fn_check_sorgente_chiudibile` (documento chiudibile) | un onere già emesso fermerebbe la chiusura del documento | è coerente? |

Gli altri (emissione mirata, origini della fattura, lineage, termini di pagamento, partita merce,
cruscotti, lotti) si censiscono nel giro, con un pgTAP che **costruisce** l'onere legato per ogni
comportamento deciso.

### 6.5 Dopo

* **Giro 1** (DB): porta oneri con il documento facoltativo (fra quelli della commessa), criterio
  «manuale» riscritto, lettori allineati secondo il censimento, pgTAP, guide fatturazione e
  commesse. Richiesta BE/FE: il documento nella porta oneri e nella sua maschera.
* **Giro 2** (trasporto): T-1…T-3 del §5.4 riletti sopra il giro 1. L'emissione mirata di un
  ordine porterà con sé il suo trasporto.

## 7. Proposta di Tid: gli oneri come righe del documento (2026-11-03)

Tid: una colonna per onere vorrebbe una modifica al DB per ogni addebito nuovo. Al posto della
testata, gli oneri come **righe**: (i) una tabella di righe-onere del documento, oppure (ii) le righe
di dettaglio stesse, con l'articolo-onere che le distingue («l'onere è un articolo particolare»).

**Lettura del team DB.** Entrambe risolvono **insieme** T-4 e C-1: la riga-onere arriva in
commessa **dal push**, con il documento come sorgente, quindi gruppo fatturabile, origini e
correzione («si corregge il documento») vengono da sé. La porta oneri di commessa resta, invariata e
sourceless, per gli addebiti che non sono di nessun documento: **la regola del 2026-07-28 («manuale =
sourceless») non si tocca**, e il §6.2 decade. Nessuna colonna per causale: l'onere nuovo è una riga
di `causali_onere` e un articolo.

Il precedente c'è già: il **preventivo** ha righe di nature diverse e le smista per natura
(`vw_preventivi_righe_smistabili_ordine` / `…_commessa`): la merce va all'ordine, il resto in
commessa.

| | (i) tabella righe-onere | (ii) righe del documento |
| --- | --- | --- |
| lettori delle righe (`ordini_righe` 52, `ddt_righe` 51 oggetti, doc auto-gen 2026-11-03) | non toccati per costruzione | vanno censiti: oggi danno per garantito «solo MERCE» (D-1/D-2) — evasione, residuo, stato EVASO, copia in bolla, magazzino |
| infrastruttura (prezzo, IVA, totali, stampa, lock fuori bozza, RLS, audit, API, drawer) | da rifare per ogni documento | c'è già |
| decisione toccata | nessuna | **revoca parziale di D-1 e D-2** (Tid, 2026-10-13: ordine e bolla «solo MERCE»), che diventano «MERCE e oneri» |

**Da decidere ancora, in entrambe:** con l'ordine fatturato **alla consegna**, l'onere scritto
sull'ordine quando va in commessa (al push dell'ordine, o con la prima bolla)? E un onere sulla
bolla, fatturata dall'ordine (XOR), dove va?

### 7.1 Decisione di Tid (2026-11-03)

**Forma (ii): righe del documento.** L'onere è un articolo particolare e **segue la logica degli
articoli**: è l'operatore che lo mette nel documento giusto. Il §6.2 e C-1 decadono; D-1 e D-2
(2026-10-13) diventano «MERCE e oneri».

Ne discendono, sul modello (lettura del team DB, da confermare):

* **nessuna copia o spostamento automatico** dell'onere fra documenti oltre a quelli che valgono per
  gli articoli: fatturazione alla conferma → l'operatore lo mette sull'ordine; alla consegna → sulla
  bolla (o sull'ordine, e allora viaggia nella bolla come le altre righe — da confermare);
* **un onere che non verrebbe mai fatturato si rifiuta**, non si tollera: sulla bolla di un ordine
  che fattura alla conferma (`DDT_FATTURA_DA_ORDINE`) la riga-onere non andrebbe in commessa né
  dalla bolla né dall'ordine;
* la riga-onere **non si evade** a magazzino: niente scarico, niente residuo da spedire, non pesa
  sullo stato EVASO. È il cuore del censimento dei lettori delle righe.

### 7.2 Conferme di Tid (2026-11-03) e piano

* **Ordine → bolla: sì**, l'onere sull'ordine passa nella bolla come le altre righe.
* **Onere che non verrebbe fatturato: si segnala** (forma da fissare: errore che rifiuta, o avviso
  `W_`; proposta DB: errore, perché un addebito perso non lo vede nessuno).
* **L'onere non si evade**: confermato.

Due conseguenze delle conferme, da chiudere nel censimento:

* **una volta sola**: con spedizioni parziali l'onere passa nella **prima** bolla che lo prende e poi
  non più (serve un «già passato» suo, perché il residuo della merce non lo descrive);
* **la segnalazione esenta la copia**: sulla bolla di un ordine che fattura alla conferma la
  riga-onere copiata dall'ordine è lecita (la fattura l'ordine); si segnala solo l'onere scritto
  **a mano** su quella bolla.

| # | Giro | Cosa |
| --- | --- | --- |
| 1 | censimento (DB, analisi) | lettori di `ordini_righe`, `ddt_righe`, copia ordine → bolla, push in commessa: per ognuno il comportamento sulla riga-onere |
| 2 | DB, giro 1 | righe d'ordine e di bolla ammettono gli articoli-onere; esclusi da evasione, residuo, magazzino, stato EVASO; copia nella prima bolla; segnalazione dell'onere non fatturabile; push con il documento come sorgente; pgTAP che costruiscono ogni caso |
| 3 | BE/FE | picker articoli che ammette gli oneri su ordine e bolla, totali, stampa con gli oneri dopo gli articoli (§7.3), messaggio dell'errore |
| 4 | DB, giro 2 | trasporto: causale `TRASPORTO` a catalogo, T-3 riletto, guide (ordini, bolle, fatturazione) |

### 7.3 Segnalazione e stampa (Tid, 2026-11-03)

* **Segnalazione = errore** che rifiuta la scrittura (codice registrato, messaggio che dice dove
  mettere l'onere).
* **Stampa:** nel dettaglio delle righe gli oneri vengono **dopo** gli altri articoli, accorpati.
  Nessuna sezione dedicata, solo l'ordine. Vale per tutti i documenti stampati che possono avere
  oneri, **fattura compresa**.
  * DB: la lettura delle righe espone **se la riga è un onere** (da articolo/causale, o da
    `tipo_movimento` sulla fattura), così il BE non ricostruisce la regola.
  * BE: le righe in stampa le compongono i `*_document_context_builder` (ordine, bolla, fattura…):
    ordinamento merce prima, oneri dopo, con il dato del DB. Template invariati.

## 8. Censimento (team DB, 2026-11-03)

Letti dalla doc auto-generata: i 78 oggetti che leggono `vendite.ordini_righe` e/o `vendite.ddt_righe`,
più gli oggetti a monte da cui dipendono (ammissione, residuo, partita, push, reso, magazzino). Nessun
lettore di `magazzino.*` legge `ddt_righe`. Due premesse corrette strada facendo:

* il rifiuto dei non-MERCE **non** sta in `script.trgfn_righe_natura_vendita` (che scrive e congela la
  natura) ma in `script.fn_check_articolo_riga_su_contesto`, ramo ORDINE/DDT
  (`E_RIGA_NATURA_NON_AMMESSA`); il guard di riga e il picker ne leggono il primo motivo;
* in commessa un ONERE **con** sorgente è già ammesso: il CHECK
  `chk_commesse_attivita_senza_sorgente_onere_rettifica` (`20261012-27`) dice «con sorgente, oppure
  ONERE o RETTIFICA».

### 8.1 Che cosa cambia, per area

| Area | Oggetti | Classe | Che cosa |
| --- | --- | --- | --- |
| **Ammissione** | `script.fn_check_articolo_riga_su_contesto` | ADATTARE | ramo ORDINE/DDT: merce **oppure** articolo con `causale_onere_id`; un servizio qualunque resta fuori. Segue da sé: guard di riga, picker `catalogo.fn_articoli_ammessi`, `catalogo.fn_articolo_righe_vive_non_ammesse` |
| **Catalogo** | `catalogo.trgfn_articoli_guard_onere_natura` | ADATTARE | un articolo-onere non è gestito a magazzino, né composito, né a lotto o seriale. Con questo sono a posto **per costruzione** magazzino, prelievi, scarico, distinta (`fn_ddt_merce_da_movimentare`, `fn_check_ddt_merce`, `fn_posta_ddt`, `fn_cambia_stato_ddt`, `trgfn_ddt_righe_prelievi_guard`, `fn_*_riga_componenti_init`) |
| **Predicato** | BB nuovo «la natura è merce», sulla natura **congelata** della riga | nuovo | oggi la stessa condizione (`destinazione_tipo = 'ORDINE_VENDITA'`) è scritta in linea in almeno cinque oggetti (viste di smistamento del preventivo, `fn_list_preventivi_da_pushare`, la check di ammissione, il guard dell'articolo-onere): il BB nasce e **ritira le copie** nello stesso giro (regola del 2). Su ordine e bolla «non merce» = onere, perché lo garantisce l'ammissione (va scritto nel COMMENT). La causale si legge dall'articolo solo dove serve il suo valore (ammissione, push) |
| **Evasione e stato dell'ordine** | `fn_ordine_ha_residuo_evasione`, `fn_ordine_proietta_stato_evasione` (ramo 1), `fn_situazione_merce_ordine`, `vw_dash_fatturazione_ordini`, `vw_ordini_righe_dettaglio` | ESCLUDERE | l'onere non ha residuo e non decide CONFERMATO/PARZIALMENTE_EVASO/EVASO. Il filtro sul residuo copre a valle genera-bolla, verbi del reso, correzione e ritiro |
| **Partita merce** | `fn_partite_merce` (copre `fn_resi_da_accreditare`, `vw_partite_merce`, il lato partita della diagnosi e della situazione) | ESCLUDERE | filtro in `dr_in`, nei due rami |
| **Reso** | `trgfn_resi_righe_guard_origine_coerente` (nuovo motivo, es. `E_RESO_RIGA_ONERE`); `fn_conferma_reso`, `fn_annulla_reso` | ESCLUDERE | l'onere non si rende. Il `bool_and(reso ≥ quantità)` che porta la bolla a RESO deve ignorare gli oneri, se no una bolla con un onere non va mai a RESO. Con il guard, accredito, riconsegna e coda sono a posto per costruzione |
| **Copia ordine → bolla** | `fn_genera_ddt_da_ordine`, `trgfn_ordini_ful_guard_consistenza`, `script.fn_check_ddt_riga_correggi_qta_evasa` | ADATTARE | §8.2 |
| **Push in commessa** | `fn_list_ordini_da_pushare`, `fn_ddt_push_diagnosi` → `fn_list_ddt_da_pushare` | ADATTARE | l'onere nasce `ONERE` con la causale dell'articolo e la sorgente del documento. Sulla bolla oggi cadrebbe in `DDT_SENZA_PARTITA` e non partirebbe mai: serve il ramo dell'onere (salta la partita, quantità = quella della riga) |
| **Errore 5** | `script.fn_check_ddt_emittibile` (+ capability) | ADATTARE | §8.3 |
| **Stampa e maschera** | `vw_ordini_righe_dettaglio`, `vw_ddt_righe_dettaglio` | ADATTARE | colonna «è onere» (regola di stampa §7.3); residuo ed evasa a NULL sull'onere |
| **Builder pgTAP** | `dbops.fn_pgtap_crea_reso`, `fn_pgtap_crea_ddt_da_ordine` | lieve | prendono «la prima riga»: con un onere al numero 1 sbagliano bersaglio. Filtro merce nel builder del reso |
| Tutto il resto | totali, IVA, lock di bozza, testata, emittente, cliente, lineage, legami, date dei documenti | OK | una riga-onere non cambia nulla |

Da verificare nel giro (non visto dal censimento): chi in commessa legge `tipo_movimento = 'ONERE'` come
«riga della porta manuale» (annullo della commessa per genere, emissione mirata, cruscotti). Con l'onere
**da documento** la stessa etichetta copre due strade.

### 8.2 La copia una volta sola

**Proposta: il legame di evasione esistente** (`ordini_righe_fulfillment`), scritto dalla copia con la
quantità intera dell'onere. Ne vengono, senza codice nuovo: la seconda bolla lo salta (residuo 0); la
diagnosi legge dal legame il trigger dell'ordine, quindi l'onere copiato da un ordine «alla conferma»
non si fattura due volte; prezzo ereditato, cliente, lineage e legami funzionano; annullando la bolla il
legame si ritira e l'onere torna all'ordine. Il costo: «legame di evasione» non vuol più dire solo
merce evasa, e i lettori della **quantità** usano il predicato (sono gli ESCLUDERE del §8.1, che
servono comunque). Un legame nuovo vorrebbe rifare tutti i lettori del legame ordine↔bolla.

In `fn_genera_ddt_da_ordine`: l'onere passa intero; entra nella prima bolla anche se l'operatore non
l'ha selezionato; una bolla di soli oneri dà `E_DDT_NIENTE_DA_EVADERE`. La regola «intero» la tiene il
guard di consistenza del legame, non la madre.

### 8.3 Dove nasce l'errore

Non all'inserimento della riga: nella copia la riga di bolla nasce **prima** del suo legame, e un
guard all'INSERT non distinguerebbe la copia dall'onere scritto a mano. Va **all'emissione** della
bolla, come motivo di `script.fn_check_ddt_emittibile` (lo legge anche la capability, quindi in bozza il
bottone si spegne col motivo). Predicato: riga-onere attiva **senza legame** su una bolla il cui ordine
fattura alla conferma. Codice proposto `E_DDT_ONERE_NON_FATTURABILE`. ⚠️ Oggi la diagnosi legge il
trigger **solo** dal legame: una riga a mano senza legame risulta pushabile; per l'onere senza legame il
trigger va letto dalla sorgente di testata della bolla.

### 8.4 Domande per Tid

| # | Domanda | Proposta |
| --- | --- | --- |
| **K-1** | In commessa l'onere da ordine o bolla nasce come ONERE (con causale) o come riga normale? | ONERE con causale e sorgente (il CHECK lo ammette già) |
| **K-2** | Ordine o bolla con **soli** oneri, nessuna merce: si conferma / si emette? | No: un addebito senza merce si fa in commessa |
| **K-3** | L'onere porta date di consegna? | No (vuote): se no falsa la data minima della lista e il «riga spedita» |
| **K-4** | La copia usa il legame di evasione esistente (§8.2)? | Sì |
| **K-5** | L'onere entra da solo e intero nella prima bolla, anche se non selezionato? | Sì |
| **K-6** | La quantità dell'onere copiato si corregge in bolla? | No (motivo nuovo nella check della correzione) |
| **K-7** | L'errore scatta all'emissione (in bozza si vede come motivo) e non all'inserimento? | Sì (§8.3) |
| **K-8** | È errore anche un onere su una bolla con causale **non fatturabile** (conto visione, campionatura)? | Sì, stesso motivo, anche se copiato dall'ordine |
| **K-9** | Un onere a mano su una bolla di **riconsegna** di un reso (trasporto addebitato) è ammesso? | Sì, se la causale è fatturabile |
| **K-10** | Un onere sul **preventivo** o sull'**offerta** segue la merce nell'ordine? Oggi va dritto in commessa e si fattura anche se la merce non parte | Per ora no (l'operatore lo mette sull'ordine); se sì, cambiano lo smistamento del preventivo e la check dell'offerta |

**✅ Tid, 2026-11-03: K-1…K-10 come da proposta.** Con K-7 la «segnalazione = errore» del §7.3 scatta
all'**emissione** della bolla (in bozza è un motivo che spegne il bottone), non alla scrittura della riga.

## 9. Giro 1 — sviluppo (team DB, 2026-11-03)

Via di Tid il 2026-11-03 («inizia gli yaml da -16»). **`-16`…`-42` applicati da Tid su dbdev il 2026-11-03** (11:52,
`databasechangelog`); `-43`…`-46` (P-1, P-2) applicati alle 12:03. **Corsa pgTAP di Tid verde** (2026-11-03). Nulla committato.

### 9.1 ChangeSet

| # | Oggetto | Che cosa |
| --- | --- | --- |
| `-16` | `script.fn_natura_e_merce` (nuovo) | BB «la natura è merce», sulla natura congelata della riga |
| `-17` | `script.fn_check_articolo_riga_su_contesto` | ordine e bolla ammettono merce **o** articolo-onere; usa il BB |
| `-18`, `-20` | `catalogo.trgfn_articoli_guard_onere_natura` + trigger | usa il BB; regola 2: un onere non è gestito, composito, a lotti o a matricola (`E_ARTICOLO_ONERE_STRUTTURA`); trigger `UPDATE OF` su 6 colonne |
| `-19` | `vendite.vw_preventivi_righe_smistabili_ordine` | la copia in linea passa al BB (stesso risultato) |
| `-22`, `-23` | `fn_ordine_ha_residuo_evasione`, `fn_ordine_proietta_stato_evasione` | residuo e stato solo sulla merce |
| `-24` | `fn_situazione_merce_ordine` (+ COMMENT di `vw_situazione_merce_ordine`) | solo merce |
| `-25` | `vw_ordini_righe_dettaglio` | `e_onere`, `causale_onere_id` in coda; evasa/residua NULL sull'onere |
| `-26` | `script.fn_check_ordine_confermabile` | K-2: `E_ORDINE_CONFERMA_SOLO_ONERI` (guard e capability la leggono già) |
| `-27` | guard nuovo su `ordini_righe` | K-3: `E_RIGA_ONERE_DATA_CONSEGNA` |
| `-30` | `fn_partite_merce` | solo merce |
| `-31` | `trgfn_resi_righe_guard_origine_coerente` | `E_RESO_RIGA_ONERE` |
| `-32` | `fn_conferma_reso`, `fn_annulla_reso` | RESO/CONSEGNATO decisi sulla sola merce |
| `-33` | `script.fn_check_ddt_riga_correggi_qta_evasa` | K-6: motivo RIGA_ONERE (`E_DDT_RIGA_ONERE_NON_CORREGGIBILE`) |
| `-34` | `vw_ddt_righe_dettaglio` | `e_onere`, `causale_onere_id` in coda |
| `-35` | `dbops.fn_pgtap_crea_reso` | prende la prima riga di **merce** |
| `-36`, `-37` | `fn_genera_ddt_da_ordine`, `trgfn_ordini_ful_guard_consistenza` | l'onere passa intero, una volta, anche non selezionato (`E_ORD_FUL_ONERE_NON_INTERO`) |
| `-38`, `-40` | `fn_list_ordini_da_pushare`, `fn_list_ddt_da_pushare` (DROP+CREATE) | `tipo_movimento = 'ONERE'` + colonna `causale_onere_id` in coda |
| `-39` | `fn_ddt_push_diagnosi` | ramo dell'onere (senza partita, dose = quantità); trigger dalla testata per l'onere senza legame |
| `-41`, `-42` | `script.fn_check_ddt_emittibile`, `trgfn_ddt_guard_causale_emissione` | `E_DDT_EMISSIONE_SOLO_ONERI` (K-2), `E_DDT_ONERE_NON_FATTURABILE` (K-7, K-8) |

CSV: 8 codici nuovi in `messaggi_errore.csv` / `codici_errore.csv` (id 1420, 1422, 1423, 1425, 1426,
1428, 1429, 1430), testo di `E_RIGA_NATURA_NON_AMMESSA` e note dei due codici toccati.
pgTAP nuovi: `script/test-fn-natura-e-merce-v1`, `script/test-ammissione-articoli-onere-righe-v1`,
`catalogo/test-articolo-onere-struttura-v1`, `vendite/test-ordine-onere-evasione-v1`,
`vendite/test-bolla-onere-partita-reso-v1`, `vendite/test-ordine-onere-copia-push-v1`,
`vendite/test-ddt-onere-emissione-v1`; aggiornato `vendite/test-vw-righe-dettaglio-sorgente-lista-v1`
(colonne nuove).

### 9.2 Prove (prima dell'apply)

* presidi statici verdi sui 24 changeSet (letterali, runOnChange, preCondition, trigger, grant,
  timestamp, v1) e sul preambolo dei pgTAP;
* l'SQL estratto dei 24 changeSet, in ordine, in **una** transazione annullata su `zeroerp_ruoli` come
  owner: passa;
* i 7 pgTAP nuovi + quello aggiornato, con l'SQL del giro e i codici nuovi in testa, da owner: **113/113**
  (un rosso era della fixture, corretto: l'azione `emetti_ddt` va concessa prima di leggere la
  capability). ⚠️ Da owner, non come applicazione: l'esito che conta è la corsa di Tid dopo l'apply.
* **non regressione**: i 147 pgTAP esistenti che toccano gli oggetti del giro, lanciati da owner senza e
  con l'SQL del giro in testa: **146 identici**, uno cambia ed è quello aggiornato (2 rossi → verde). I
  rossi da owner preesistenti sono gli stessi prima e dopo;
* presidi globali (catalogo messaggi, codici, canale campo, primo motivo, bersagli, viste sotto RLS,
  `plan_cache_mode`, `COST`, riferimenti morti, capability): stesso esito prima e dopo. L'unico rosso
  (`dbops/test-punti-canale-campo-v1` t.17) è precedente e dipende dal `20261103-01` di un altro
  cantiere, non applicato sullo scratch.

### 9.3 Richiesta al BE (bloccante per il push)

`vendite.fn_upsert_commessa_attivita` vuole ONERE ⇔ causale: finché il BE non passa la causale, ogni
riga ONERE del push di ordini e bolle è rifiutata.

1. `backend/apps/vendite/db/commesse_repository.py`: `causale_onere_id` in `_PUSHABLE_SHARED_COLS`;
   `PushableRow.causale_onere_id: int | None` (`_opt_int`, i lister di preventivi, contratti e consumi
   non la espongono); `CommessaAttivitaInput.causale_onere_id: int | None = None`; in `upsert_attivita`
   `p_causale_onere_id => %s` (e nel percorso batch se compone la chiamata); docstring «26 colonne».
2. `backend/apps/vendite/services/commesse_source_handlers.py`, `_build_attivita_input`:
   `causale_onere_id=row.causale_onere_id` (`tipo_movimento` lo legge già dalla riga). Da verificare il
   resolver di prezzo su un articolo-onere.
3. ~~Stampa (§7.3): ordinamento nei `*_document_context_builder`~~ → sostituito dal §9.8: l'ordine lo
   dà il DB con `sezione_documento`.

### 9.4 Richiesta al FE

* picker: gli oneri compaiono già su ordine e bolla (la lettura è la stessa check);
* i18n: `vendite.ordini.azione_reason.solo_oneri`, `vendite.ddt.azione_reason.solo_oneri`,
  `vendite.ddt.azione_reason.onere_non_fatturabile`, `vendite.ddt.correggi_qta_evasa_reason.riga_onere`,
  `vendite.ordini.data_consegna_confermata_reason.riga_onere` (`-46`),
  `vendite.ddt.azione_reason.trasporto_non_dovuto` (`-47`);
* dettaglio riga: sull'onere niente date di consegna e niente evaso/residuo (la vista dà NULL).

⚠️ Fino ad allora il presidio `check-i18n-keys` (pre-commit e CI) è **rosso, atteso**: le sei chiavi
sopra le emette il DB e i locales non le hanno. Il commit DB del 2026-11-03 l'ha saltato solo per quel
hook (`SKIP=check-i18n-keys`); si chiude quando il FE aggiunge le chiavi.

### 9.5 Punti aperti per Tid

| # | Punto | Proposta |
| --- | --- | --- |
| **P-1** ✅ | Regola del 2: «il trigger di fatturazione dell'ordine di testata della bolla» è scritto in linea in due posti, la diagnosi del push (`-39`) e la check di emissione (`-41`) | ✅ Tid 2026-11-03: sì. `-43` BB `vendite.fn_ddt_trigger_ordine_testata`, `-44` diagnosi, `-45` check di emissione (le due copie ritirate) |
| **P-2** ✅ | `script.fn_check_ordine_riga_data_consegna_confermata` dice «la data si cambia» su una riga-onere, ma il guard `-27` la rifiuta: capability e guard dissentono | ✅ Tid 2026-11-03: sì. `-46`: motivo 0 `RIGA_ONERE` col codice del guard, `E_RIGA_ONERE_DATA_CONSEGNA` |
| **P-3** | `vw_ddt_righe_dettaglio.evasa` **resta com'è** sull'onere (decisione 9 diceva NULL): lì non è una quantità, è il flag con cui il form ferma la quantità della riga copiata; con NULL il form la lascerebbe modificare e il DB la rifiuterebbe | tenerla |
| **P-4** | `vw_dash_competenza_gruppi.ha_oneri` conterà anche gli oneri arrivati da un documento: la stessa etichetta copre la porta oneri e il push | da guardare nel giro 2 (o accettare) |
| **P-5** | Il nome `trgfn_articoli_guard_onere_natura` ora giudica anche la struttura | tenere il nome (lo leggono pgTAP e doc) |
| **P-6** ✅ | FE: spegnere nel form articolo i flag magazzino/composito/lotto/seriale su un articolo-onere | ✅ fatto il 2026-11-03 sopra il `-53` (§9.9) |

Dopo P-1/P-2: apply di `-43`…`-46`, corsa pgTAP come applicazione, poi la richiesta BE/FE (§9.3,
§9.4) e il giro 2 (trasporto). P-3…P-6: proposte del team DB, da confermare.

### 9.6 P-1 e P-2 (2026-11-03)

L'apply di `-16`…`-42` è arrivato prima delle decisioni: i changeSet applicati non si toccano
(checksum), P-1 e P-2 sono changeSet **nuovi**.

* `-43` `vendite.fn_ddt_trigger_ordine_testata(sorgente_tipo_id, sorgente_uid)`, BEGIN ATOMIC, INVOKER:
  il trigger di fatturazione dell'ordine sorgente di testata, NULL se la bolla non viene da un ordine.
  Censite le altre letture dell'ordine di testata (archi H della lineage, cliente copiato da
  `trgfn_ddt_normalize`): dicono altro, non sono copie.
* `-44` `fn_ddt_push_diagnosi`: il LATERAL in linea diventa un ramo del CASE che chiama il BB (stessa
  condizione: onere senza legame). `-45` `fn_check_ddt_emittibile`: la SELECT INTO diventa la chiamata.
* `-46` `script.fn_check_ordine_riga_data_consegna_confermata`: motivo 0 `RIGA_ONERE`
  (`E_RIGA_ONERE_DATA_CONSEGNA`, valori e campo come il guard `-27`), prima dello stato; reason_key
  `vendite.ordini.data_consegna_confermata_reason.riga_onere` (al FE).

Prove su dbdev (giro 1 applicato), SQL di `-43`…`-46` in testa, transazione annullata, da owner:
presidi statici verdi; pgTAP `vendite/test-fn-ddt-trigger-ordine-testata-v1` (nuovo, 6/6, col
presidio che le due copie in linea non tornino), `vendite/test-ordine-onere-evasione-v1` (+2 per
P-2: 30/30; **rossi senza `-46`**, verdi con), `test-ddt-onere-emissione-v1` 13/13,
`test-ordine-onere-copia-push-v1` 17/17; non regressione su 55 pgTAP (diagnosi, lister, check di
emissione, capability DDT, date di consegna, presidi globali): 53 identici, i 2 che cambiano sono i
due sopra.

### 9.7 Chiusura del giro 1 lato DB (2026-11-03)

`20261103-16…-46` applicati su dbdev (`databasechangelog`: `-16…-42` alle 11:52, `-43…-46` alle
12:03); corsa pgTAP di Tid verde, come applicazione. Restano:

* **BE (§9.3), bloccante**: senza `causale_onere_id` nel push, `fn_upsert_commessa_attivita` rifiuta
  ogni riga ONERE che arriva da ordini e bolle. Fino ad allora un ordine con un onere non si spinge in
  commessa;
* **FE (§9.4)**: chiavi i18n dei motivi nuovi, dettaglio riga dell'onere;
* **Tid**: P-3…P-6 (§9.5);
* **giro 2**: il trasporto (causale `TRASPORTO`, T-1…T-3 riletti sopra il giro 1) e le guide
  (`gestione-ordini`, `gestione-ddt`, `fatturazione`: gli oneri come righe del documento).

## 10. Giro 2 — il trasporto (team DB, 2026-11-03)

«Non abbiamo produzione, procedi» (Tid, 2026-11-03): P-3…P-6 passano come proposti (§9.5; P-6 resta
facoltativo per il FE), e si apre il giro 2. Il BE si allinea dopo (§9.3): fino ad allora il push degli
oneri si rompe, ed è accettato.

### 10.1 T-1…T-3 riletti sopra il giro 1

| # | Esito |
| --- | --- |
| **T-1** | chiusa dal giro 1: il trasporto è una **riga-onere** del documento (né a, né b, né c del §3) |
| **T-2** | ✅ causale `TRASPORTO` (id 6) in `config/causali_onere.csv`, articolo-onere `ONERE_TRASPORTO` (`…00e6`, NR, IVA 22%, servizio una tantum) in `catalogo/articoli_onere.csv`, regole di fatturazione in `vendite/articolo_regole_onere.csv` (senza, l'onere non arriva in fattura). Loader esistenti, `runOnChange`: nessun changeSet nuovo. Righe provate su dbdev contro i guard del giro 1 (transazione annullata) |
| **T-3** | **riaperta**: col giro 1 il controllo ha dove agganciarsi (§10.2) |

### 10.2 T-3 bis — la modalità di addebito e l'onere di trasporto (decisione di Tid)

La modalità sta sulla bolla (`vendite.ddt.modalita_addebito_trasporto_id`); l'ordine di vendita non
l'ha. `FRANCO` = il trasporto lo paga il mittente, che può rifatturarlo o no: nessuna regola.
`ASSEGNATO` = lo paga il destinatario al vettore; `TERZI` = lo paga un terzo. In questi due casi un
onere **di causale `TRASPORTO`** sulla bolla (scritto o copiato) addebiterebbe al cliente un trasporto
che non paga a noi.

**Proposta del team DB:** errore all'emissione, motivo di `script.fn_check_ddt_emittibile` come gli
altri del §8.3 (la capability spegne «Emetti» col motivo). Codice nuovo, causale letta per
`codice_interno` (`TRASPORTO`), non per id. Alternativa: avviso `W_` che non ferma.

**✅ Tid, 2026-11-03: come da proposta.** Fatto:

* `-47` `script.fn_check_ddt_emittibile`: punto 3-quater `E_DDT_TRASPORTO_NON_DOVUTO` (id 1431,
  CONFLITTO_STATO; reason `TRASPORTO_NON_DOVUTO`, reason_key
  `vendite.ddt.azione_reason.trasporto_non_dovuto`, dettaglio `{riga_id, riga_nr, modalita,
  modalita_descrizione}`): la prima riga attiva il cui articolo ha la causale `TRASPORTO`, su una bolla
  `ASSEGNATO` o `TERZI`. `FRANCO` o modalità assente: nessun motivo. Causale e modalità per
  `codice_interno`;
* `-48` `vendite.trgfn_ddt_guard_causale_emissione`: il ramo che lo solleva (il `LOOP` non ha `ELSE`);
* pgTAP `vendite/test-ddt-trasporto-non-dovuto-v1` (8): assegnato, terzi, capability, emissione
  rifiutata; franco, senza modalità e un altro onere senza motivo. Controprova prima dell'apply: senza
  `-47`/`-48` i casi 2–5 sono rossi;
* guida [gestione-ddt](../../guide/gestione-ddt.md) §3.6 e §14; manual delle due funzioni.

Applicati da Tid con i seed del §10.1 il 2026-11-03 (12:33, `databasechangelog`). Dopo l'apply: il
nuovo pgTAP 8/8 e i 55 pgTAP di diagnosi, check di emissione, capability della bolla e presidi
globali con lo stesso esito di prima di `-47`; `test-porta-oneri-v1` e `-giro-completo-v1` verdi col
seed caricato. ⚠️ Prove da owner: l'esito come applicazione è la corsa di Tid.

### 10.3 Fatto nel giro 2

* seed T-2 (§10.1); `vendite/test-porta-oneri-v1` test 3 conta i **sei codici del seed per nome** (prima
  contava tutti gli articoli-onere attivi: rosso al primo onere creato dall'utente). ⚠️ Rosso finché il
  CSV non è caricato;
* guide (stato attuale, 3 novembre 2026): [gestione-ordini](../../guide/gestione-ordini.md) §3.2, §3.6
  (nuova), §10, §13; [gestione-ddt](../../guide/gestione-ddt.md) §3.2, §3.6 (nuova), §11, §14;
  [fatturazione](../../guide/fatturazione.md) «L'unità di decisione» (gli oneri di commessa sono solo
  quelli senza documento); [gestione-commesse](../../guide/gestione-commesse.md) «Annullare una
  commessa» (l'onere di un documento esce col documento, verificato su `fn_documento_legami`).
* debito di commento, non di comportamento: il commento interno di `vendite.fn_documento_legami` dice
  «ONERE: senza sorgente per progetto»; dal giro 1 l'onere di un documento ha la sorgente ed è
  classificato CONSUMO (giusto). Si corregge al primo changeSet che tocca la funzione (✅ Tid, 2026-11-03:
  ok, nessun changeSet solo per il commento).

### 10.4 Chiusura del giro 2 (2026-11-03)

`-47`, `-48` e i seed del trasporto applicati; corsa pgTAP di Tid verde, come applicazione. Commit dei
giri 1 e 2 su `dev/db-tid`: changeSet `20261103-16…-48`, CSV (codici, messaggi, seed degli oneri),
pgTAP, pagine manual, doc auto-generata degli oggetti toccati, guide e questo brief. Fuori dal commit,
perché di altri cantieri o da rigenerare: le pagine di `pagamenti/`, il `20261103-06`, e gli `index`
degli schemi `catalogo`, `script`, `vendite` — la loro descrizione è lo «Scopo» del manual, e in quattro
pagine la riga della data era finita lì (spostata sotto il titolo): si rigenerano alla prossima
generazione della doc.

### 9.8 Richiesta del team BE (2026-11-03) — chiusa

Il BE, preparando il §9.3, ha trovato due mancanze **del DB**. Erano entrambe giuste.

| # | Mancanza | Causa | Risposta DB |
| --- | --- | --- | --- |
| 1 | il push degli oneri resta rifiutato anche col BE allineato | il push non chiama la madre: passa dal wrapper `vendite.fn_batch_upsert_commessa_attivita`, che legge dal JSON tutte le chiavi della madre tranne `causale_onere_id`. Il §9.3 lo dava per «se il batch compone la chiamata»: la compone il DB. Il pgTAP del giro 1 chiamava la madre a mano, per questo non l'aveva visto | `-49`: chiave facoltativa `causale_onere_id` → `p_causale_onere_id` |
| 2 | la fattura non dice quale riga è un onere, e l'ordine delle righe lo decide il BE | il §7.3 lo prometteva («fattura: da `tipo_movimento`») ma `vw_fattura_righe_lista` non lo esponeva; l'ordine del documento (`ordinamento, riga_nr`) tiene insieme kit e plafond | `-50`: in coda `tipo_movimento`, `e_onere`, `causale_onere_id`, `sezione_documento`. `-51`, `-52`: `sezione_documento` anche su ordine e bolla |

**La regola dell'ordine sta nel DB, uguale sui tre documenti**: `sezione_documento` (1 articoli,
2 oneri) è la **prima chiave** dell'ordine del documento — fattura `sezione_documento, ordinamento,
riga_nr`; ordine e bolla `sezione_documento, riga_nr`. Vale a video e in stampa (il BE legge le righe
con la stessa lettura). Una colonna e non un numero di posizione con una funzione finestra: le viste si
leggono anche per una riga sola, e la finestra le farebbe valutare intere. Sulla fattura «è un onere» si
legge dall'**articolo** (la riga di fattura non ha la natura congelata), così è onere anche la
rettifica di un onere; `tipo_movimento` dice il movimento.

Prove (dbdev, transazione annullata, da owner): presidi statici verdi; pgTAP nuovo
`vendite/test-onere-batch-e-sezione-documento-v1` (10/10) che fa il percorso **vero**: ordine →
lister → **wrapper batch** → commessa → fattura → `vw_fattura_righe_lista`. Controprova col vecchio
corpo del wrapper (`20261013-17`): test 1 e 2 rossi. Aggiornato `test-vw-righe-dettaglio-sorgente-lista-v1`
(colonna nuova). Non regressione su 18 pgTAP (viste di riga, fattura, batch, presidi globali): stesso
esito, salvo i due file sopra; un rosso **preesistente** da owner (`test-ddt-righe-evase-dall-ordine-v1`
t.43, la porta che vuole il proprietario della tabella) era rosso anche prima del giro 1.
`-49`, `-50` applicati da Tid alle 13:07, `-51`, `-52` alle 13:14 (`databasechangelog`); **corsa pgTAP di Tid verde**, come applicazione. Committato il 2026-11-03.

**Elenco chiuso per il BE** (sostituisce il punto 3 del §9.3):

1. push: `causale_onere_id` in `_inp_to_jsonb_row` (oltre al §9.3, punti 1 e 2);
2. ordine del documento: `FattureRepository._righe_ordine_documento = "sezione_documento"`,
   `_righe_ordine_documento_extra = ("ordinamento", "riga_nr")`; `OrdiniRepository` e `DdtRepository`
   `_righe_ordine_documento = "sezione_documento"`, extra `("riga_nr",)`. Nessun ordinamento nei
   `*_document_context_builder`: le righe arrivano già in ordine dalla lettura completa.

Fuori elenco, da decidere se servirà: il preventivo (anche lui ammette gli oneri, K-10) ordina per la
sua colonna `ordine`; oggi non è nel perimetro.

### 9.9 BE e FE (team BE/FE, 2026-11-03)

Fatto su `dev/backend-tid`, sopra `20261103-16…-52` (verificati su dbdev prima di partire: wrapper batch
con la causale, `e_onere`/`sezione_documento` sulle tre viste).

| Richiesta | Fatto |
| --- | --- |
| §9.3 punti 1-2, §9.8 punto 1 | `causale_onere_id` in `_PUSHABLE_SHARED_COLS`, `PushableRow`, `CommessaAttivitaInput`, `_build_attivita_input`, `upsert_attivita` (`p_causale_onere_id`) e `_inp_to_jsonb_row` (la chiave del wrapper) |
| §9.8 punto 2 | `_righe_ordine_documento = "sezione_documento"` su ordine, bolla e fattura (extra `riga_nr`; fattura `ordinamento, riga_nr`). Nessun ordinamento nei builder di stampa |
| codici nuovi | policy rigenerate (`genera_error_policies`: i nove codici del giro, nessun altro) e frasi di ripiego; quella di `E_RIGA_NATURA_NON_AMMESSA` allineata («merci e articoli-onere») |
| §9.4 | le sei chiavi i18n (`check-i18n-keys` pulito); form della riga d'ordine senza date sull'onere (da `e_onere`); dialog «Genera DDT» senza le righe-onere, con una nota che passano intere nella prima bolla |
| D24 (`8ac576ec2d`) | tolta l'esenzione di `E_DOC_EMITTENTE_BA_INCOERENTE` da `test_ui_action_e_canale_campi.py` (la chiedeva il test stesso) |

Prove: suite BE sul DB vero (`ZEROERP_TEST_DB_E2E=1`) 7120 verdi; mypy senza rilievi nuovi; smoke
nuovo `backend/scripts/tests/smoke-push-onere-ordine.py` (6/6), che **costruisce** il caso: ordine con
`ONERE_TRASPORTO` alla riga 1 e la merce alla 2 → lister → push dal wrapper batch → in commessa l'onere è
`ONERE`, causale `TRASPORTO`, sorgente l'ordine; la lettura completa e la stampa mettono l'onere dopo la
merce. FE: 1087 test verdi, lint e build puliti.

**Richiesta al DB (8-bis).** Il picker articoli legge `catalogo.vw_articoli_dettaglio`, che non espone
`causale_onere_id`: sulla riga **nuova** il form non sa che l'articolo scelto è un onere, e mostra le date
di consegna (nascono vuote; se l'operatore le scrive risponde `E_RIGA_ONERE_DATA_CONSEGNA`). Proposta:
`causale_onere_id` in coda alla vista (o un `e_onere` dell'articolo). Con quella il FE spegne le date anche
in creazione, e P-6 (flag magazzino/composito/lotto/seriale spenti nel form articolo) ha il dato.

Fuori dal giro, verificato: il prezzo di un articolo-onere nel push resta quello della riga del documento;
il calcolo d'audit del prezzo è facoltativo e sull'ambiente di sviluppo non trova la mappa
categoria→listino alla data dello smoke (avviso, nessun errore: vale anche per la merce).

**8-ter, sopra il `-53` (2026-11-03).** Il DB ha esposto `e_onere` e `causale_onere_id` in coda a
`vw_articoli_dettaglio` (fast-forward di `Tito-dev` su `dev/backend-tid`, colonne verificate su dbdev).

| Chi | Fatto |
| --- | --- |
| BE | le due colonne in `_LOOKUP_ARTICOLI_COLONNE` (i due picker) e in `ARTICOLI_DETAIL_COLUMNS` (lista e drawer). Il filtro `solo_oneri` legge `a.e_onere` e `a.causale_onere_id` dalla vista: ritirato il JOIN sulla base `catalogo.articoli`, che serviva solo a quello; resta il JOIN del vocabolario per la decodifica. Nuovo `test_articolo_e_onere_db.py` (DB vero, 3 test: picker di riga, picker degli oneri, dettaglio), che cade tutto togliendo le colonne |
| FE riga d'ordine | le date di consegna spente anche in creazione, da `e_onere` dell'articolo scelto; scegliendo un onere le date già scritte si svuotano (nascoste ma piene partirebbero al salvataggio). Nuovo `OrdiniRigaForm.spec.js` (3 test) |
| FE P-6 | nel drawer articolo, su un onere magazzino, composito, lotto e seriale sono spenti, anche nella correzione di struttura (il guard non ha porta amministratore), con una nota (`catalogo.hint_onere_struttura`). Il solo componente resta libero. `ArticoloDrawer.spec.js` +2 test |
| FE «Genera DDT» | il filtro delle righe-onere ha il suo spec, `OrdineEvasioneDialog.spec.js` (4 test, dialog e macchina di selezione veri): l'onere non è in tabella e la nota lo conta; la conferma e il payload (`righe` null) contano le sole merci; un ordine con la sola riga-onere da evadere dà solo chiusura. Togliendo il filtro ne cadono 3 |

**8-quater, rilettura critica del codice del giro (2026-11-03).** Il contratto è stato verificato sulla doc
auto-generata: `e_onere`/`causale_onere_id` della vista articoli, `p_causale_onere_id` della funzione
singola e del wrapper batch, la colonna esposta solo dai lister di ordini e bolle, e l'ordine del documento
delle tre viste (`sezione_documento`, poi la posizione della riga; sulla fattura lo spareggio `riga_key` lo
aggiunge il mixin). Nessun difetto lì.

| Chi | Fatto |
| --- | --- |
| FE «Genera DDT» | il conto degli oneri si azzera a ogni lettura: senza ordine, o con una lettura fallita, la nota restava quella dell'ordine aperto prima |
| smoke | `smoke-push-onere-ordine` sceglieva la natura di merce ricopiando la regola (`destinazione_tipo = 'ORDINE_VENDITA'`): ora chiede il predicato del DB, `script.fn_natura_e_merce` |
| regola del 2, FE (ok Tid) | classe `app-dialog-intro` in `main.css` per la frase introduttiva di un dialog di processo: era uno `style` inline copiato quattro volte in tre dialog (`OrdineEvasioneDialog` due, `DdtResoDialog`, `ResoRiconsegnaDialog`), ritirate nello stesso giro; registrata nel catalogo BB frontend |
| regola del 2, smoke (ok Tid) | `data_documento_isolata()` in `_smoke_fatturazione.py` (~14 mesi avanti, al 15): era la stessa espressione in `smoke-push-termine-documento-commessa` e `smoke-push-onere-ordine`, ritirate; registrata nel catalogo BB backend |
| FE P-6 (ok Tid) | sull'onere anche la sezione magazzino del drawer articolo dice perché l'interruttore è spento (`hint_onere_struttura` al posto di `hint_gestito_a_magazzino`); prima la frase stava solo sotto «composito». `ArticoloDrawer.spec.js`: i test 4 e 5 lo verificano |

Prove: BE 135 test verdi sulle sette suite toccate (`ZEROERP_TEST_DB_E2E=1`, 1 skip fra i mockati); FE
verdi le spec di `ArticoloDrawer`, `OrdineEvasioneDialog`, `OrdiniRigaForm` e dei dialog di bolla e reso
toccati, eslint pulito sui file toccati. Non rilanciati gli smoke dopo l'estrazione (scrivono su dbdev): compilano, e chiamano solo il
nuovo helper.

**8-sexies, sopra il `-65` (2026-11-03).** La rilettura critica aveva trovato che «Genera DDT» diceva
«l'onere passa nella prima bolla» anche su un onere già partito: sulla riga-onere la vista non diceva se
era già legato a una bolla (evaso e residuo NULL per scelta, `-25`). Il DB ha esposto in coda a
`vw_ordini_righe_dettaglio` `onere_in_bolla` (vero se l'onere è già partito con una bolla, falso se è da
passare, NULL sulla merce), con la regola della copia nella bolla (fast-forward di `Tito-dev` su
`dev/backend-tid`; colonna `boolean` verificata su dbdev). Il BE non cambia: `list_righe` legge `v.*`.

| Chi | Fatto |
| --- | --- |
| FE «Genera DDT» | gli oneri restano fuori dalla tabella e si contano in due: da passare (`evasione_oneri_nota`, ora «nella prossima bolla»: dopo il ritiro di una riga di bolla l'onere torna da passare, e la bolla dopo non è la prima) e già partiti (`evasione_oneri_in_bolla_nota`, nuova). «Già partito» si legge dalla colonna, mai ricostruito dai legami. `OrdineEvasioneDialog.spec.js` +2 test (6): l'onere partito, un onere partito e uno da passare |

Prove: spec del dialog 6/6, eslint pulito, `check_i18n_keys` pulito.

### 9.10 Giro 8-septies — la causale dell'onere a video (Tid, 2026-11-04)

**Origine.** Tid, 2026-11-04: nella gestione articoli serve vedere la causale dell'articolo-onere,
modificabile in inserimento e bloccata in modifica.

**Decisioni di Tid (2026-11-04).**

1. La decodifica in coda a `catalogo.vw_articoli_dettaglio`, sulla forma di `natura_vendita_*`:
   `causale_onere_codice_interno` (per la logica) e `causale_onere_descrizione` (a video). ⛔ Non
   `causale_onere_codice`: sopra un `codice_interno` mente sulla sorgente (linee-guida-sql §6c,
   guardrail CI `check_naming_stato_codice.sql`).
2. Il blocco in modifica **resta A-10** (`brief-db-articoli-ammessi-per-documento`, 2026-10-13): la
   causale si blocca quando l'articolo è **usato**, come natura, composito, magazzino, lotto e
   matricola, che dicono con lei che cos'è l'articolo. Prima del primo uso cambiarla non rompe
   niente. A DB c'è già tutto: `trgfn_articoli_guard_struttura_se_usato`, il gemello per il form in
   `dbops.lock_columns_conditional` (`20261013-51`), la porta `fn_articolo_correggi_struttura`
   (SUPER_ADMIN).

**DB (dopo il via).** Un changeSet `20_code`: `CREATE OR REPLACE VIEW` con `LEFT JOIN
config.causali_onere` e le due colonne in coda (la vista può solo appendere), più il `COMMENT ON VIEW`
che nomini la decodifica della causale. ⚠️ DDL dalla doc auto-generata **di oggi**, non dal `-53`: la vista
è cambiata dopo, con `20261106-03` (`e_obsoleto`) e `20261110-92` (`has_componenti_alla_data`), e il
commento con `20261112-20` (doc rigenerata il 2026-11-11, prima del `-20`: il commento si rilegge dal
catalogo). pgTAP: le due colonne decodificano un articolo-onere costruito nel test, e sono `NULL` sulla
merce.

**Richiesta al BE.**

* le due colonne in `ARTICOLI_DETAIL_COLUMNS` (lista e drawer) e, se il picker le mostra, in
  `_LOOKUP_ARTICOLI_COLONNE`: la vista le espone, ma finché il BE non le nomina non escono.

**Richiesta al FE.**

* nel drawer articolo la causale si **vede** (`causale_onere_descrizione`), si sceglie in inserimento e
  si spegne quando `lock_columns_conditional` la dichiara bloccata (articolo usato), come gli altri
  campi di struttura;
* in inserimento il picker offre **solo le causali attive non ancora legate** a un articolo: il legame
  è 1:1 (`uq_articoli_causale_onere`). ⚠️ Fatto di struttura (2026-11-04): la violazione di
  quell'indice **non ha un codice registrato** e arriverebbe come 23505 grezzo; se il picker non basta
  a escluderla, il DB la traduce in un codice nel giro (da decidere nello sviluppo).
* scegliendo una causale valgono le regole già a video da P-6 (flag di struttura spenti) e il guard
  `trgfn_articoli_guard_onere_natura` (natura non merce).

**Rilettura del 2026-11-12 (ripresa dopo la sospensione).** Verificato sul repo:

* A-10 regge: `causale_onere_id` è fra le otto colonne della dichiarazione
  `catalogo.fn_articolo_colonne_struttura` (`20261111-34`), che dal `20261111-35` il guard legge nel corpo,
  e fra le regole del form del `20261013-51`; l'etichetta «causale onere» c'è in
  `catalogo.fn_articolo_flag_etichetta` (`-33`). Il DB del blocco non cambia;
* l'indice 1:1 `uq_articoli_causale_onere` ha ancora **nessun codice registrato** (23505 grezzo): resta da
  decidere nello sviluppo, come sopra;
* ⚠️ **una seconda sede della decodifica esiste già nel BE**: il filtro `solo_oneri` di
  `backend/apps/catalogo/db/catalogo_repository.py` (picker della porta oneri) fa `JOIN
  config.causali_onere` ed espone `co.codice AS causale_onere_codice` e `co.descrizione AS
  causale_onere_descrizione`; il FE (`CommessaGestioneDrawer.vue`) legge la sola descrizione, il codice lo
  legge solo `test_articolo_e_onere_db.py`. Con le colonne nella vista quel JOIN è una copia (regola del 2):
  si ritira nel giro BE, come l'8-ter ha ritirato il JOIN su `catalogo.articoli`.

| # | Domanda | Proposta del team DB |
| --- | --- | --- |
| **C-1** | Il picker oneri del BE espone `causale_onere_codice` (il `codice` utente della causale): la vista lo porta anche lei, o il BE lo lascia cadere? | **Lo lascia cadere**: nessuno lo mostra, e la forma di Tid (decisione 1) è quella di `natura_vendita_*`, `codice_interno` + `descrizione`. Il test BE passa a `causale_onere_codice_interno` |

**✅ Tid, 2026-11-12: C-1 come da proposta**, e via allo sviluppo. Il BE lascia cadere `causale_onere_codice`, ritira il JOIN del filtro `solo_oneri` e legge le due colonne dalla vista.

**Fatto (DB, 2026-11-12).** `20261112-40-update-vw-articoli-dettaglio-causale-onere`: corpo dal
`pg_get_viewdef` di dbdev (coincide col `20261110-92`), `LEFT JOIN config.causali_onere` sulla PK (1:1,
nessuna RLS: la vista resta senza `security_invoker`), le due colonne in coda dopo `e_obsoleto`,
`COMMENT` della vista riscritto e `COMMENT` delle due colonne. pgTAP
`catalogo/test-vw-articoli-dettaglio-e-onere-v1` esteso (plan 4 → 7): decodifica sull'onere (la fixture ha
`codice` diverso da `codice_interno`, così un alias sbagliato si vede), NULL sulla merce, posizione dopo
`e_obsoleto`. Manual della vista aggiornato.

Prove (`scripts/prova_changeset.py`, scratch `zeroerp_ruoli` da owner, ROLLBACK): estratto per intero,
catalogo identico dopo; il pgTAP esteso **senza** l'estratto si ferma al test 3 (colonne assenti),
**con** 7/7. Non regressione, stesso esito senza e con: `test-distinta-alla-data-v1` 17,
`test-vw-articoli-dettaglio-bom-capability-v1` 7, `test-articoli-approvvigionamento-v1` 12,
`vendite/test-articolo-ritirato-v1` 17, `rls/test-rls-viste-security-invoker` 7,
`test-non-editable-fields-dal-lock-vivo-v1` 9. ⚠️ Prove da owner: l'esito che conta è la corsa di Tid
dopo l'apply.

**Due buchi trovati scrivendo la richiesta al FE (2026-11-12).** Oggi **nessuno** offre l'elenco delle
causali da scegliere: né un endpoint BE né un picker FE (l'unica lettura delle causali è la decodifica del
picker oneri). E il «solo le causali libere» è una regola (attiva, non legata a un altro articolo):
scritta nel BE sarebbe logica fuori dal DB.

| # | Domanda | Proposta del team DB |
| --- | --- | --- |
| **C-2** | Chi dice quali causali si possono dare a un articolo? | Il DB: una funzione `catalogo.fn_causali_onere_assegnabili(p_articolo_id)` (le attive non legate ad altri articoli, più quella già dell'articolo, così il drawer in modifica la ritrova), letta dal picker. Il BE la espone, il FE la mostra |
| **C-3** | La seconda causale uguale (l'indice 1:1 `uq_articoli_causale_onere`) arriva come 23505 grezzo: si registra un codice? | Sì: il picker non basta (due operatori insieme, l'API diretta). Codice `E_ARTICOLO_CAUSALE_ONERE_GIA_USATA` (DATO_ERRATO, campo `causale_onere_id`, valori: la causale e l'articolo che la porta) dal guard dell'articolo-onere, prima dell'indice |

**✅ Tid, 2026-11-12: C-2 e C-3 come da proposta**, con una correzione su C-2: niente funzione, si usa il
**lookup generico**. Verificato: il lookup (`dbops.fn_get_lookup_codici`, endpoint `core/lookup/codici/`)
non vale solo per `config` (la whitelist `config.tabelle_gestibili` ha righe di nove schemi), ma oggi serve
solo tabelle, e sulla tabella delle causali «libere» non si filtra. Quindi una **vista** sulla forma del
lookup, registrata nella whitelist. Senza parametro la vista non contiene la causale dell'articolo aperto:
il drawer la legge dalla riga dell'articolo (`causale_onere_descrizione`), e su un articolo usato la tendina
è spenta comunque (A-10).

**Fatto (DB, 2026-11-12).**

* `20261112-41-create-vw-causali-onere-assegnabili`: `catalogo.vw_causali_onere_assegnabili` (`id`,
  `codice`, `codice_interno`, `descrizione`, `attivo`), le causali che nessun articolo porta; il filtro
  delle attive lo fa il lookup. Nessuna RLS sotto, niente `security_invoker`, GRANT dai default
  privileges. Seed `config/tabelle_gestibili.csv` id 94: `lookup = true`, `pannello = false`, oggetto
  `(config, causali_onere)`;
* `20261112-42-update-trgfn-articoli-guard-onere-causale-gia-usata`: regola 0 del guard, prima di natura e
  struttura, su `INSERT` e quando la causale cambia: `E_ARTICOLO_CAUSALE_ONERE_GIA_USATA` (DATO_ERRATO,
  campo `causale_onere_id`, valori: codice dell'articolo, causale, codice dell'articolo che la porta;
  messaggio id 1482). Corpo e COMMENT dal vivo (quelli del `20261111-36`); il trigger non cambia
  (`causale_onere_id` è già nell'elenco `OF`). L'indice resta, per due scritture concorrenti;
* pgTAP `catalogo/test-causale-onere-assegnabile-v1` (11); manual della vista (nuova) e del guard.

Prove (`scripts/prova_changeset.py`, scratch da owner, ROLLBACK; i CSV in testa con uno YAML di prova
fuori dal repo, perché i loader non hanno SQL da estrarre): il pgTAP nuovo 11/11; **controprova** senza
il `-42`: rossi i test 6, 7, 9, 11 (i quattro del doppione). Non regressione su 36 pgTAP che nominano la
causale, il guard, il lookup o la whitelist, e su 9 presidi globali (codici conformi, COMMENT al presente,
corpo senza commenti, canale del campo, riferimenti morti, motivi nominati, valori attesi) più
`rls/test-rls-viste-security-invoker`: **stesso esito senza e con**. Rossi preesistenti da owner, uguali
prima e dopo: `config/test-pannello-porta-v1` (3), `vendite/test-fn-partite-merce-chiusura-v1` (1),
`vendite/test-vw-situazione-merce-ordine-v1` (1). ✅ Applicati da Tid su dbdev il 2026-11-12 (`-40`…`-42` alle 18:36, con i seed di `tabelle_gestibili` e dei messaggi, `databasechangelog`); **corsa pgTAP di Tid verde**, come applicazione.

**Elenco chiuso per il BE** (dopo l'apply di `-40`…`-42` e dei CSV):

1. `backend/apps/catalogo/db/catalogo_repository.py`: `a.causale_onere_codice_interno`,
   `a.causale_onere_descrizione` in `ARTICOLI_DETAIL_COLUMNS` (accanto a `a.causale_onere_id`) e in
   `_LOOKUP_ARTICOLI_COLONNE`;
2. stesso file, filtro `solo_oneri`: ritirati il `JOIN config.causali_onere co` e `extra_cols`
   (`causale_onere_codice` non esce più, C-1); resta `a.e_onere` nel `WHERE`. Il commento sulla sonda
   («regge perché il JOIN è 1:1») si aggiorna: quel JOIN non c'è più;
3. `backend/apps/catalogo/tests/db/test_articolo_e_onere_db.py:83`: `causale_onere_codice` →
   `causale_onere_codice_interno`;
4. nessun endpoint nuovo per C-2: la tendina usa il lookup generico, `core/lookup/codici/?rel=catalogo.vw_causali_onere_assegnabili` (la whitelist la legge dal DB);
5. il codice nuovo `E_ARTICOLO_CAUSALE_ONERE_GIA_USATA` nelle policy (`genera_error_policies`: solo questo codice) e la sua frase di ripiego.

**FE:** `CommessaGestioneDrawer.vue` legge già `causale_onere_descrizione`: invariato. Drawer articolo come
sopra: la causale a video (`causale_onere_descrizione`); in inserimento una tendina sul lookup generico
(`rel=catalogo.vw_causali_onere_assegnabili`); in modifica la causale dell'articolo dalla sua riga, e la
tendina spenta quando `vw_non_editable_fields` la dichiara bloccata (articolo usato). Il rifiuto
`E_ARTICOLO_CAUSALE_ONERE_GIA_USATA` arriva sul campo `causale_onere_id` come gli altri errori di campo:
nessuna chiave i18n nuova (non è un motivo di capability).
