# Come si scrive un test pgTAP

> **A chi serve**: chiunque aggiunga o modifichi un test in `db/pgtap/`.
> **Da dove viene**: tre giorni di lavoro nell'agosto 2026, e ogni regola qui
> sotto è costata un difetto vero. Storia e misure:
> `docs/it/dev/work-done/brief-db-pgtap-runner-rls-baseline.md`.
> **Ultimo aggiornamento**: 12 novembre 2026

## La cosa da sapere per prima

**I test girano come l'applicazione.** `scripts/testpgtap.sh` si connette come
`zeroerp_app` con il contesto operatore, e **le policy RLS sono attive**.

Fino al 2026-08-07 giravano come owner, che la RLS la salta: in pratica nessun
test verificava una policy. Se trovi un documento — una guida, un commento —
che dice «il pgTAP gira come owner», è vecchio.

**Cosa cambia per te.** Un rosso può essere **un permesso** o **una policy**,
non solo una fixture. E una fixture che scrive dove l'applicazione non scrive
non passa più: è un difetto, non un dettaglio.

## Non partire da zero

```bash
cp db/pgtap/_TEMPLATE.sql.txt db/pgtap/<schema>/test-<cosa>.sql
```

Il template porta il preambolo giusto e, accanto a ogni riga, **perché** c'è.
È lo strumento più utile di questa guida: le regole che si applicano da sole
sono le uniche che sopravvivono.

⛔ **Si parte dal template, non dal file accanto.** Una fixture copiata porta con
sé il suo debito: un test che pesca conto, listino o emittente dal database è
verde solo dove quei dati ci sono, anche se «è lo stile della cartella». Prima
di prendere a modello un altro test lo si cerca in
`db/pgtap/baseline-rossi-ci.tsv`: il modello è un test che il mondo se lo
costruisce. Dal database un test legge solo il catalogo di seed.

## Le tre righe del preambolo

Sono presidiate da `scripts/guardrail_pgtap_preambolo.py`: se ne manca una senza
dichiararlo, la CI si ferma.

| riga | cosa succede senza |
|---|---|
| `BEGIN;` … `ROLLBACK;` | un fallimento a metà lascia i dati di prova nel database, e **la corsa successiva vede un rosso non suo** |
| contesto applicativo | con la RLS attiva le `SELECT` della fixture leggono **zero righe**: le asserzioni finiscono nei rami `skip` e il file diventa **verde per sottrazione** |
| `SET CONSTRAINTS ALL IMMEDIATE` | i **365 vincoli differiti** scattano al `COMMIT`, che qui non arriva mai: non vengono esercitati, e di nuovo verde per sottrazione |

⚠️ **`SET CONSTRAINTS` non va «sempre in testa»**: va **dove l'unità di lavoro è
completa**. Se la fixture crea un padre in un'istruzione e il suo satellite in
quella dopo, in testa fa scattare il vincolo a metà strada. Si sposta dopo
l'ultima coppia — e comunque **prima** di ogni cleanup, o scatta su righe già
cancellate.

⛔ **E se la sposti, la finestra la dichiari**: subito dopo la riga di contesto,
`SET CONSTRAINTS ALL DEFERRED;`. La finestra differita «di default» non è una
promessa di nessuno: su un database vuoto la riga di contesto **costruisce** il
mondo ed esce con i vincoli IMMEDIATE, come ogni helper (sotto, §«Il mondo si
costruisce»). Un file che fra il contesto e il proprio `SET CONSTRAINTS ALL
IMMEDIATE` costruisce una saga contando sul default è **verde su dev e rosso in
CI** — e lo è solo quando è il primo della corsa, che è il modo peggiore di
esserlo: `anagrafiche/create-cliente` il 2026-09-21, «due volte in due giorni»
senza riprodursi da solo.

### Se una di queste non ci può stare

Si **dichiara**, non si spiega e basta:

```sql
-- pgtap-contesto: escluso — <perché>
-- pgtap-differiti: escluso — <perché>
```

Una ragione in prosa non è leggibile da un cancello, e soprattutto **non
distingue «escluso apposta» da «dimenticato»**. Nell'agosto 2026 la famiglia
`rls/` fu esclusa **in blocco** dal contesto: almeno un file non ne aveva
diritto e girava con 4 asserzioni su 5 in `skip`, per settimane.

## Le fixture

### L'emittente non si pesca, si deriva

Un documento appartiene all'emittente di **chi agisce**, e le policy
`ef_whitelist` lo pretendono. Due convenzioni, due helper:

```sql
emittente_fiscale_id        = script.fn_pgtap_emittente_operatore()      -- preventivi, ordini, ddt, resi
emittente_soggetto_ruolo_id = script.fn_pgtap_emittente_sr_operatore()   -- commesse, fatture, lotti
```

⚠️ **Non è una scorciatoia per far passare la RLS**: rende scrivibile ciò che
l'applicazione scriverebbe. Una fixture che ha bisogno di un emittente *diverso*
sta collaudando la separazione fra emittenti — quella non si aggira, si
costruisce cambiando contesto.

⚠️ **I due helper sollevano se non c'è nessun emittente**, e un errore fuori da
`throws_ok` chiude la transazione: uno `skip()` scritto più sotto non viene mai
raggiunto. Un file che li usa ha prima costruito il mondo, o ha la riga di
contesto senza argomento, che lo costruisce. ⛔ E chi agisce non è mai un id
scritto a mano (`app.current_user_id = '1'`): lo sceglie o lo costruisce la riga
di contesto.

⚠️ **L'emittente di un documento è quello del suo conto**:
`anagrafiche.fn_get_emittente_fiscale_pk(<ba>)`. Ruolo e utility di testata di
ordine, bolla e reso sono quelli del billing account, quindi una fixture non
prende «il primo soggetto-ruolo» né un conto `NULL` per saltare un guard. Un
test sul guard di perimetro con un emittente altrui lavora su una bolla senza
conto: sull'ordine risponde prima il guard che lega emittente e conto.

### Il mondo si costruisce, non si cerca — e prima del contesto

