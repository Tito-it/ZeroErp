# Brief DB — Il reso confermato e la bolla di ri-consegna nei pgTAP: una strada, non venti copie

## ⏭️ Chi riparte — aggiornato al 2026-10-25

**⏸️ In attesa del giro 5 di [brief-modello-documento-vendita](brief-modello-documento-vendita.md)** (bolla e reso al
modello: stato solo dal verbo, `dbops.fn_pgtap_porta_a_stato` riscritto). Quando è applicato e verde come app,
**riparte il team DB** coi builder del giro D-4 (E-1…E-5 decise, §7.6), sopra il modello nuovo (§7.7).

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ team DB + Tid | Problema, proposta e via (nel brief del giro 1) | §1, §3 | — |
| 2 | ✅ team DB | Censimento dei 32 file che scrivono un reso a mano | §5.1 | 1 |
| 3 | ✅ team DB | I due builder, i presidi, il porting di 29 file, regressione prima/dopo senza differenze | §5 | 2 |
| 4 | ✅ Tid | Apply di `-05`/`-06`, corsa pgTAP come app: verde (2026-10-25) | §5.3 | 3 |
| 5 | ✅ Tid | D-4: le fixture ripetute si fanno in questo brief | §6 | 3 |
| 6 | ✅ team DB | Giro D-4: censimento fine delle cinque strade | §7.1-§7.5 | 5 |
| 7 | ✅ Tid | Decisioni E-1…E-5: come da proposta (2026-10-25) | §7.6 | 6 |
| 7-bis | altra sessione | Giro 5 di brief-modello-documento-vendita applicato e verde (Tid: si aspetta, 2026-10-25) | §7.7 | — |
| 8 | team DB | Giro D-4: i builder decisi, porting, regressione | §7 | 7, 7-bis |
| 9 | **Tid** | Apply del giro D-4, corsa pgTAP come app; archiviazione | — | 8 |

Decisioni aperte di Tid: nessuna. Lavoro da committare: questo documento (il giro del reso è nel commit
`2e1a6aaac`).

> **Chi scrive:** team DB (`dev/db-tid`), 2026-10-25. **A chi:** il team DB; Tid per l'apply.
> **Origine:** giro 2 di [brief-db-pgtap-bolla-e-reso-costruiti](../work-done/brief-db-pgtap-bolla-e-reso-costruiti.md),
> archiviato il 2026-10-25 a giro 1 chiuso (§7 di quel brief), con la decisione D-3 di Tid (la bolla di ri-consegna
> entra qui).
> **Perimetro:** solo DB — i pgTAP (`db/pgtap/`) e i builder di fixture (`dbops`). Nessuna ricaduta su backend o
> frontend, nessun cambio al modello del dominio.
> **Brief vicini verificati:** nessuno aperto sul tema; il giro 1 è chiuso e il suo builder
> (`dbops.fn_pgtap_crea_ddt_da_ordine`) è la base su cui questo si appoggia.

---

## 1. Il problema, in parole semplici

Sopra una bolla consegnata molti test costruiscono un **reso**: la merce che torna indietro. Lo scrivono a mano:
la testata legata alla bolla, la riga legata alla riga della bolla, la conferma (`vendite.fn_conferma_reso`, il
verbo del dominio, che vuole l'azione `conferma_reso`). Il reso ha regole sue — la riga deve corrispondere a merce
davvero consegnata, la quantità non può superarla, la conferma pretende i suoi dati — e ogni file le soddisfa da
sé. Quando una regola cambia, le copie restano indietro in silenzio.

Dopo un reso per ri-consegna, diversi test generano la **bolla di ri-consegna** (`vendite.fn_genera_ddt_riconsegna`)
e le scrivono a mano indirizzo e causale per portarla a consegnata: la stessa trappola d'ordine che il giro 1 ha
tolto alla bolla da ordine (D-3).

⚠️ Del reso il database ha il **verbo di conferma** ma non una madre di creazione: testata e righe in produzione le
scrive il backend (`resi_service`). Il builder le scrive coi suoi INSERT, come i test, e passa dal verbo vero per
la conferma.

---

## 2. Che cosa NON cambia

* Il modello del dominio: nessun guard, nessun verbo, nessuna tabella.
* I test in cui la strada è il caso: le regole del reso, i suoi errori, la conferma dentro `lives_ok`, il reso
  annullato, la riga spenta in bozza, il legame `resi_righe_riconsegne`. Restano scritti a mano.
* Le asserzioni: si cambia la fixture, non ciò che il test prova.

---

## 3. La forma del builder (default approvati col via del 2026-10-25)

`dbops.fn_pgtap_crea_reso(etichetta, ddt_id, quantità, stato, …)`:

* sopra una bolla consegnata (quella di `dbops.fn_pgtap_crea_ddt_da_ordine`, o una che il test passa);
* testata e riga col collegamento alla riga della bolla e alla riga d'ordine che essa evade (dal legame, con un
  ordine dichiarato); la quantità chiesta (default: una parte del consegnato, così il residuo resta misurabile);