Su un database ricostruito dai changelog (la CI, un'installazione nuova) il
**catalogo** c'è tutto e le **anagrafiche** sono a zero: nessun emittente,
nessun operatore, nessun cliente. Una fixture che li *cerca* (`SELECT … FROM
anagrafiche.emittenti_fiscali ORDER BY id LIMIT 1`, «un operatore con
whitelist», «un cliente libero») lì non trova niente e il file muore nel
fixture — copertura **zero**, non parziale. Il 2026-09-12 erano così **21 test
del perimetro** (`script/test-fn-scope-*`, `rls/*`): la proprietà fail-closed
delle funzioni di scope era collaudata solo sulla macchina di sviluppo.

Costruire i casi significa costruire anche **l'azienda e chi ci lavora**:

| Serve | Helper |
| --- | --- |
| **il mondo di un test di dominio**: azienda + operatore + contesto aperto + un cliente fatturabile legato a quell'azienda | `dbops.fn_pgtap_crea_mondo_cliente('<etichetta>')` |
| ⚠️ i builder che ricevono il **billing account di un'altra fixture** non costruiscono un cliente in più: prendono l'azienda di chi agisce (serve un contesto aperto) e verificano il conto | `dbops.fn_pgtap_cliente_del_builder` / `dbops.fn_pgtap_azienda_di_chi_agisce` (building block, non si chiamano dal test) |
| **una fattura** del mondo (registro coerente; nasce in bozza e arriva allo stato chiesto per la matrice, con indirizzi e intestazione scritti come fa la fatturazione) — col quarto e quinto parametro fuori bozza **senza indirizzi** e/o **senza intestazione** | `dbops.fn_pgtap_crea_fattura('<etichetta>'[, '<stato>'[, <ba_id>[, <senza_indirizzi>[, <senza_intestazione>[, <minimo>, <totale_a_pagare>, <termine_pagamento_id>[, <senza_utility>]]]]]])` |
| **un contratto** del mondo, nato dalla madre del dominio (`DRAFT`; `ATTIVO` con un listino del mondo; `ANNULLATO` dal verbo) — col terzo parametro sul cliente di un'altra fixture, per esempio quello di una commessa; col quarto il **figlio di un'offerta** accettata, nato dalla push; dal quinto all'ottavo **periodo, data e listino** del test | `dbops.fn_pgtap_crea_contratto('<etichetta>'[, '<stato>'[, <ba_id>[, <offerta_id>[, <valido_dal>, <valido_al>, <data>, <listino_id>]]]])` |
| **un ordine** di vendita del mondo (emittente del cliente, numero dal dominio; nasce in bozza e arriva allo stato chiesto per la matrice); col quarto parametro la **data dell'ordine**, scritta alla nascita | `dbops.fn_pgtap_crea_ordine('<etichetta>'[, '<stato>'[, <ba_id>[, <data>]]])` |
| **una bolla nata da un ordine** confermato, dalla madre del dominio (con causale e indirizzi che l'emissione pretende), nello stato chiesto — default **consegnata**; `DRAFT` per scriverle qualcosa in bozza e poi portarla avanti; due spedizioni dalla stessa riga con `p_qta_da_evadere` e poi `p_ordine_id`; da un ordine speciale costruito dal test con `p_ordine_id` | `dbops.fn_pgtap_crea_ddt_da_ordine('<etichetta>'[, '<stato>'[, <ba_id>]], p_quantita => …, p_prezzo => …, p_articolo_id => …, p_fatturazione_trigger => …, p_ordine_id => …, p_qta_da_evadere => …, p_righe => …, p_data => …, p_causale_codice => …, p_data_ordine => …, p_righe_ordine => …)` (per nome). ⚠️ La riga restituita è la **prima per numero**: con un onere nell'ordine (trasporto, spese), che passa intero nella bolla, può essere l'onere |
| **un reso** su una bolla (del test, di un reso in bozza a cui aggiungere una riga, o una bolla consegnata costruita), con la riga legata alla riga della bolla e alla riga d'ordine del legame, confermato dal verbo (l'azione `conferma_reso` la concede `dbops.fn_pgtap_porta_a_stato`, che il builder usa per lo stato); `DRAFT` per lasciarlo in bozza; l'annullo resta del test | `dbops.fn_pgtap_crea_reso('<etichetta>'[, <ddt_id>[, <qta>[, '<tipo>'[, '<stato>']]]], p_ddt_riga_id => …, p_ordine_riga_id => …, p_reso_id => …, p_data => …)` |
| **la bolla di ri-consegna** di un reso per ri-consegna confermato, dalla madre del dominio, completata di ciò che l'emissione pretende e portata allo stato chiesto (default consegnata); tutto il reso o una parte di una riga | `dbops.fn_pgtap_crea_ddt_riconsegna(<reso_id>[, '<stato>'], p_resi_riga_id => …, p_quantita => …, p_data => …)` |
| **un ordine con le sue righe**, nello stato chiesto (default confermato): una riga dai parametri o più righe (sconto, date di consegna); data alla nascita e momento di fatturazione in bozza; a richiesta righe e stato su una testata in bozza del test. Il builder dell'ordine resta senza righe | `dbops.fn_pgtap_crea_ordine_con_righe('<etichetta>'[, '<stato>'[, <ba_id>]], p_quantita => …, p_prezzo => …, p_articolo_id => …, p_fatturazione_trigger => …, p_data_ordine => …, p_righe => …, p_ordine_id => …)` |
| **una bolla senza ordine** con una riga prezzata, nello stato chiesto (default consegnata); causale, data e magazzino a scelta; la merce gestita si rifiuta (righe e prelievi di magazzino li scrive il test su `fn_pgtap_crea_ddt`, che ha la data alla nascita come sesto parametro) | `dbops.fn_pgtap_crea_ddt_senza_ordine('<etichetta>'[, '<stato>'[, <ba_id>]], p_quantita => …, p_prezzo => …, p_articolo_id => …, p_causale_codice => …, p_data => …, p_magazzino_id => …)` |
| **attività di commessa fatturate**: emesse dalla madre e agganciate a una fattura vera in bozza, una riga per attività (attività del test, stesso cliente); a richiesta dentro un lotto | `dbops.fn_pgtap_fattura_attivita('<etichetta>', ARRAY[<attivita_id>, …][, <lotto_id>])` |
| **un preventivo** del mondo (emittente del cliente, numero dal dominio, validità da oggi; nasce in bozza e arriva allo stato chiesto per la matrice). Senza righe: oltre la bozza si ferma sull'emissione, che chiede una riga | `dbops.fn_pgtap_crea_preventivo('<etichetta>'[, '<stato>'])` |
| **un preventivo con una riga** valida per l'emissione (merce, aliquota, prezzo 10), nello stato chiesto (default emesso), dal verbo; a richiesta la riga e lo stato su una testata in bozza del test | `dbops.fn_pgtap_crea_preventivo_con_righe('<etichetta>'[, '<stato>'], p_preventivo_id => …, p_prezzo => …, p_articolo_id => …)` |
| **una testata che cambia stato dopo aver preso le righe** (ogni testata di vendita con una matrice dei passaggi: nasce nello stato iniziale, il test scrive le righe, poi lo stato per le transizioni vere — fuori bozza le righe non si scrivono) | `dbops.fn_pgtap_porta_a_stato('vendite.<testata>', <id>, '<stato>')` (anche `vendite.fatturazione_lotti`, se vuoto). ⚠️ Su **tutte** le testate che conosce (preventivo, offerta, contratto, ordine, bolla, reso, commessa, fattura, lotto, versione di listino) lo stato si cambia solo dal verbo (la porta): la fixture fa ogni passo col verbo e **concede** all'operatore in sessione l'azione del passaggio (per esempio `emetti_ddt`, `conferma_reso`). Un `UPDATE` diretto della colonna di stato è rifiutato (`E_DOC_STATO_SOLO_DAL_VERBO`); una bolla `RESO` si costruisce confermando un reso totale |
| **una commessa** del mondo, aperta dalla madre del dominio (codice ed emittente dal dominio, competenza nel mese corrente) — nello stato chiesto, sul cliente di un'altra fixture; fuori bozza con l'attività approvata che l'uscita pretende; a richiesta con la **sorgente ROOT** | `dbops.fn_pgtap_crea_commessa('<etichetta>'[, '<stato>'[, <ba_id>[, <con_attivita>[, <con_sorgente_root>]]]])` |
| **un lotto di fatturazione** dell'azienda, nato dalla madre e portato allo stato chiesto (vuoto); a richiesta l'esito che trattiene un gruppo | `dbops.fn_pgtap_crea_lotto('<etichetta>'[, '<stato>'[, <ba_id>[, <tipo_doc_id>[, <mese>[, '<gruppo_key>'[, <del_cliente>]]]]]])` |
| **un'attività** approvata su una commessa costruita, scritta dalla madre (articolo costruito, pronta per l'emissione; articolo e listino del chiamante se li dà); con la **sorgente** l'attività che la push di una riga avrebbe scritto — la chiave la compone `script.fn_segment_key`, mai a mano — con quantità, stati e periodo dichiarati | `dbops.fn_pgtap_crea_commessa_attivita(<commessa_id>[, …], p_sorgente_codice => …, p_sorgente_chiave => …, p_sorgente_riga_id => …, p_stato_emissione => …)` (per nome) |
| una **filiale bancaria** su cui agganciare un conto | `dbops.fn_pgtap_crea_filiale_bancaria('<etichetta>')` |
| il **gestore** dell'installazione (lo prende se c'è, lo costruisce se non c'è) | `dbops.fn_pgtap_crea_gestore('<etichetta>')` |
| un'azienda con il suo operatore (e identità) | `dbops.fn_pgtap_crea_emittente_operatore()` |
| un **operatore umano** — persona fisica, risorsa umana, identità — **senza azienda**, volendo super admin | `dbops.fn_pgtap_crea_operatore_umano('<etichetta>'[, p_super_admin := true])` |
| un **punto di prelievo** nuovo, su un indirizzo suo | `dbops.fn_pgtap_crea_pdp(['<utility>'])` |
| un **listino** con una versione ATTIVA, dell'azienda di chi agisce (contesto aperto prima) | `dbops.fn_pgtap_crea_listino(<utility_id>[, '<etichetta>'[, valido_dal[, valido_al]]])` |
| l'utente tecnico di un processo, a roster | `dbops.fn_pgtap_crea_roster_processo('<processo>')` |
| un cliente fatturabile (soggetto → CL → istanza → BA) | `dbops.fn_pgtap_crea_cliente_ba('<etichetta>'[, utility, emittente_sr])` |
| un soggetto con un ruolo e basta (CL, FO, BANK_B…) | `dbops.fn_pgtap_crea_soggetto_pg(...)` + `fn_pgtap_crea_soggetto_ruolo(..., 'CL')` |
| un **super admin** (senza azienda, come in produzione) | `dbops.fn_pgtap_crea_operatore_umano('<etichetta>', p_super_admin := true)` — sotto, §«Un super admin non ha un'azienda» |
| **un articolo** del test, costruito intero con la struttura che il test sceglie: non gestito a magazzino se il test non misura il magazzino; kit, solo componente, lotto e seriale a richiesta | `dbops.fn_pgtap_crea_articolo('<codice>'[, <gestito>[, …]])` |
| cambiare la **struttura di un articolo già usato**, dalla porta vera e come super admin costruito | `dbops.fn_pgtap_articolo_correggi_struttura(<articolo_id>, <campi>)` |
| **articoli dentro una versione di listino**: una riga attiva per articolo, con prezzo e periodicità (va chiamato prima di usare l'articolo: ne allinea la tipologia) | `dbops.fn_pgtap_listino_aggiungi_articoli(<versione_id>, ARRAY[<articolo_id>, …][, <prezzo>[, '<periodicita>']])` |
| un **cliente completo**: il cliente fatturabile più la riga di `anagrafiche.clienti`, nello stato chiesto e con le date che lo stato pretende (contesto aperto prima) | `dbops.fn_pgtap_crea_cliente('<etichetta>'[, utility, emittente_sr[, '<stato>']])` |
| un'**azienda senza operatore** (emittente con la valuta): da sola non la vede nessun test | `dbops.fn_pgtap_crea_emittente()` |
| un **magazzino** dell'azienda di chi agisce (contesto aperto prima) | `dbops.fn_pgtap_crea_magazzino('<codice>', <usa_ubicazioni>)` |
| un **indirizzo** fabbricato: gli indirizzi sono dati di macchina, le vie sono seed | `dbops.fn_pgtap_crea_indirizzo_dettaglio('<etichetta>')` |
| **una bolla in bozza senza righe**, sul cliente del test: righe e prelievi li scrive il test | `dbops.fn_pgtap_crea_ddt(<ba_id>, <destinatario_sr_id>, '<causale>'[, <magazzino_id>[, <magazzino_arrivo_id>[, <data>]]])` |
| **un consumo**, il documento d'origine più leggero per una riga di commessa; quello di una commessa è lo stesso a ogni chiamata | `dbops.fn_pgtap_crea_consumo(<ba_id>[, <mese>[, <meta>]])` / `dbops.fn_pgtap_consumo_della_commessa(<commessa_id>)` |
| la **provenienza** che una chiave del push nomina, per scrivere una riga di commessa con la madre | `dbops.fn_pgtap_provenienza_da_chiave('<segment_key>')` |
| una **sorgente di prova**: un tipo di documento che il catalogo non ha (una famiglia di numerazione o un ambito di prova) | `dbops.fn_pgtap_crea_sorgente('<codice>'[, '<tabella>'::regclass])` |
| **un'azione di processo concessa** a un utente, e fatta valere anche sull'area — sotto, §«I permessi dell'operatore del test» | `dbops.fn_pgtap_concedi_azione(<auth_user_id>, '<azione>')` |
| lo **scope di un lavoro in coda** accodato da chi è in sessione | `dbops.fn_pgtap_scope_operatore([<emittente_id>])` |
| ⚠️ valuta, forma dell'indirizzo e verifica del conto li risolvono i builder | `dbops.fn_pgtap_valuta` / `dbops.fn_pgtap_indirizzo_libero_forma` / `dbops.fn_pgtap_cliente_ba_del_mondo` (building block, non si chiamano dal test) |

⭐ **Un builder che esiste si estende; uno nuovo nasce solo per una trappola
d'ordine o per una regola di dominio che altrimenti si ricopierebbe nei test**,
non perché «serve spesso». E un builder composto (l'ordine con le righe) chiama
il builder base, non lo ricopia: due strade per costruire lo stesso documento
fanno divergere le fixture.

⛔ **Ordine obbligato: prima il mondo, poi `fn_pgtap_set_contesto_operatore(<auth_user_id>)`.**
Con un operatore già in sessione il legame BA → emittente lo scrive già il
trigger del billing account, verso l'azienda di chi agisce: chiedere col terzo
parametro la stessa azienda non cambia niente, chiederne un'altra è rifiutato
dal building block. Da owner si costruisce tutto prima e si lega il BA
con il terzo parametro; come `zeroerp_app` si apre il contesto e si chiama
`fn_pgtap_crea_cliente_ba` **senza** terzo parametro (dalla rev `20260912-38` il
legame lo lascia al trigger, verso l'emittente di chi agisce).

⭐ **La riga di contesto del template lo fa da sola, se serve.** Da
`20260920-01`, `script.fn_pgtap_set_contesto_operatore()` senza argomento —
quando non trova nessun operatore, cioè su un database vuoto — costruisce
azienda + operatore e apre il contesto su quello. Un file che vuole solo «un
operatore su un emittente» non ha altro da fare. Il builder si chiama a mano
quando servono gli **id** del mondo (l'emittente per un registro, il soggetto
ruolo, **due** aziende) o quando il soggetto del test è l'operatore umano.

⭐ **E la composizione ha un helper suo** (rev `20260922-17`): quando a un file
servono *insieme* l'azienda, il contesto e un cliente fatturabile — il caso di
gran lunga più frequente — `dbops.fn_pgtap_crea_mondo_cliente('<etichetta>')` li
costruisce nell'ordine giusto e ne torna tutte le chiavi in una riga. Senza
contesto costruisce e lo apre; **con un contesto già aperto riusa l'azienda di
chi agisce**, e non è un risparmio: un'azienda nuova lascerebbe il cliente legato
a quella vecchia, invisibile sotto RLS. ⛔ Non comprende registro, articolo né i
cataloghi di `80_data`: entra ciò che ha una **trappola d'ordine**, non ciò che
serve spesso.

⭐ **Una FATTURA e' una catena, non un INSERT**: il cliente va legato
all'azienda di chi agisce, il registro dipende da quell'azienda e la valuta si
risolve lungo la catena «cliente → azienda → gestore».
`dbops.fn_pgtap_crea_fattura()` mette tutti e tre gli anelli. La coppia
(emittente, utility) **non** la scrive: senza la sua riga valgono i parametri di
sistema dell'utility, e scriverla nasconderebbe ai test il caso dell'emittente
nuovo. La fattura **nasce nello stato iniziale** e la fixture la porta allo stato
chiesto per la matrice dei passaggi; il **terzo parametro** e' il billing account
di una fattura gia' costruita, per la seconda dello stesso cliente. ⛔ Righe, scadenze, contabili e
movimenti restano al test: sono il suo caso.

⚠️ **Un super admin non ha un'azienda.** È multi-emittente per modello, e non è
un dettaglio: un billing account senza legame ricade sull'emittente di **chi
agisce** prima che sul gestore globale, quindi un super admin costruito come
utente tecnico (che un'azienda ce l'ha sempre) sposta il ripiego. E toglierla
dopo non si può. Si costruisce con `fn_pgtap_crea_operatore_umano(…,
p_super_admin := true)`, che passa dalla madre di produzione e nasce senza.
Un super admin **lavora** su un'azienda solo se la **sceglie**, come in alto:
`app.current_emittente_id`. Con l'azienda scelta, il mondo e i builder che lo
compongono (fattura, ordine, contratto…) costruiscono su quella, come il trigger
che lega il cliente; senza, il mondo lo rifiuta. È il modo in cui lavorano gli
smoke Python con l'utente `dev.smoke`.

⛔ **Ciò che un builder scrive si legge in un'istruzione SEPARATA.** Un `JOIN`
sulla tabella che il builder ha appena scritto, o una funzione `STABLE`, nella
**stessa istruzione** della chiamata vede la snapshot di prima: la temp table
nasce vuota, o il super admin risulta non esserlo.

⚠️ E `anagrafiche.bank_branches` e' **dato di macchina**, non seed: da zero e'
vuota, e un conto bancario ci sbatte sul NOT NULL. La filiale si costruisce con
`dbops.fn_pgtap_crea_filiale_bancaria()`.

⚠️ Gli helper escono con i vincoli **IMMEDIATE**: un file che li vuole
differiti fino a un punto suo (`pgtap-differiti`, «fattura + atto») li riapre
con `SET CONSTRAINTS ALL DEFERRED` subito dopo.

⛔ **E la riga di contesto, quando costruisce, è un helper.** Senza argomento su
un database vuoto chiama il builder, e ne eredita il contratto: esce IMMEDIATE.
Con argomento, o dove un operatore esiste (dbdev), **non tocca i vincoli** — e
non può fare altrimenti: il modo di una transazione non si legge né si
ripristina, e un setter di contesto che chiudesse i vincoli pendenti li
chiuderebbe *nei panni del nuovo attore* (la trappola RLS di
`rls/test-rls-listini-ef-whitelist-write`). Quindi il contratto è asimmetrico
per costruzione, e la regola per i file è una sola: **dopo la riga di contesto
non si conta sulla finestra differita di default** — se la si vuole, si
dichiara con `SET CONSTRAINTS ALL DEFERRED`. È ciò che il primo file della suite
(`anagrafiche/create-cliente`) non faceva: verde su dev, rosso in CI il
2026-09-21, e da solo mai — il secondo file committa un operatore in autocommit
e da lì in poi nessuno percorre più il ramo che costruisce.

⚠️ E i **rami `skip` spariscono**: con il mondo costruito la precondizione c'è
sempre, e un `CASE WHEN EXISTS(...) THEN ok(...) ELSE skip(...)` diventa un
`ok(...)`. Un test che *può* saltare, su un database vuoto salta.

⛔ **Nessuna pesca residua, e una pesca non si ripara con un filtro.** In una
fixture passata ai builder non resta «il primo super admin» né un id fisso: su
un database vuoto la pesca non fallisce, dà `NULL`, e il builder costruisce un
mondo suo; dove i dati ci sono trova una riga vera e prende un'altra strada. Un
verde sul database vuoto prova solo la strada del database vuoto. E un filtro
(«il primo cliente la cui utility ammette la tipologia») rende la pesca
coerente, non presente: il cliente scelto porta la sua storia. Valgono gli
stessi motivi per ciò che non è anagrafica:

* **anche l'articolo si costruisce** (`dbops.fn_pgtap_crea_articolo`): da zero
  il catalogo ha solo gli oneri, e altrove «l'ultimo articolo» può essere un kit
  o un articolo gestito a magazzino, che alla bolla muove merce e cambia il
  verbo che lo stato pretende;
* **sotto un vincolo di unicità o di non sovrapposizione la chiave è del
  test**: dove il contesto riusa un'azienda esistente, una riga di fixture può
  collidere con una riga vera (per `categorie_clienti_listini` una categoria
  cliente creata dal test e messa sul conto, non la prima del seed; un cliente
  per contratto, perché i contratti dello stesso cliente non si sovrappongono).
  Modello: `db/pgtap/vendite/test-fn-resolve-prezzo-listino-v2-bundle-prioritario-v1.sql`.

⚠️ **La seconda azienda.** L'azienda in più si costruisce prima del contesto, ma
il suo cliente nasce aprendo il contesto sull'operatore di **quella** azienda e
chiamando il builder senza terzo parametro; poi il contesto torna su chi agisce.
Senza contesto la policy rifiuta la riga. Vale anche per il cliente che serve a
un super admin: lo crea un operatore con un contesto aperto.

⚠️ **Dopo `fn_pgtap_crea_mondo_cliente` la riga di contesto resta**:
`PERFORM script.fn_pgtap_set_contesto_operatore(<auth_user_id del mondo>)`. Il
cancello del preambolo riconosce il contesto da quella chiamata, e una riga
dichiarata dice a chi legge su quale operatore gira il file.

⚠️ **L'operatore di `fn_pgtap_crea_emittente_operatore` ha la credenziale di un
processo.** Una veste di persona (cliente del portale, cliente dello shop) su
quella credenziale è rifiutata dal guard sulla natura: un'identità di persona
nasce su un utente suo.

⭐ **La riga di lavoro si verifica appena costruita, nominando ciò che manca**:
un `LATERAL (VALUES ('campo', t.campo IS NULL), …)` con `string_agg` dei soli
mancanti, confrontato con la stringa vuota. Un `AND` unico dice che manca
qualcosa, non cosa; e un `SELECT … INTO` su zero righe fa fallire il test molto
più avanti, su una colonna estranea.

### Solo stati che il modello produce

Una fixture scritta a mano può confermare un ramo che nessun percorso raggiunge.
I dati si costruiscono **come li scrive chi li produce** — la madre, la push, il
loader — non come il ramo sotto esame li vorrebbe: se per far scattare un ramo
serve inventare un valore, la domanda è chi lo scrive davvero.

* **Uno stato che la madre non produce non si fabbrica.** Per «una fattura
  ferma nel lotto» la fattura resta indietro rispetto al lotto; il caso opposto
  è una difesa, e il test lo dichiara con uno `skip` motivato. «Avanti» e
  «indietro» si leggono dal vocabolario degli stati (`congela_fiscale`), non
  dalla colonna `ordine`.
* **Una riga incompleta si corregge passando dal builder, non aggiungendo il
  pezzo che manca**: una veste `OPERATORE` scritta a mano senza risorsa umana è
  uno stato che la madre non produce.
* **Un ramo che un guard a monte rende irraggiungibile non si raggiunge
  spegnendo il trigger.** Il caso si omette, e l'intestazione del file dice
  quale ramo non è coperto e quale guard lo chiude.
* **Un helper che imita un flusso del backend ripete ogni chiamata al database
  che il servizio fa**, non solo la madre: un passo saltato non fallisce, manca,
  e la regola che ci vive non la attraversa nessun test. Se la regola sta in un
  passo che il backend fa a parte, la cura è portare il passo dentro la madre.
* **La forma che il percorso garantisce ha un'asserzione sua** («ciò che nasce
  dalla push ha sorgente `COMMESSA`»): è ciò che tiene vera la fixture nel
  tempo.

### I permessi dell'operatore del test

L'operatore che i builder costruiscono non porta con sé i permessi dei verbi:
il test se li concede, come farebbe un amministratore, e non li dà per scontati.

* **Il livello d'area** che `script.fn_guard_livello` pretende si scrive con una
  riga in `config.user_override_aree` per il proprio operatore; senza, il verbo
  risponde `E_PERMESSO_NEGATO`, perché il guard nega quando non trova niente.
  Modello: `db/pgtap/config/test-fn-pannello-scrivi-v1.sql`.
* **L'azione di processo** che `script.fn_guard_azione` pretende la concede
  `dbops.fn_pgtap_concedi_azione`. Si concede nel setup, **prima** della prima
  lettura di capability: una capability letta prima della concessione nasconde
  l'azione, e il test fallisce lontano dalla causa.
* ⛔ **Nessun helper `SECURITY DEFINER` per saltare la porta**: sarebbe una
  scorciatoia che anche l'applicazione può eseguire.
* **Una `TEMP TABLE` è di chi la crea**, cioè del ruolo del runner, e una
  funzione `SECURITY DEFINER` la legge coi privilegi del **suo** proprietario:
  risponde `permesso negato` e la transazione è persa per tutte le asserzioni a
  valle. La fixture concede `SELECT` sulla temp table al proprietario della
  funzione letto dal catalogo (`pg_get_userbyid(proowner)`), mai a un ruolo
  scritto per nome: il proprietario dipende da chi ha migrato.

### Un test in un solo contesto prova solo quel contesto

Un invariante non dipende da chi preme il pulsante, e una regola che guarda chi
agisce ha più di una faccia. Il test le costruisce tutte.

* **Un guard che legge un risolutore di sessione** si asserisce sia da operatore
  con la sua azienda sia da super admin senza azienda: è proprio il secondo a
  mascherare il difetto.
* **Una regola «l'emittente di chi agisce, altrimenti il predefinito»** si prova
  in due facce — in sessione e senza (`set_config('app.current_user_id', '',
  true)`) — e con **due aziende**. Su un database da zero la prima azienda che
  la fixture crea diventa la predefinita dell'installazione
  (`trgfn_emittenti_fiscali_default_bootstrap`): con una sola, le due risposte
  coincidono e il test è verde senza provare niente. Le due aziende nascono in
  due istruzioni, il contesto si apre sulla seconda, e una prima asserzione
  verifica che quella **non** è la predefinita. Modello:
  `db/pgtap/rls/test-rls-billing-account-returning-secondo-emittente.sql`.
* **Un caso che attraversa due perimetri** si prova nei panni di chi li vede
  entrambi, cioè un super admin: è anche l'unico che nel mondo reale può
  costruirlo. Se la fixture sposta una riga fuori dal perimetro di chi esegue,
  ogni `UPDATE` o `DELETE` successivo tocca zero righe in silenzio, e il guard
  che la rilegge risponde «assente» prima della regola che si voleva provare.

### Kit e listini: l'ordine conta

* **Un kit con la distinta**: l'articolo nasce composito
  (`p_is_composito => true`) prima di scrivere `catalogo.articoli_componenti`;
  lo stato di approvazione della riga si scrive **dopo** il componente, perché
  il componente ricalcola il prezzo del padre; un componente che il test vuole
  togliere nasce `obbligatorio = false`. Modello:
  `db/pgtap/script/test-fn-check-prezzi-autorizzati-v1.sql`.
* **Un listino che contiene un kit**: la versione si costruisce in `BOZZA`, si
  scrivono righe e componenti e solo dopo si porta ad `ATTIVA`, perché fuori
  dalla bozza i componenti non si scrivono.
* ⚠️ **Il listino del builder nasce sulla prima tipologia ammessa dalla
  utility**, che può ammettere solo il consumo, mentre un kit ha solo erogazioni
  a quantità fissa: il test che mette un kit in quel listino sceglie subito dopo
  una tipologia che ammette la quota fissa, altrimenti il primo motivo di
  rifiuto è «senza erogazione».

### Una regola nuova si censisce sulle fixture

Chi aggiunge un vincolo o un guard cerca in `db/pgtap/` le fixture che lo
attraversano, non solo i test che lo nominano.

* **Un vincolo che restringe una colonna** rompe tre forme di fixture: chi
  omette la colonna, chi scrive `NULL` nella sua posizione, chi passa
  `=> NULL` alla madre. Prima di dare un valore al `NULL` si leggono le
  asserzioni: se il `NULL` è ciò che il test misura, la fixture si sposta sul
  caso che il modello ammette, non si riempie.
* **Una regola di veste o sulla natura di una credenziale** si censisce dagli
  `INSERT INTO anagrafiche.identita_digitali` delle fixture e da chi riusa la
  credenziale di un helper: le funzioni di scope le chiamano le policy, e una
  ricerca dei chiamanti non trova nessun file.
* **Una regola su una riga di catalogo** tocca anche i test che quella riga la
  **pescano** senza nominarla (sotto, §«`LIMIT 1` senza `ORDER BY`»).
* **Un valore nuovo in un vocabolario chiuso** fa diventare rosso, apposta, il
  test che lo enumera: si allarga l'elenco **e** si aggiunge l'asserzione su
  che cosa significa il valore.

### ⚠️ «Libera» vuol dire «libera ADESSO»

`dbops.fn_pgtap_piva_libera()` e `dbops.fn_pgtap_cf_libero()` rispondono **la prima
non ancora usata in questo istante**. Non sono generatori: finché nessuno scrive
quel soggetto, la chiamata successiva risponde **lo stesso numero** — anche in
un'altra istruzione (misurato il 2026-09-23).

⇒ Due conseguenze, e sono state due rossi veri:

1. chiederne **due in una volta** per due soggetti diversi dà due volte lo stesso
   valore, e il secondo INSERT muore su `uq_soggetto_idstato_id_fiscale_univoco`;
2. precalcolarla **prima** di costruire il mondo è peggio: la riga di contesto,
   quando costruisce azienda e operatore, prende proprio quella — e il soggetto del
   test collide con il soggetto dell'azienda.

⭐ La regola è una: **la si chiede quando serve, dopo che il mondo esiste**, e una
per volta. In un file a più casi, ogni caso chiede la sua.

### `LIMIT 1` senza `ORDER BY` non verifica, scommette

Quale riga esca dipende dal piano del planner, che cambia coi dati: il test
passa a giorni alterni e nessuno capisce perché.

1. **`ORDER BY` su una chiave stabile** — rende la scelta ripetibile;
2. **la condizione che rende il caso significativo** — spesso una guardia a
   monte (idempotenza, stato) rende irraggiungibile proprio il ramo da provare;
3. **scegli una volta sola.** Se ti servono due valori della stessa riga (id e
   aliquota, id e codice), una CTE o una temp table — due sotto-select
   indipendenti possono pescare righe diverse. È successo: `iva_id` e
   `iva_aliquota` uscivano da due estrazioni su **sette** candidati, e il test
   avrebbe calcolato i totali con l'aliquota sbagliata;
4. **se dipende da chi agisce, derivalo dal contesto** invece di pescarlo;
5. **se la porta solleva il primo di più motivi ordinati, il soggetto si sceglie
   sul motivo che scatterà davvero**, chiedendolo alla `fn_check_*`
   (`… -> 0 ->> 'reason' = '<MOTIVO>'`) e non ricopiandone le condizioni: una
   ricerca a mano del motivo N pesca un soggetto su cui ne scatta uno
   precedente, e il rosso accusa il codice invece della selezione;
6. **una riga di vocabolario si nomina per codice.** «La prima tipologia della
   utility con queste erogazioni» cambia esito quando il vocabolario cresce, e
   la fixture eredita le regole della riga che le capita.

Lente per censire: `python3 scripts/censimento_limit1.py`. ⚠️ È una lente e non
un cancello: metà delle occorrenze sono su temp table del test stesso, dove il
`LIMIT` non sceglie niente. Un cancello con quel tasso di falsi positivi si
impara a disattivare.

### «Oggi» è il giorno dell'azienda, non quello della sessione

Il codice legge il giorno dal fuso dell'azienda (`script.fn_data_operativa()`), e
il test deve costruire lo **stesso** giorno:

| serve | si scrive |
| --- | --- |
| oggi | `script.fn_data_operativa()` |
| il giorno di un istante (`data_mov`, `data_insert`, …) | `script.fn_giorno_operativo(<istante>)` |
| l'istante in cui comincia un giorno | `script.fn_inizio_giorno_operativo(<data>)` |

⛔ `CURRENT_DATE`, `LOCALTIMESTAMP`, `now()::date` e un `::date` su un istante
danno il giorno della **sessione**, e la sessione dei test gira apposta in un
fuso il cui giorno è **diverso** da quello dell'azienda: `scripts/testpgtap.sh`
sceglie, file per file, fra +14 e −11 quello che adesso cade in un altro giorno.
Così un test che confonde i due giorni è rosso a ogni ora, non solo di notte.
La prima metà della regola la presidia `scripts/guardrail_pgtap_preambolo.py`;
un'eccezione si dichiara con `-- pgtap-oggi: escluso — <perché>`.

⚠️ **Una data di fixture si scrive rispetto a oggi, non come letterale**:
`script.fn_data_operativa() + N` o `- N`. Una data fissa era futura quando è
stata scritta e smette di esserlo: la prima regola che la confronta con oggi
ferma la fixture prima delle asserzioni.

⚠️ **`now()` è fermo all'apertura della transazione**, e un test è una
transazione sola: apertura e chiusura di un intervallo scritte con `now()`
coincidono, e un `CHECK` stretto le respinge. Un test che misura tempi usa
`clock_timestamp()` per ogni istante successivo — e guarda se un trigger
attraversato fa lo stesso errore.

⭐ Un rosso da riprodurre nel fuso dell'azienda: `PGTZ=Europe/Rome
scripts/testpgtap.sh …` (il runner rispetta un `PGTZ` già impostato).

### Le chiavi generate devono essere larghe

Un suffisso di **due caratteri esadecimali** sono 256 valori. Con 64 righe
residue in tabella la collisione arriva al **25% delle corse** — ed è così che
un test è oscillato «fra 6 e 0 asserzioni» per mesi senza che nessuno capisse.
Usa il suffisso intero: la colonna quasi sempre lo regge.

⚠️ **Un `codice` generato nasce già maiuscolo** (`upper()` sul generatore del
suffisso, non sulle ricerche): l'automazione lo salva normalizzato, e un
suffisso esadecimale minuscolo non si ritrova più per valore.

### Padre e figlio in due istruzioni, non in una CTE

Le CTE che scrivono condividono **la stessa snapshot**. Una policy che risolve
il perimetro dal padre (`fn_scope_*_via_fattura`) non lo trova e nega
fail-closed. In `LANGUAGE sql` non si può separare: serve `plpgsql`, due
`INSERT` e una variabile in mezzo.

⚠️ L'errore che ottieni parla di RLS sulla tabella **figlia**, e sembra un
problema di permessi. Non lo è.

## Le asserzioni

### Un errore si asserisce, non si spera

`throws_ok(sql, NULL, NULL, 'desc')` verifica **che** sollevi, non **cosa**:
accetta anche il crash del guard che volevi verificare, o un `permesso negato`
che non c'entra niente.

```sql
throws_ok  (sql, 'P0001', NULL, 'desc')   -- errore di dominio (fn_log_and_raise_error)
throws_ok  (sql, '23514', NULL, 'desc')   -- CHECK   ·  '23505' unique  ·  '23503' FK
throws_like(sql, '%frase stabile%', 'desc')
```

⚠️ **`P0001` dice «è un errore di dominio», non QUALE**: tutti i codici passano
da `fn_log_and_raise_error`, che usa quello SQLSTATE per tutti. Per distinguere
fra due codici si asserisce il **codice** (qui sotto).

⚠️ **E il pattern non deve attraversare un segnaposto.** Il messaggio
`Riga DDT %s non trovata` si matcha con `'%Riga DDT %non trovata%'`, mai con la
frase intera: l'id interpolato la spezza in mezzo.

⭐ **Il discriminante più stabile fra due errori di dominio è il codice**, che
`fn_log_and_raise_error` espone nel campo `CONSTRAINT` dell'eccezione
(`GET STACKED DIAGNOSTICS … = CONSTRAINT_NAME`): non cambia quando la frase per
l'operatore viene riscritta. `throws_like` sulla frase resta per i casi in cui
la frase è la posta in gioco.

Il codice si legge con il building block `dbops.fn_pgtap_codice_errore`, che
esegue l'istruzione e restituisce che cosa l'ha rifiutata:

```sql
SELECT is(dbops.fn_pgtap_codice_errore($$SELECT schema.fn_verbo(…)$$),
          'E_CODICE_ATTESO', 'il verbo rifiuta: E_CODICE_ATTESO');
SELECT is(dbops.fn_pgtap_codice_errore($$…$$), NULL, 'il verbo accetta');
```

La risposta è, in quest'ordine: `NULL` se l'istruzione passa, il **codice di
dominio**, il **nome del vincolo** per un CHECK, UNIQUE o FK violato, altrimenti
lo **SQLSTATE**. Un errore inatteso non interrompe il file: torna come valore, e
l'`is()` mostra che cosa è successo. ⛔ Non si riscrive una `pg_temp` che fa la
stessa lettura: una copia locale prima o poi risponde in un altro modo allo
stesso rifiuto.

Lo stesso SQLSTATE può arrivare da due fonti, e il test resta verde per quella
sbagliata:

* **due vincoli con lo stesso SQLSTATE**: si asserisce il **nome** del vincolo
  nel messaggio (`throws_like`). Un vincolo nuovo può tenere verde per
  coincidenza un `throws_ok` scritto per un altro;
* **una tabella seminata con id fissi**: un `INSERT` senza id prende dalla
  sequenza un numero che il seed ha già usato, e il `23505` arriva dalla chiave
  primaria. Il test negativo passa un id libero;
* **una figlia con un trigger `AFTER` che riscrive il padre**: il rifiuto può
  arrivare dal guard del padre con lo stesso codice. Si legge la pila
  (`GET STACKED DIAGNOSTICS … PG_EXCEPTION_CONTEXT`) e si pretende che il
  rifiuto **non** passi dalla funzione di ricalcolo. Modello: `pg_temp.chi_rifiuta`
  in `db/pgtap/vendite/test-righe-e-componenti-le-altre-famiglie-v1.sql`;
* **il caso «riga inesistente»** si prova con un id positivo fuori scala
  (`2147483647`): un id negativo lo ferma prima il guard sul parametro, e il
  test collauda un altro errore.

⚠️ **Un `throws_ok(…, '42501')` su un privilegio usa un'istruzione che non tocca
righe**: `INSERT … SELECT … WHERE false` o `UPDATE … SET id = id WHERE false`. Il
permesso si controlla prima delle righe; eseguito da proprietario, un
`INSERT … VALUES` non solleva e scrive davvero la riga, che sporca le asserzioni
successive.

> **Quanto costa non farlo, misurato.** Su 137 `throws_ok` senza discriminante,
> una sonda ha eseguito lo statement e letto lo SQLSTATE vero: **tre test
> VERDI** collaudavano una cosa diversa da quella dichiarata — un guard che
> **esplodeva** in `format()` invece di parlare (`22023`), un «errore su colonna
> generata» spacciato per guard (`428C9`), una violazione di FK spacciata per
> guard (`23503`).

### I trigger `BEFORE ROW` girano prima dei `CHECK`

Un'asserzione che crede di collaudare un `CHECK` viene spesso intercettata dal
guard e non lo raggiunge mai. Per arrivare davvero al `CHECK` serve un caso che
il guard **lascia passare**.

⚠️ **Anche la policy parla prima dei vincoli.** In un `INSERT` il `WITH CHECK`
della RLS si valuta prima di `NOT NULL` e `CHECK`: con a `NULL` la colonna su
cui la policy si ancora, la riga esce con `42501` e il vincolo non viene
raggiunto (da proprietario lo stesso `INSERT` dà `23502`). Un `NOT NULL` su
quella colonna si asserisce con `col_not_null(...)`; il `42501` non si fissa in
un test, sarebbe il sintomo.

⚠️ **E un trigger `BEFORE` può riscrivere la colonna che asserisci.** Prima di
asserire su una colonna si cercano i trigger che scrivono `NEW.<colonna>`: su
una colonna derivata il valore scritto dal test non esiste mai, e l'asserzione
misura il trigger. Che una propagazione **non** sia scattata si asserisce sul
`ctid` della riga figlia, che cambia a ogni `UPDATE`, con un caso di controllo
in cui lo si vede cambiare.

### Quando togli un `LIMIT 1`, chiediti cosa vorrebbe dire l'asserzione

Spesso la forma giusta è **più severa**, non solo più stabile:

* `SELECT DISTINCT` su un valore di testata **esplode** se le righe dello stesso
  documento ne portano di diversi — asserisce anche l'invarianza;
* `bool_and(...)` su tutte le righe dice «**nessuno** è incoerente», invece di
  «uno a caso va bene».

## Il disegno delle asserzioni

Un test verde dice una cosa sola: che le sue asserzioni non sono state violate.
Se misurino la regola è un'altra domanda, e si risponde prima di dichiararlo
finito.

### La prova di mutazione: un test si vede rosso prima di crederlo

Un test nuovo si prova **al contrario**: dentro la transazione si rompe la
regola in due o tre modi diversi, dopo aver scritto quali asserzioni devono
diventare rosse. Un'asserzione che resta verde dove ci si aspettava rosso, o
che passa a `skip`, non sta misurando la regola. Le varianti:

* **tolta la regola, il test deve diventare rosso** — è la sola prova che il
  rifiuto arriva dalla regola dichiarata e non da un'altra fonte con lo stesso
  codice;
* **un presidio «zero righe» si popola una volta**, in una transazione
  annullata, e si controlla che il rosso dica **quale** riga;
* **un blocco `EXCEPTION WHEN OTHERS` che finisce in `skip()` si fa fallire
  almeno una volta**: un errore di scrittura del test ci finirebbe dentro per
  sempre;
* **si guarda se salgono i rossi o gli skip**: un test che alla rottura salta ha
  scelto il soggetto col verdetto dell'oggetto sotto esame (qui sotto).

### Da dove arriva il dato che soddisfa l'asserzione

Per ogni asserzione ci si chiede da dove arriva il dato che la rende vera. Se
passa dal meccanismo sotto esame — la policy, il registro, la vista —
l'asserzione parla di sé stessa, e resta verde proprio quando il meccanismo si
rompe.

* **Il soggetto si sceglie sulle precondizioni strutturali del ramo** (catalogo,
  righe costruite), mai sul verdetto che l'oggetto dà oggi (`WHERE stato = 'OK'`
  letto dalla vista che si collauda): se l'oggetto si rompe la `SELECT` non
  trova nessuno, e il test salta invece di diventare rosso.
* **Il denominatore di un invariante si prende fuori dal filtro**: le righe che
  la fixture ha costruito, il catalogo di PostgreSQL, un `CHECK`. Se il
  denominatore è ristretto, il file lo dichiara.
* **Un'asserzione di copertura non contiene un numero scritto a mano** («copre
  tutti e tre i canali»): l'elenco si legge dalla fonte che lo dichiara — il
  `CHECK` (`pg_get_constraintdef`), il catalogo — e l'asserzione diventa la
  regola: ogni valore dichiarato è usato da almeno una riga.
* **Il criterio di una vista non si riscrive nel test**: ne nascerebbe una
  seconda copia, cioè il difetto che un presidio esiste per trovare.
* **L'assenza di un termine si asserisce su un campo che la fixture non
  compone**: la ragione sociale del cliente costruito contiene l'etichetta e il
  codice del billing account.

### Un'asserzione che passa a vuoto

Davanti a ogni asserzione ci si chiede: **che cosa succede se ciò che nomino non
c'è?** Le forme che restano verdi su una configurazione monca:

* **un ordine relativo scritto sugli indici** (`MIN(ord) FILTER (…) <
  MIN(ord) FILTER (…)`): se uno dei due sparisce il confronto dà `NULL`. Si
  scrive in forma di **copertura**: quanti casi rispettano l'ordine, contro
  quanti casi esistono;
* **il conteggio dei cattivi a partire da un `JOIN`**: il dato rotto al punto di
  non agganciarsi esce dal join e smette di essere contato. Accanto a «è la riga
  giusta» va il gemello «la riga esiste», scritto al rovescio: si parte da chi
  dichiara il legame e si pretende l'altro capo con `NOT EXISTS`;
* **un'esclusione** (il pregresso, un `IS NOT NULL`): tollera anche il difetto
  nuovo che ha la stessa forma. L'esclusione è una decisione e resta; accanto va
  il gemello positivo, che crea una riga dal percorso reale e asserisce che è
  giusta;
* **`count(*)` da solo quando la posta è una colonna**: va in coppia con
  `count(<colonna>)`. Una colonna consegnata su tutte le righe e valorizzata su
  nessuna ha struttura giusta e presidi verdi;
* **`count(*) = 0` su una tabella sotto policy**, eseguito come applicazione: è
  verde anche a tabella piena (sotto, §«Quando il test non può girare come
  l'applicazione»);
* **`has_check(schema, tabella, descrizione)`**: il terzo argomento è la
  descrizione, non il nome, e l'asserzione è verde con **qualunque** `CHECK`. Un
  vincolo si asserisce per nome e definizione insieme (`pg_get_constraintdef`
  del vincolo con quel `conname`, confrontato col testo atteso);
* **`has_column`**: verifica il nome, non da dove arriva il valore. Su una
  famiglia di viste quasi identiche l'errore plausibile è la riga copiata dalla
  sorella; accanto va un'invariante sul **contenuto**, vera anche a database
  vuoto. E le viste della famiglia si elencano per nome: un giro su
  `LIKE 'vw_%_lista'` conta solo quelle che ci sono;
* **`columns_are`**: confronta **insiemi**. «Le colonne nuove in coda» si legge
  da `pg_attribute.attnum`; e se una vista è fissata da `columns_are` in due
  file, uno resta la sede dell'insieme e l'altro asserisce solo ciò che è nato
  con la modifica;
* **`information_schema.triggers`**: porta una riga per evento, non per trigger.
  Un conteggio si scrive `COUNT(DISTINCT trigger_name)`, o si legge `pg_trigger`;
* **un override lasciato aperto**: una fixture che apre
  `zeroerp.allow_lock_columns_override` la richiude nella riga dopo, o le
  asserzioni successive sono verdi per sottrazione.

### Che cosa asserire

* **Il test di un difetto non asserisce il sintomo** («il codice X affiora fra i
  candidati»): il giorno della riparazione sarebbe rosso, e un rosso su una
  riparazione spinge a rimettere il difetto. Si scrivono due asserzioni: la
  **capacità** del meccanismo e l'**invariante** della riparazione. La seconda è
  negativa e passa a vuoto se il meccanismo si spegne: la tiene onesta la prima,
  e il commento lo dice.
* **Un test sulla forma copre ogni ramo del modello con un rappresentante** (per
  una capability: un documento per dominio e stato). Iterare su tutti i
  documenti presenti non aggiunge un ramo: ripete lo stesso, paga la funzione N
  volte e lega la copertura ai dati della macchina.
* **Due funzioni che si parlano si provano dal produttore al consumatore.** Un
  test per lato le lascia verdi entrambe anche quando la madre rifiuta ciò che
  il lister produce: la riga del lister, `to_jsonb`, si passa alla madre.
  Modello: `db/pgtap/vendite/test-push-contratto-dalla-madre-v1.sql`.
* **Un elenco esplicito di colonne si presidia per differenza**: una tabella
  temporanea delle escluse con la loro ragione, le colonne nominate lette dal
  corpo vivo della funzione, e l'asserzione che `pg_attribute` meno nominate
  meno escluse sia vuoto. La prossima colonna fa rosso finché qualcuno decide.
  Modello: `db/pgtap/vendite/test-fn-crea-revisione-preventivo-riga-completa-v1.sql`.
* **Adeguare un test a una firma che distingue più casi non è tradurre**: si
  asseriscono tutti i campi, non il primo.

### Il testo di un oggetto di catalogo dipende da chi legge

Il testo che PostgreSQL stampa per un oggetto dipende dal `search_path`:
`x::regclass::text`, `regprocedure::text`, `pg_get_viewdef`,
`pg_get_function_sqlbody` e `pg_policies.qual` tolgono lo schema quando è nel
percorso, e l'applicazione nel percorso ha più schemi del proprietario.

* **Si confrontano gli OID** (`'config.x'::regclass::oid`), o il nome si compone
  con `format('%I.%I', nspname, relname)`. Una regex su un testo di catalogo
  scrive lo schema facoltativo, o legge sotto
  `SET LOCAL search_path = pg_catalog`. Un conteggio atteso a zero su quel
  filtro è verde anche col difetto: gli serve il gemello «esiste».
* **Il tipo `name` ha collation `C`.** Un'espressione costruita da `relname`,
  `proname`, `nspname` o `conname`, confrontata in `results_eq` o ordinata
  insieme a testo normale, solleva un errore di ordinamento e il file si ferma
  lì: porta `COLLATE "default"`.
* **Dentro `format()` un booleano esce `t` o `f`**, mentre `bool::text` dà
  `true` o `false`: in un `is()` su una stringa composta ogni booleano porta
  `::text`, oppure l'atteso si scrive con `t`/`f`.

### Chiamare prima, asserire dopo, leggere una volta

* **La funzione sotto esame non si chiama dentro la `SELECT` che ne conta gli
  effetti.** Le sottoquery sorelle leggono le tabelle com'erano all'inizio
  dell'istruzione, e il rosso accusa la funzione invece del test. Il verbo si
  chiama prima (`CREATE TEMP TABLE … AS SELECT * FROM fn_…`) e si asserisce
  nell'istruzione dopo; fa eccezione l'asserzione che legge solo il valore di
  ritorno.
* **Ciò che più asserzioni leggono senza che in mezzo cambi niente si copia una
  volta in una `TEMP TABLE`, dopo la riga di contesto.** La copia contiene le
  righe che la RLS lascia vedere a quell'operatore: il test non si indebolisce,
  paga il filtro una volta sola. Una fotografia per momento: dopo una scrittura
  si rilegge l'oggetto vivo.
* **Fa eccezione l'asserzione sul perimetro**: chiedere a una copia se la policy
  filtra misura il filtro su una tabella che la policy non ha.

## Quando il test non può girare come l'applicazione

Prima di tutto: **è quasi sempre un difetto della fixture.** Il marcatore serve
a un caso solo.

> ⭐ **il SOGGETTO del test non è raggiungibile dall'applicazione.**

```sql
-- pgtap-runner: owner
-- pgtap-runner-motivo: <perché, in chiaro>
```

Il motivo è **obbligatorio**: senza, il runner esce con codice 4. Le tre forme
ammesse e — soprattutto — **l'elenco di cosa il criterio esclude** stanno
nell'intestazione di `scripts/testpgtap.sh`.

**In una riga: se l'applicazione quella cosa la fa, il marcatore è sbagliato.**

Tre casi in cui il soggetto è davvero fuori dalla portata dell'applicazione:

* **un presidio che conta su tutta la tabella.** `count(*) = 0` su una tabella
  sotto policy, come applicazione, è verde anche a tabella piena: il presidio
  dichiara il marcatore col motivo, e si vede rosso almeno una volta (sopra,
  §«La prova di mutazione»);
* **un test su `pgagent.*`**: il ruolo applicativo non ha accesso allo schema.
  E dove pgAgent non è installato, come in CI, la fixture sta in un blocco con
  `EXCEPTION` che porta a uno `skip()` col motivo. Presidio: `scripts/guardrail_forme_changeset.py`, regola `pgtap-pgagent-owner`. Un test
  che legge `pgagent` solo dopo `has_schema_privilege`, e si salta, lo dichiara in testa:
  `-- pgtap-pgagent-owner: ammesso — <perché>`;
* **un test che fa DDL su una tabella del modello** (`CREATE TRIGGER`,
  `DROP TRIGGER`, `ALTER TABLE`). ⚠️ Dichiara prima `SET LOCAL lock_timeout`:
  quel DDL prende un lock esclusivo fino al `ROLLBACK`, aspetta ogni transazione
  aperta sulla tabella e intanto ferma chi la usa. Il timeout non rende il test
  più veloce: fa di un'attesa muta un errore che si legge.

## Ciò che una sessione sola non prova

Un pgTAP è una transazione in una sessione: lock, attese e ciò che parte al
`COMMIT` da lì non si vedono.

* **Un advisory lock si asserisce nella struttura**: il corpo della funzione
  (`pg_get_functiondef`) contiene `pg_advisory_xact_lock`, come in
  `db/pgtap/vendite/test-ordini-lock-cliente.sql`. Dentro la stessa sessione il
  lock è rientrante, e il comportamento non si osserva.
* **Il ramo «lock occupato»** si raggiunge facendo tenere il lock a una seconda
  connessione `dblink`, aperta sul DSN di `myapp.dblink_log_connection`; dove il
  DSN non si apre il test fa `skip()` col motivo. La riga che la funzione scrive
  si legge in un'istruzione successiva. Modello:
  `db/pgtap/maintenance/test-job-run-saltata-v1.sql`.
* **Che una funzione serializzi** si prova con due sessioni vere, ognuna con le
  sue fixture in una transazione che finisce in `ROLLBACK`, e lo si dichiara. Il
  verdetto non è il messaggio della seconda, uguale con e senza attesa: è
  `pg_locks` con la stessa chiave concessa a una e negata all'altra, più la
  durata della seconda chiamata. ⚠️ `hashtext` è un intero con segno e
  `pg_locks` lo stampa senza: le chiavi si confrontano modulo 2³².
* **Un `NOTIFY` parte al `COMMIT`**, che qui non arriva: si prova con due
  sessioni `dblink`, una in `LISTEN` e una che committa un'istruzione a zero
  righe (un trigger per istruzione scatta lo stesso), chiudendo ogni fase con
  una notifica sentinella invece di un'attesa a tempo. Modello:
  `db/pgtap/script/test-notify-permessi-catalogo-v1.sql`. ⚠️ `dblink_exec`
  rifiuta un'istruzione che restituisce righe (`SELECT fn()` → `2F003`): va
  dentro un `DO`. Se l'errore finisce in un `EXCEPTION … skip()`, il test va
  sempre in skip. E nella prova prima dell'apply la DDL estratta tiene i lock
  che la seconda sessione aspetta: un `SET lock_timeout` su quella sessione fa
  di un'attesa infinita uno skip col motivo.

## Provare un test prima che il changeSet sia applicato

Un test che esercita una funzione non ancora applicata si prova con
`scripts/prova_changeset.py`: legge l'SQL dai changeSet, lo esegue in testa al
test dentro la stessa transazione e chiude con `ROLLBACK`. Fa due corse, senza e
con l'SQL nuovo, e confronta gli esiti.

```bash
scripts/prova_changeset.py <changeSet.yaml> … --pgtap db/pgtap/<schema>/test-<cosa>.sql
```

Gira sullo scratch e da proprietario degli oggetti, perché la DDL lo richiede:
i test di perimetro lì sono rossi nelle due corse, e l'esito come applicazione
arriva dopo l'apply. I limiti sono elencati nell'intestazione dello script.

⚠️ **Il fuso della prova non è quello del runner.** `scripts/testpgtap.sh` fa
girare ogni file in un fuso il cui giorno è diverso da quello aziendale; la prova
gira nel fuso della sessione. Un test che dipende dalla data (`CURRENT_DATE`, una
regola «da oggi») si prova anche con `PGTZ=Pacific/Kiritimati` davanti al comando,
altrimenti la prova è verde dove la corsa vera è rossa.

⚠️ **Il confronto prova solo i file che arrivano in fondo.** Si legge così:

* **una regressione sta su due numeri**, le asserzioni eseguite e i fallimenti.
  Meno asserzioni con gli stessi rossi è una regressione: il file muore prima.
  Un rosso che sparisce va spiegato prima di essere creduto;
* **stessi `skip` o stesso errore nelle due corse non è verde: è non provato**,
  e così si dichiara. Un file già rosso prima, o che salta le asserzioni (`skip`
  conta come `ok`), è un buco nella rete: si legge la sua fixture rispetto a ciò
  che il cambio giudica. Per i presidi che elencano si confronta il testo
  dell'elenco trovato, non il numero dell'asserzione;
* **i test da rilanciare si trovano leggendoli, non contando gli esiti**: quelli
  che attraversano il verbo cambiato (soprattutto le fixture che fanno la
  transizione fuori da un'asserzione) e, quando cambia il **valore** di un campo
  — una capability, una colonna di vista — quelli che in `db/pgtap/` nominano
  quel campo. Un test che ne fissa il valore vecchio può stare in un altro
  dominio.

## Prima di dire «fatto»

```bash
scripts/testpgtap.sh db/<schema>/test-<cosa>.sql   # il tuo test
scripts/pgtap-baseline.sh <schema>                 # nessuna regressione nello schema
scripts/pgtap-baseline.sh --modificati             # solo i pgTAP toccati nell'albero
python3 scripts/guardrail_pgtap_preambolo.py       # le invarianti di preambolo
```

`--modificati` esegue i `.sql` di `db/pgtap/` che git vede cambiati rispetto a `HEAD`, più quelli
nuovi: dice se i **test** toccati sono verdi. Se hai cambiato una funzione o un trigger non basta,
perché i test che la esercitano non sono fra i file modificati: lì serve lo schema.

⚠️ **La baseline è un registro di debito, non una lista di eccezioni**: deve
calare. Un file che fallisce nella *fixture* non esegue **nessuna** asserzione —
la sua copertura vale **zero**, non «parziale», ed è un'area che *sembra*
coperta.

⚠️ **Un test che diventa verde va spiegato prima di essere creduto.** Nel
cantiere è successo tre volte. E vale al contrario: «6 o 0 asserzioni» sembrava
un'oscillazione fra verde e rosso, ed erano **due difetti in fila** con il file
sempre rosso.

⭐ **E un test nuovo si vede rosso prima di dirlo fatto**: sopra, §«La prova di
mutazione».

⛔ **Il perimetro di una prova non è una cartella.** Un guard difende una
**tabella**, e chi ci scrive può stare in qualunque schema. La lista dei test si
ricava dai nomi toccati — `grep -rln 'schema.tabella\|nome_funzione' db/pgtap/`
— e la baseline si lancia su ogni schema che quella lista nomina. Una funzione
plpgsql nuova passa anche dai presidi che guardano **tutte** le funzioni, che i
test del cantiere non coprono: `dbops/test-riferimenti-morti-v1` (compila ogni
corpo), `script/test-rubinetto-primo-motivo-v1` (l'elenco esatto di chi chiama
`fn_raise_primo_motivo_se_presente`), `script/test-catalogo-messaggi-errore-completo`
e, per una `SECURITY DEFINER`, `dbops/test-security-definer-search-path-v1`.

⚠️ **Come si legge l'esito di un file.**

* **Il metro è «asserzioni eseguite contro il piano»**, non l'assenza di
  `not ok`: un file fermato a metà da un'eccezione non ne stampa nessuno. E un
  errore **dopo** l'ultimo `ok` lo rende rosso lo stesso: si leggono tutti gli
  errori, separati dagli avvisi.
* **Fuori dal runner `psql` va lanciato con `-v ON_ERROR_STOP=1`**, e l'errore
  si cerca ovunque nella riga (`psql:file:riga: ERRORE:`), non a inizio riga.
* **Un file in transazione non ha cleanup in coda**: lo fa il `ROLLBACK`, e un
  `DELETE` finale è solo un altro punto in cui un guard nuovo può fermarlo.

⚠️ **Come si legge un rosso della baseline.**

* **Un rosso vero non cambia nome fra due corse.** Prima di attribuire una
  regressione al proprio lavoro, o di registrarla, si rilancia e si confrontano
  i due elenchi; i sospetti si provano poi uno per uno. Un file rosso nella
  corsa e verde da solo dipende dalla corsa, non dal codice.
* **La suite legge i test dall'albero di lavoro nel momento in cui gira**: non
  si lancia durante un rebase o un cambio di ramo. Un rosso il cui messaggio
  corrisponde alla versione precedente del file è un rosso della corsa, non del
  database: si rilancia ad albero fermo.

## Girano in CI?

**Sì, ma non sempre.** La suite costa ~7 minuti:

| quando | gira? |
|---|---|
| PR verso `main` | ✅ sempre — è il cancello prima dell'integrazione |
| push su `Tito-dev` che tocca `db/` o `scripts/` | ✅ |
| push su `Tito-dev` che **non** tocca il DB | ❌ |
| PR verso `Tito-dev` | ❌ — basta il cancello statico sul preambolo |

Il perché è misurato: sui 30 giorni al 2026-08-07 `Tito-dev` ha avuto **656
commit**, di cui **155** toccano `db/` e **107 solo `backend/`**. È anche il ramo
di scambio fra backend e DB, quindi buona parte del traffico non riguarda il
database — e lì la suite girerebbe per niente. Farla solo verso `main`, invece,
la farebbe arrivare troppo tardi: il rosso spunterebbe mescolato a giorni di
lavoro altrui, e bisecarlo costa più dei minuti risparmiati.

⚠️ **In CI la baseline è un'altra**: `db/pgtap/baseline-rossi-ci.tsv`. Il
database della CI è **ricostruito da zero**, quello di sviluppo ha dati veri: i
test che dipendono da dati preesistenti falliscono là e non qui. Confrontare le
due popolazioni produrrebbe decine di finte regressioni — lo stesso difetto di
metro disomogeneo da cui è nato tutto.

Quindi: **un rosso in CI non è automaticamente un rosso da te, e viceversa.**
Prima di inseguirlo, guarda quale baseline lo conosce.

⭐ **E la baseline della CI si aggiorna DALLA CI** — `--update` su quel file
fuori da GitHub è un cancello (`exit 2`), perché la misura dello scratch non è
la sua: il 14-09 lo scratch dava 33 «verdi non registrati», la CI ne dichiarava
31, e i due elenchi differivano di quattro file. La CI però non committa: stampa
l'elenco RIENTRATI, e per due giorni nessuno l'ha trascritto. Da quel giorno:

```bash
scripts/pgtap-baseline-ci-rientrati.sh            # ultima corsa utile su Tito-dev
scripts/pgtap-baseline-ci-rientrati.sh <run-id>   # una corsa precisa
```

legge il log della corsa di GitHub (`gh`), toglie da `baseline-rossi-ci.tsv`
**quelle** righe e stampa le regressioni senza aggiungerle — un rosso nuovo entra
nel registro solo per decisione. ⚠️ GitHub ritira i log dopo pochi giorni
(`410`): l'elenco si prende dalla corsa mentre c'è.

⚠️ **E un `ERRORE_FIXTURE` in CI si legge, non si indovina.** La baseline stampa
solo l'etichetta: il messaggio vero sta nel **log del container Postgres**, che
GitHub scarica per intero nel passo «Stop containers» del job
(`gh run view <run> --job <job> --log`, poi cercare `ERROR:` con lo `STATEMENT:`
che segue). Il 2026-09-13 quel log ha detto in una riga ciò che due giorni di
confronto con lo scratch non dicevano: **47 × `permission denied for table
auth_user`**, cioè 23 file morti per un privilegio che esisteva solo su dev —
e lo scratch era verde perché **copiava** quel privilegio insieme allo schema
`django` ([linee-guida-sql §11.9](/linee-guida-sql)). Lo scratch è un metro
finché riceve la configurazione dalla stessa sede della CI; quando la copia da
dev, misura dev.

⚠️ **E l'etichetta di un rosso noto è quella del giorno in cui è entrato.** Il
confronto con la baseline guarda solo la presenza del file e non rinfresca la
causa (`ERRORE_FIXTURE`, `ASSERZIONE`): prima di ragionare sul perché di un
rosso noto lo si rilegge nel log del container della corsa.

## Perché una guida non basta

Chi ha scritto queste regole ne ha violata una **poche ore dopo averla
scritta** — «un requisito che vive in due posti si dimentica in uno dei due» —
duplicando il default del runner in due script.

Per questo l'ordine di efficacia è: **template → cancello → guida**, e questa
pagina è l'ultimo dei tre. Serve per ciò che non si automatizza: *da chi difende
questo guard? cosa vorrebbe dire davvero questa asserzione?* Il resto lo devono
fare il template che copi e il cancello che ti ferma.

---
{% include-markdown "signature-core.md" %}