* il tipo di reso per codice (`RESO_A_CREDITO`, `RESO_PER_RICONSEGNA`);
* la conferma dal verbo `vendite.fn_conferma_reso` se lo stato chiesto lo vuole (default: confermato);
* **D-3**: a richiesta, la bolla di ri-consegna dal verbo `vendite.fn_genera_ddt_riconsegna`, con ciò che la
  consegna pretende, portata allo stato chiesto per la matrice (o un builder suo, se il censimento mostra che le
  due strade si usano separate).

Da decidere nel censimento, e da scrivere qui: più righe in un reso (riga della bolla e quantità per ciascuna),
più resi sulla stessa riga, l'azione `conferma_reso` concessa dal builder o dal test.

---

## 4. Il materiale del giro 1 (fatto datato, 2026-10-25)

I quattro agenti del porting del giro 1 hanno descritto la strada del reso file per file
([brief del giro 1](../work-done/brief-db-pgtap-bolla-e-reso-costruiti.md) §6.6). In sintesi:

* testata `vendite.resi` (stato DRAFT, sorgente `DDT_VENDITA`, `sorgente_uid` = uid della bolla, `storicizza`
  false); emittente e cliente li mette il normalize;
* righe `vendite.resi_righe` (riga della bolla, `ordine_riga_id` dal legame — in sei file con `LIMIT 1` senza
  ordine —, articolo, descrizione, unità e fattore copiati dalla riga della bolla, quantità, tipo reso);
* conferma da `vendite.fn_conferma_reso`, con l'azione `conferma_reso` concessa prima;
* circa 20 file la ripetono (gruppi B, C, D del giro 1: accrediti, rinunce, motore dei resi, partite e
  situazione della merce, contatori, dashboard); la bolla di ri-consegna con indirizzo e causale a mano in almeno
  quattro (partite merce chiusura, situazione merce chiusura, partite merce dopo nota di credito, contatore).

Il censimento fine — quale blocco di ogni file è una copia e quale è il caso — è il primo passo (§ «Chi riparte»).

---

## 5. Il giro (fatto, 2026-10-25)

### 5.1 I builder

* `20261025-05` — `dbops.fn_pgtap_crea_reso(etichetta, p_ddt_id, p_quantita, p_tipo_reso_codice DEFAULT
  'RESO_A_CREDITO', stato DEFAULT 'CONFERMATO', p_ddt_riga_id, p_ordine_riga_id, p_reso_id, p_data)`. La bolla:
  del test, del reso a cui si aggiunge una riga (`p_reso_id`, finché è in bozza), o una consegnata costruita da
  `dbops.fn_pgtap_crea_ddt_da_ordine`. La testata porta solo sorgente, uid e data: il resto lo mettono i trigger.
  La riga: la riga della bolla (o la prima), la riga d'ordine (o la prima del legame, ordinata), quantità
  operativa (default: metà della riga, arrotondata in su), tipo per codice. La conferma dal verbo, con l'azione
  `conferma_reso` concessa dal builder all'operatore in sessione. Uno stato abortito si rifiuta (l'annullo è del
  verbo `vendite.fn_annulla_reso`), come per la bolla.
* `20261025-06` — `dbops.fn_pgtap_crea_ddt_riconsegna(p_reso_id, stato DEFAULT 'CONSEGNATO', p_resi_riga_id,
  p_quantita, p_data, p_causale_codice DEFAULT 'VENDITA')` (D-3). Separato dal reso: i test fanno più ri-consegne
  dallo stesso reso. Il censimento ha mostrato che la madre copia già causale e indirizzi dalla bolla d'origine:
  quelli che i test riscrivevano a mano erano ridondanti; il builder completa solo i mancanti.
* Presidi `db/pgtap/dbops/test-fn-pgtap-crea-reso-v1.sql` (11 casi; due provano che quantità oltre il consegnato e
  bolla non consegnata le ferma il guard vero, non il builder) e `test-fn-pgtap-crea-ddt-riconsegna-v1.sql` (7).
* Doc: pagine manuali `dbzero/dbops/manual/fn_pgtap_crea_reso.md` e `fn_pgtap_crea_ddt_riconsegna.md`, due righe
  nella tabella dei builder della guida pgTAP.

### 5.2 Il porting

Censimento (fatto datato, 2026-10-25): 32 pgTAP scrivevano una testata di reso a mano. **29 portati**, 3 lasciati
interi (`magazzino/test-ddt-trasferimento-v1`, `vendite/test-esecutivi-ba-coppia-v1`,
`vendite/test-resi-righe-guard-origine-coerente-v1`: il reso è dentro un `throws_*`/`lives_ok` o è la nascita
della testata stessa). Nessuna attesa e nessun `plan` cambiati.

Resta scritto a mano, dentro i file portati, ciò che è il caso: le conferme e gli annulli che il test misura
(e lì la concessione di `conferma_reso` resta esplicita), la riga spenta in bozza, il reso senza righe
(`magazzino/test-reso-carico-v1` 6b), i rientri di magazzino, il legame `resi_righe_riconsegne` scritto a mano,
le ri-consegne in bozza dal verbo dove la bolla appena generata è ciò che si misura (sei file chiamano ancora
`vendite.fn_genera_ddt_riconsegna`, tutti per questo motivo o dentro un `throws_ok`).

**Curato**: `vendite/test-resi-rinunce-fondamenta-v1` era rosso in partenza (6 ok su 11, poi un errore): la fixture
pescava dal database una riga di bolla con capienza e «il primo tipo di reso che riapre il residuo». Sullo scratch
la riga non c'era e il tipo non era quello per ri-consegna. Ora si costruisce col builder: 11/11.

### 5.3 La prova (fatto datato, 2026-10-25, scratch `zeroerp_ruoli` come owner)

* I 32 file del censimento, prima e dopo, in sequenza: **stesso piano, stessi `ok`, stessi `not ok`** in 31; il 32°
  è `test-resi-rinunce-fondamenta-v1`, da rotto a verde. I `not ok` di partenza (test di scope, rossi da owner)
  restano gli stessi.
* Presidi verdi; `dbops/test-riferimenti-morti-v1` e `dbops/test-security-definer-search-path-v1` verdi col changeSet;
  guardrail del preambolo e dei changeSet verdi.
* Tid ha applicato `-05`/`-06` sullo scratch mentre gli agenti provavano: l'ultima regressione è sui builder
  applicati. Non provato: la corsa come app.

### 5.4 Note sui builder, senza azione

* La concessione di `conferma_reso` fatta dal builder vale per tutta la sessione: un file che dopo conferma o
  annulla a mano resterebbe verde anche senza la sua concessione. I file che lo fanno la tengono esplicita.
* Il builder non scrive `storicizza = false` (lo scrivevano le copie a mano): resta il default di tabella, come
  negli altri builder. Nessun esito cambiato.
* Segnalati e lasciati (una copia sola, regola del 2): il magazzino del reso alla nascita (un file), la testata
  senza righe (un caso), la ri-consegna in bozza senza completamenti (è la madre stessa).

---

## 6. Decisione di Tid

**D-4 — le fixture ripetute emerse, fuori dal reso.** Il porting ha trovato altre strade ricopiate che nessun
builder copre:

| Strada | Dove (fatto datato) |
| --- | --- |
| commessa + attività + emissione, con una fattura vera agganciata all'attività | ~6 file (accrediti, rinunce, annulli) |
| ordine confermato senza bolla (testata + riga + conferma) | ~5 file (chiusure, righe evase) |
| la fattura scritta a mano sul segmento della bolla | 2 file (chiusure) |
| la riga aggiunta a mano su una bolla in bozza | 2 file (partite merce, contatore) |
| la bolla senza ordine consegnata a mano (INSERT, indirizzo, tre UPDATE di stato) | 2 file RLS |

Proposta del team DB: un brief suo. **Decisione di Tid (2026-10-25): no — «nessun altro brief, rimane in
questo».** Il perimetro del brief si allarga a queste strade: censimento fine, un builder dove c'è una trappola
d'ordine, le copie ritirate nello stesso giro (§7).

---

## 7. Giro D-4 — le altre fixture ripetute (censimento fatto, 2026-10-25)

Censimento in sola lettura, file per file, copia o caso (fatto datato: i numeri descrivono le copie, non decidono
il lavoro). Il motivo di ogni builder è la **trappola d'ordine** della strada, scritta per ciascuna.

### 7.1 L'ordine confermato con le sue righe

47 file scrivono righe d'ordine a mano: **9 sono il caso** (guard sulle righe, IVA e riepiloghi, natura, lineage,
date di consegna), **5 misti** (la testata è il caso — emittente di default, coppia BA, flag sulla testata,
termini — e righe e conferma sono copia), **~33 copie piene**.

La trappola: la testata nasce in bozza con la data alla nascita (fuori bozza è congelata); il trigger di
fatturazione si riscrive in bozza (il normalize lo eredita dal BA solo all'INSERT); le righe si scrivono in bozza,
con l'IVA (la conferma rifiuta un prezzo senza aliquota) e `qta_operativa` con `quantita`; le date di consegna non
precedono la data dell'ordine; poi la conferma per la matrice.

Varianti vere: stato finale (CONFERMATO, DRAFT con righe, ANNULLATO), trigger, data, quantità e prezzo, numero di
righe (1, a volte 2 o N), sconto (3 file), date di consegna sulla riga (2), articolo del test, `p_ordine_id` sulla
testata del test (5 misti).

⚠️ **Storia**: che `dbops.fn_pgtap_crea_ordine` *non* scriva righe è una decisione registrata (D-1 di
`brief-db-righe-e-componenti-debiti-residui`). Estenderlo la revocherebbe: la proposta è un builder nuovo che lo
compone.

La stessa strada vive **dentro** `dbops.fn_pgtap_crea_ddt_da_ordine` (ramo senza `p_ordine_id`): il builder nuovo
la sostituisce, e la bolla da ordine può allora inoltrare le righe (sconto, più righe) — riconsegna-eredita e
genera-ddt-da-ordine non scriverebbero più l'ordine a mano.

### 7.2 L'attività di commessa emessa, con la fattura vera agganciata

| Variante | Che cosa | File |
| --- | --- | --- |
| V1 | un'attività sul segmento della bolla, emessa, una fattura in bozza con una riga | 8 (`*_fattura` di chiusure, accrediti, rinunce, annulli, ri-consegna dopo nota; il blocco di annullo-commessa-rettifica) |
| V2 | N componenti di kit, una fattura, N righe | 1 (accredito-kit) |
| V3 | attività del builder, testata da `fn_pgtap_crea_fattura`, riga e aggancio | 1 (rls viste fattura) |
| V4 | attività fatturabile scritta a mano, senza emissione | 1 da portare (billing-account guard); in 4 gli stati sono il caso |
| V5 | con lotto: marchio, testata della madre, lucchetto, esito | 3 (reset-lotto-draft, elimina-fattura-da-lotto, esito-gruppi); più riporta-lotto-a-draft, che oggi va in skip perché pesca un lotto |

L'attività è già coperta da `dbops.fn_pgtap_crea_commessa_attivita` (sorgente, quantità, prezzo, articolo) e la
commessa da `dbops.fn_pgtap_crea_commessa(…, p_con_sorgente_root => true)`. Manca la metà **fattura agganciata**,
con la sua trappola: sorgente ROOT prima dell'emissione; l'attività fatturabile letta per `commessa_attivita_id`
(oggi per `segment_key … ORDER BY id DESC LIMIT 1`, che con le rettifiche sullo stesso segmento prende la riga
sbagliata); testata e righe in due istruzioni (sotto RLS); registro coerente con l'emittente; righe finché la
fattura è in bozza, poi lo stato; l'aggancio dopo la riga (il guard ammette solo vuoto → valorizzato). Del
dominio nessuna funzione scrive le righe di fattura (le scrive il backend): il builder fa gli INSERT.

Incoerenze trovate:
* le sette copie `*_fattura` dichiarano la sorgente **COMMESSA** con la chiave della bolla (forma ibrida); annullo-
  commessa-rettifica usa **DDT_VENDITA** come la push;
* un **reset scritto a mano** (annullo-commessa-rettifica, `ann_reset_lotto` di annulla-accredito, test 13 della
  dash competenza) sgancia la fattura senza cancellarla: in annullo-commessa-rettifica proprio sulla riga
  rettificata, uno stato che il verbo vero (`vendite.fn_cleanup_fatture_by_ids`, che lì rifiuta con
  `E_FATTURE_RIGHE_RETTIFICATE`) non produce;
* `ann_reset_lotto` in `rinuncia-gate-accredito` è **definita e mai chiamata** (copia morta).

### 7.3 La bolla senza ordine portata fuori bozza

`dbops.fn_pgtap_crea_ddt` (bozza senza righe, per il magazzino) più `fn_pgtap_porta_a_stato` **non bastano**: manca
il passo con la trappola, la riga. Per uscire dalla bozza una bolla senza ordine pretende la riga, il prezzo sulla
riga (senza ordine non c'è da dove ereditarlo), l'aliquota col prezzo, un articolo merce costruito, il BA, la
causale e l'indirizzo; e se la riga muove merce, il verbo con l'azione `emetti_ddt` invece dell'UPDATE.

Copie: ~12 file (i due RLS a due mondi, causale immutabile, magazzino della testata, articolo ammesso, numerazione,
storia del BA, esecutivi, push delle bolle, righe evase J…); stato d'arrivo CONSEGNATO, EMESSO, SPEDITO o DRAFT con
la riga; causale VENDITA, a volte CONTO_VISIONE; una riga. Caso in ~15 (guard all'INSERT, testate senza BA o senza
causale, righe senza prezzo, magazzino che muove merce).

### 7.4 La riga aggiunta a mano su una bolla in bozza

Nove righe a mano: **7 sono il caso** (sospetto duplicato, riga «in più», natura, porta del verbo, WITH CHECK). Le
due di fixture vogliono «merce senza ordine consegnata», cioè la strada §7.3. Nessun builder per questa strada.

### 7.5 Trovato fuori dalle cinque strade

* `vendite/test-fn-list-ddt-da-pushare-v1`, casi A: la **bolla da ordine scritta a mano** (sorgente, riga,
  legame). Il giro 1 non l'ha vista (non chiama la madre): si porta su `dbops.fn_pgtap_crea_ddt_da_ordine`.
* `vendite/test-resi-rinunce-fondamenta-v1`: la bolla di destinazione della ri-consegna, in bozza, scritta a mano
  sopra un reso in bozza. La madre vuole un reso confermato: è il caso del test, resta.

### 7.6 Decisioni di Tid (2026-10-25: «per le decisioni fai come da tua proposta»)

* **E-1 — l'ordine con le righe.** Proposta: builder nuovo `dbops.fn_pgtap_crea_ordine_con_righe(etichetta,
  stato DEFAULT 'CONFERMATO', ba, p_quantita, p_prezzo, p_articolo_id, p_fatturazione_trigger, p_data_ordine,
  p_righe jsonb, p_ordine_id)` che compone `fn_pgtap_crea_ordine` (D-1 resta: quel builder continua a non scrivere
  righe). `p_righe` per più righe, sconto e date di consegna; `p_ordine_id` per la testata del test.
  `dbops.fn_pgtap_crea_ddt_da_ordine` ci delega la sua copia interna e inoltra le righe.
* **E-2 — la fattura agganciata.** Proposta: builder nuovo `dbops.fn_pgtap_fattura_attivita(p_attivita_ids bigint[],
  stato DEFAULT 'DRAFT', p_lotto_id DEFAULT NULL)`: emette, legge l'attività fatturabile per attività, testata
  (senza lotto da `fn_pgtap_crea_fattura`; con lotto dalla madre `vendite.fn_get_or_create_fattura_header`), righe
  con quantità e prezzo dell'attività, aggancio, stato per la matrice. Copre V1, V2, V3 e **V5 (lotto)**: dentro
  anche il lotto, che cura riporta-lotto-a-draft.
* **E-3 — la sorgente delle attività fatturate.** Proposta: **DDT_VENDITA** (la chiave la compone
  `script.fn_segment_key`), come la scrive la push; la forma ibrida COMMESSA + chiave della bolla delle sette copie
  non la produce nessuna strada del dominio.
* **E-4 — il reset scritto a mano.** Proposta: dove il test vuole una fattura tolta, il verbo vero
  `vendite.fn_cleanup_fatture_by_ids`; dove il verbo rifiuta (riga rettificata), la fixture costruisce uno stato
  che il modello non produce, e il test si riscrive sullo stato che il modello produce (da guardare file per
  file, con le attese dichiarate se cambiano). La copia morta si cancella.
* **E-5 — la bolla senza ordine fuori bozza.** Proposta: builder nuovo `dbops.fn_pgtap_crea_ddt_senza_ordine(etichetta,
  stato DEFAULT 'CONSEGNATO', ba, p_quantita, p_prezzo, p_articolo_id, p_causale_codice, p_data, p_magazzino_id)`,
  gemello di quello da ordine; `dbops.fn_pgtap_crea_ddt` resta la bozza senza righe del magazzino. Merce gestita:
  rifiutata (i test che muovono merce scrivono le righe da sé). Nessun builder per la riga a mano (§7.4).

### 7.7 Perché si aspetta (2026-10-25)

Mentre il censimento si chiudeva, l'altra sessione ha avviato il giro 5 di brief-modello-documento-vendita:
`20261025-07` … `-21` (non applicati quando scritto) mettono su bolla e reso un trigger che vieta l'UPDATE diretto
dello stato, riscrivono sul verbo comune `vendite.fn_cambia_stato_ddt`, `fn_conferma_reso` e `fn_annulla_reso`
(permesso letto dalla matrice) e riscrivono `dbops.fn_pgtap_porta_a_stato` (`-19`). Il giro D-4 tocca gli stessi
punti (la bolla senza ordine passa da `porta_a_stato`, la bolla da ordine si riscrive, ~50 pgTAP in buona parte
gli stessi della loro bonifica). Tid: **si aspetta il giro 5**, poi D-4 sopra il modello nuovo.

⚠️ Alla ripresa: i numeri di changeSet liberi si rileggono (max+1 su tutti i livelli: il giro 5 occupa già
`-07` … `-21`); il censimento §7.1-§7.5 si ricontrolla sui file che il giro 5 avrà portato; i builder del giro 1 e
del reso (`fn_pgtap_crea_ddt_da_ordine`, `fn_pgtap_crea_reso`, `fn_pgtap_crea_ddt_riconsegna`) si riprovano sul
`porta_a_stato` e sui verbi nuovi (per esempio l'azione `conferma_reso` che `fn_pgtap_crea_reso` concede: il
permesso ora lo legge la matrice).
