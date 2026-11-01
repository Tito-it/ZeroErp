# Mappa Concentrica — Changelog

> **Ultimo aggiornamento**: 31 ottobre 2026

> Cronologia datata degli aggiornamenti della [Mappa Concentrica](../mappa-concentrica.md).
> La mappa mostra solo lo **stato corrente** per anello; questo documento conserva la storia,
> per non gonfiare il documento principale.
>
> Registra solo evidenze presenti nel repository: commit e documentazione
> `docs/it/dev/work-done/` o `docs/it/dev/work-in-progress/`. Dove la documentazione indica
> test UI o working tree non ancora consolidato, lo stato resta esplicitamente marcato come tale.
>
> ## Come si compatta un mese
>
> Le voci recenti si scrivono per **data di aggiornamento**; quando un mese esce
> dalla finestra di consultazione, le sue voci si fondono in **una voce mensile**
> (`## luglio 2026`). ⚠️ **Non a mese chiuso**: si aspetta che i brief di quel
> mese siano **tutti in `work-done`**, altrimenti si comprime rimandando a
> documenti ancora in movimento.
>
> ⭐ **Un documento aperto non ferma il mese intero** (Tid, 2026-11-01). Alcuni
> documenti restano in `work-in-progress` per costruzione o senza data: la
> valutazione dello strato DB è permanente, un copione di collaudo vive finché non
> si esegue, un piano può essere fermo su una decisione. Aspettarli vorrebbe dire
> non compattare mai. Quindi si compattano i temi i cui documenti sono **tutti** in
> `work-done`, e i paragrafi che citano un documento aperto restano **per intero**,
> in una sezione «Rimasti per intero» in fondo alla voce del mese, con la data
> della voce d'origine. Quando quel documento si chiude, il paragrafo si compatta
> come gli altri. Primo caso: settembre 2026.
>
> **Che cosa sopravvive alla compressione**, ed è la parte che conta:
>
> 1. il **nome del tema** — è la chiave con cui ci si ritorna;
> 2. **due o tre righe** su cosa è cambiato nel sistema, mai su *come*;
> 3. **tutti i link ai brief** — sono la ragione per cui il resto si può
>    tagliare: il dettaglio non si perde, si delega alla sua sede;
> 4. ⛔ **ciò che non ha un brief NON si comprime.** Comprimere un tema che ha il
>    suo brief è *delegare*; comprimere una riga che vive solo qui è
>    **cancellare**. Nel dubbio si cerca il documento: se non c'è, il testo resta.
>
> ⛔ **Si compatta in questo file, non in un archivio a parte.** I riferimenti ai
> documenti vivono anche nei `COMMENT` SQL e in changeSet già mergiati, che non
> si toccano: l'URL di questo changelog deve restare uno.

---

## 31 ottobre 2026

> Copre il periodo **27 – 31 ottobre**, per chiudere il mese: fotografato al 31-10 alle 23:59
> più un'ora, cioè al commit `40b3a35fb` (1° novembre, 00:30, l'ultimo prima dell'01:00). Cinque
> giorni, **217 changeSet** aggiunti (121 in `vendite`, 44 in `script`, 16 in `80_data`, 15 in
> `dbops`, 14 in `config`, 5 in `90_end`, 2 in `catalogo`), **29 PR** (dalla #1962 alla #1991),
> **due documenti entrati in `work-done`** (il brief del modello del documento di vendita e
> l'archivio della valutazione DB). Si scrive per **temi**: sono sei. La voce del 28 ottobre, qui
> sotto, resta com'è: riguarda la pulizia della roadmap, non il lavoro del periodo.
>
> ⚠️ Fuori da questa voce, perché dopo l'01:00 del 1° novembre: il passo 4 del canone in commessa
> (l'obbligo della periodicità sulla riga a canone) e la documentazione del suo giro del §7 (L18).

**Anello 3 (`vendite`) — Il modello del documento di vendita è chiuso: tutti i documenti
portati.** I giri 11-14 completano il cantiere aperto il 21-10. **La fattura** (giro 11,
27-10) entra nel modello dal suo **lotto**: i pulsanti restano sul lotto e il processo dei lotti
non cambia (Tid), ma le fatture seguono il lotto attraverso il verbo e non con un `UPDATE`; la
fattura ha anche un verbo suo (l'esito dello SDI), non ha un annullo (si storna con la nota di
credito), e «numera» e «riporta in bozza» chiedono la stessa azione, `numera_fattura`, mentre le
azioni mai usate si ritirano. Lo stato del job si allinea al DB senza copia nel backend. Le
**azioni per riga** hanno un pezzo standard (registro DB, lookup `azioni-riga`, BB FE
`useAzioneRiga`, `azioni_permesse` per riga di lista) e la stampa della fattura porta la **catena
delle origini** (forma 6) al posto del riquadro «origine» sempre vuoto (D-G1). **La versione di
listino** (giro 12, 28/29-10): lo stato diventa una colonna d'id verso il vocabolario, CHIUSA è
scritta dal job delle scadenze come la cessazione del contratto, l'attivazione è un verbo con la
sua azione `attiva_listino`, e «Elimina», «Chiudi» e «Clona» sono verbi coi motivi dei pulsanti
spenti — E-1 è una **revoca parziale**, dichiarata, di una regola del 13-05. **Il giro 13**
(31-10) dà agli stati un **significato dal vocabolario** (cessazione, accettazione, accanto a
emissione e aborto) con un lettore comune, e ritira i letterali `'CESSATO'`, `'ACCETTATO'`… da
verbi, lister, push e capability; **il giro 14** mette la revisione dell'offerta nel lineage
(l'arco V, anche nei «Passaggi») e ammette la motivazione solo dove il passaggio la chiede. Il BE
legge gli stati di cessazione, accettazione e iniziale dal vocabolario e ritira le sue copie; il
presidio di avvio di gunicorn gira in un processo figlio, e un `kill -HUP` torna a bastare. Chiuso
il 31-10 con le prove a video di Tid tutte ok, D-G2 compreso; i residui (le azioni `emetti_*` e
`attiva_listino` ai profili di dbdev, due rami del preventivo senza strada dall'interfaccia, il
drawer che non si carica in silenzio) passano a PROJECT_CONTEXT. Vedi
[brief-modello-documento-vendita.md](work-done/brief-modello-documento-vendita.md).

**Anello 3 (`vendite`) — La scadenza dei preventivi esiste.** EMESSO → SCADUTO era nella matrice
e nessuno lo scriveva. Decise il 31-10: lo stato resta **scritto da un processo** — la terza riga
del registro delle chiusure per scadenza, `vendite.fn_chiudi_preventivi_scaduti`, gemello della
cessazione dei contratti (E-1, completa il modello, non lo revoca); l'accettazione oltre «Valido
al» è rifiutata anche **per data**, così la regola non dipende dall'ora del job (E-2); la revisione
si apre anche da SCADUTO (E-3); e un preventivo non si emette con la validità già finita (E-4,
applicata il 1° novembre). Il passaggio BE/FE (i due codici, il campo «Valido al») e il collaudo a
video si chiudono lo stesso giorno. Vedi
[brief-db-scadenza-preventivi.md](work-done/brief-db-scadenza-preventivi.md).

**Anello 3 (`vendite`) — Il contratto si addebita anche a canone (D31).** Decisioni G-0 … G-11 il
28-10, lotti L1 … L9 dal 29 al 31-10: il vocabolario delle **periodicità** (la riga a canone la
porta, la quota fissa la prende dal listino), il tipo di riga **ADESIONE**, mese di partenza e
anticipato/normale sulla testata di contratto e offerta, la regola dei periodi in una funzione
sola (`vendite.fn_canone_periodi`: periodi dal giorno 1, proporzione sul periodo incompleto, un
periodo che scavalca l'anno si spezza, gli arretrati si recuperano), il push a periodi con gli
**storni** come differenza quando la fine si sposta, e la dashboard che torna a giudicare i
contratti (`CANONE_NON_GENERATO`, `CANONE_NON_GENERABILE`) leggendo la stessa sede del push. Il
giro del §7 (31-10): il **kit sul listino** con la sua periodicità, la **nota di credito dal segno**
del documento con le fatture citate, il controllo all'attivazione della versione, la quota fissa
che non perde la periodicità fuori dalla bozza. BE/FE del passo 3 fatto e committato, con il BB
`_campi_canone`. ⚠️ Aperti: il passo 4 (l'obbligo della periodicità sulla riga a canone), la
documentazione del giro (L18), la colonna «Periodicità» nella lista delle righe di listino, il
collaudo a video. Vedi
[brief-db-contratto-righe-periodiche-in-commessa.md](work-done/brief-db-contratto-righe-periodiche-in-commessa.md).

**Anello 1 (`ui`, `config`) — Le liste ancora su `DataTable` grezza, secondo giro.** Sette liste
nascono a catalogo (107-113: definizioni di workflow, parametri, note di vendita e di catalogo,
UoM dell'articolo, versioni di listino, ricerca dei soggetti), e la conversione chiude due difetti
che non davano errore: le note **troncate a 200** senza paginatore, e la regola «versione di
listino in scadenza senza successore» scritta in SQL nel repository BE, ora
`vendite.fn_listini_in_scadenza_senza_successore` col preavviso a parametro. Un presidio pgTAP
tiene allineate le liste gemelle delle note. Nello stesso giro: la ricerca universale cerca sui
campi del catalogo e prende la soglia dal catalogo come ogni lista (D-6), e la **forma del valore
di un parametro** è rispettata in scrittura (D-5). Lato FE i BB `TabellaSelezioneRighe` (i tre
dialog di selezione righe) e `MatriceCatalogo` (la base di ogni matrice limitata dal catalogo, di
cui `MatriceOverride` è uno strato); il registro del presidio scende da **28 a 17** `DataTable`
grezze, da **9 a 0** senza motivo, e il motivo deve stare attaccato all'import. ⚠️ Aperto: la view
della ricerca che legge la soglia dal catalogo (§7.8.5, BE), poi l'archiviazione. Vedi
[brief-db-liste-datatable-grezze-secondo-giro.md](work-in-progress/brief-db-liste-datatable-grezze-secondo-giro.md).

**Anello 1 (permessi) — Il profilo del reparto per area, e il tetto d'area detto dal DB.** Il
profilo del reparto si gestisce **per area**, come l'operatore, sopra un BB nuovo,
`ElencoDettaglio` (elenco a sinistra, dettaglio a destra; il pannello dell'operatore migrato), e
in sola lettura i controlli sono spenti anche dentro un drawer in sola lettura. Sui valori salvati
il limite dell'area lo dice il DB (`limitata_da_area`, da `script.fn_area_consente_azione`): il
FE lo calcola solo in anteprima («sola regola DB», Tid). La documentazione della v3 dava ancora il
tetto d'area per aperto: è chiuso dal 04-10, e ora lo dice. Nello stesso giro le Utilities
dell'emittente salvano anche una configurazione nuova e hanno i decimali del CHECK DB. Vedi
[permessi-e-autorizzazioni-v3.md](work-in-progress/permessi-e-autorizzazioni-v3.md),
[brief-db-permessi-tetto-area.md](work-done/brief-db-permessi-tetto-area.md).

**Trasversale — La catena di verifica: il documento vivo si separa dal suo archivio.** Il 27-10 la
valutazione dello strato DB tiene **solo ciò che è vivo** (chi riparte, difetti aperti, scorecard)
e il resto — la valutazione di febbraio, le voci chiuse, i riallineamenti — passa a un archivio in
`work-done` con la stessa numerazione, perché i rimandi «§D13» dai changeSet restino validi. D7,
lotti 3 e 4: il registro dello scratch scende da 104 a 23 righe, quello di sviluppo da 6 a 4,
quello della CI da 360 a 358 (le misure del 28-10, qui sotto). Al 31-10 la suite pgTAP conta
**935** file, i tre registri sono invariati. Vedi
[migliorie-generali-da-test-valutazione.md](work-in-progress/migliorie-generali-da-test-valutazione.md),
[migliorie-generali-da-test-valutazione-storia.md](work-done/migliorie-generali-da-test-valutazione-storia.md).

## 28 ottobre 2026

**Trasversale — la roadmap della mappa torna a dire solo ciò che è aperto.** Le
celle «In corso» del §3 avevano riaccumulato la storia delle voci chiuse; ora
portano solo ciò che resta, e il chiuso sta qui e nei brief:

- **Catena di verifica**: chiusi D1, D2, D3, D4, D6-registro, D7 col giro 2,
  D10, D13, D14 —
  [migliorie-generali-da-test-valutazione.md](work-in-progress/migliorie-generali-da-test-valutazione.md)
- **Osservabilità** esce dalla roadmap: sette passi su sette a codice,
  collaudo in-app chiuso, analisi e diagnostica di produzione archiviate; i
  residui sono sotto «Previsti» —
  [piano-be-fe-osservabilita-pallino-e-superfici.md](work-done/piano-be-fe-osservabilita-pallino-e-superfici.md),
  [collaudo-in-app-osservabilita-giornale-errori-pallino.md](work-done/collaudo-in-app-osservabilita-giornale-errori-pallino.md)
- **Modello del documento di vendita**: la commessa (giro 10) è portata;
  fattura (giro 11) e versione di listino (giro 12) hanno il DB applicato e
  aspettano il BE; D-N1 è entrata nel giro 11, D-G1 decisa —
  [brief-modello-documento-vendita.md](work-done/brief-modello-documento-vendita.md)
- **Accessi**: L-2, L-4, L-6 e il collaudo del consenso al riuso erano chiusi
  ma la mappa li dava aperti; resta L-5 (R-4) e il collaudo di D-5 —
  [piano-be-fe-accessi-credenziale-e-vesti.md](work-in-progress/piano-be-fe-accessi-credenziale-e-vesti.md)
- **Incassi, magazzino, permesso nel verbo**: ridotti a ciò che resta (la prova
  a video; collaudi e residui del piano §5; il passo 3)

Misure rifatte sui registri: **4 rossi** su **917 file** sul database di
sviluppo, **358** nel registro della CI, **23** in quello dello scratch.
Contemporaneamente il [readme](../readme.md) perde il suo elenco di lavori
aperti, che faceva da seconda roadmap, e i numeri che invecchiavano.

## 26 ottobre 2026

> Copre il periodo **14 – 26 ottobre**, fotografato al 26-10 alle 23:59 (commit
> `54c439012`, PR #1961, l'ultimo del giorno). Tredici giorni, **624 changeSet**
> datati fra il 14 e il 26 (200 in `vendite`, 130 in `script`, 115 in `dbops`,
> 58 in `anagrafiche`, 36 in `config`, 20 in `documenti`, 16 in `maintenance`,
> 14 in `catalogo`, 14 in `80_data`), **trenta documenti entrati in
> `work-done`** e **100 PR** (dalla #1858 alla #1961). Si scrive per **temi**:
> sono nove. La voce singola del 23 ottobre (gli indicatori di qualità) è
> confluita qui, nell'ultimo tema, con il suo testo.
>
> ⚠️ Fuori da questa voce, perché del **27 ottobre**: il giro 10 del modello
> (la commessa) oltre la ricognizione, e i changeSet `20261027-*` del lotto di
> fatturazione.
>
> ⭐ **Il tema portante è *un documento alla volta, tutto intero, su un modello
> scritto una volta*.** Fino al 13-10 si portava un tema alla volta su nove
> documenti; la ricostruzione del 21-10 trova che non c'erano revoche, c'erano
> **copie**: 11 capability, 11 guard di transizione, 8 verbi d'annullo, ognuno
> con la sua variante. Da lì le regole stanno in **una guida**, e i documenti ci
> entrano uno per giro. *«Non mi sto più fidando… una volta in un modo, poi in un
> altro, poi si torna al precedente»* (Tid, 21-10) — e la regola che ne esce: *da
> lì una proposta che non è nella guida, o la contraddice, si dichiara come
> revoca*.

**Anello 3 (`vendite`) — Il modello del documento di vendita: una guida, un
giro per documento.** Il cantiere apre il 21-10 e il 24-10 Tid decide il
modello: ogni cambio di stato passa da **un verbo DB** (M-1); si emette solo da
`/emetti/`, con numero e PDF nella stessa transazione (M-2, **revoca
dichiarata** delle scelte del 05-06 sull'ordine e dell'11-07 sul DDT); l'azione
sta sulla riga della matrice (M-3), una sola azione sui passaggi pesanti — *chi
fa disfa* (M-4) —, e le matrici scritte nel codice passano in tabella (M-5). Il
25-10: la porta è un guard sulla colonna di stato, il verbo un BB comune. Le
regole vivono nella [guida del modello](../guide/modello-documento-di-vendita.md),
approvata il 25-10. Si ottimizza per la velocità: le rotture BE sono accettate
fino alla chiusura del giro BE, e *acquisti nasce sul modello, non lo rincorre*.
Al 26-10: giri 1-4 (nascita in bozza, builder, debiti, pezzo comune) e i giri
del **DDT** (con il DDT d'acquisto), del **preventivo**, dell'**ordine** e del
**contratto** (il passaggio X → X ha un codice, `E_DOC_GIA_NELLO_STATO`) chiusi
DB e BE; l'**offerta** (giro 9) applicata e verde, BE committato
con la PR #1961; la **commessa** (giro 10) alla ricognizione, con C-2 e C-3 aperte. Dentro
il primo giro è confluito D32: **un documento nasce nel suo stato iniziale** —
un `INSERT` già avanti è rifiutato da un BB unico su testate di vendita e
d'acquisto, e la bolla nata EMESSA, numerata e vuota, non è più possibile. Sul
lotto di fatturazione la regola R-1: *«non può esistere un documento definitivo
se un altro dello stesso lotto è in errore»*. ⚠️ Aperti: i giri di fattura e
listino, D-N1 (i gate delle azioni per riga), D-G1 e D-G2 ereditati dalla
grammatica, i profili su dbdev che non hanno `emetti_offerta`/`emetti_contratto`/
`emetti_ordine`, la scadenza dei preventivi (brief nuovo, E-1…E-3 a Tid). Vedi
[brief-modello-documento-vendita.md](work-done/brief-modello-documento-vendita.md),
[brief-db-documento-nasce-nello-stato-iniziale.md](work-done/brief-db-documento-nasce-nello-stato-iniziale.md),
[brief-db-scadenza-preventivi.md](work-done/brief-db-scadenza-preventivi.md).

**Anello 3 (trasversale) — Un nome per ogni tipo di documento, e l'offerta che
genera l'ordine.** La **grammatica unica** (18 → 25-10) dà al tipo di documento
un nome solo per DB e backend, senza ponti: vince il `codice_interno` di
`config.sorgenti`, i nomi corti (`DDT`, `ORDINE`, `OFFERTA`, `RESO`) si
ritirano, `config.tipi_entita` resta il catalogo dei bersagli legato da un
vincolo; righe, varianti, `acquisti`, `magazzino` ed `EMAIL_BOZZA` dentro. In
cinque lotti — catalogo, eccezioni, lettori di testate/indirizzi/origine/chiavi
del push, note, presidio —; la chiave id/uid resta doppia, e la FK lega il nome,
non l'accensione. L'**offerta** (21/22-10) si emette e si eroga come le altre:
la riga `DERIVATA_COMPONENTI` si ritira (i componenti seguono la quantità del
padre), un kit si vende a quantità fissa, «Genera ordine» diventa il verbo
`vendite.fn_genera_ordine_da_offerta` con il motivo spento prima del clic, e il
BE ritira la sua copia. Vedi
[brief-db-grammatica-unica-documenti.md](work-done/brief-db-grammatica-unica-documenti.md),
[brief-db-offerta-emissione-ed-erogazione.md](work-done/brief-db-offerta-emissione-ed-erogazione.md).

**Anello 2/3 (`documenti`, `catalogo`, `vendite`) — Il modello di stampa
standard, gli articoli che una riga può usare, il listino della commessa.** Un
emittente nuovo **emette dal primo giorno** (21-10): sei modelli standard nascono
dal seed già pubblicati, la risoluzione va prima al modello dell'emittente e poi
allo standard — conta solo un modello che può stampare —, «Personalizza» copia
lo standard e la coda di stampa stampa la versione risolta — *«la cosa
migliorativa è fornire un set di modelli standard»* (Tid, 18-10). **Quali
articoli può usare una riga lo dice il DB una volta sola**, per il picker e per
il guard (23-10; la struttura di un articolo con righe aperte si corregge in un
salvataggio solo). La **riga di commessa** (15→17-10) non contraddice la
provenienza del suo prezzo: la riga di listino porta la sua versione, il listino
è dell'emittente, mai un prezzo da una versione in BOZZA (nemmeno dal percorso
rapido del risolutore), e il guard non giudica più su un'assenza dovuta alla
RLS. ⚠️ Aperti: la numerazione della versione nuova (B-8), le righe d'acquisto
(nel cantiere `acquisti`), *quando* si scrive `listino_riga_id` (brief della
provenienza del prezzo). Vedi
[brief-db-modelli-documento-standard.md](work-done/brief-db-modelli-documento-standard.md),
[brief-db-articoli-ammessi-per-documento.md](work-done/brief-db-articoli-ammessi-per-documento.md),
[brief-db-coerenza-listino-della-riga-di-commessa.md](work-done/brief-db-coerenza-listino-della-riga-di-commessa.md),
[brief-db-provenienza-prezzo-segue-il-prezzo.md](work-in-progress/brief-db-provenienza-prezzo-segue-il-prezzo.md).

### Anagrafiche, indirizzi e magazzino — 26 ottobre

**Anello 1 (`anagrafiche`) — Il soggetto dice una cosa sola.** I **dati
fiscali e societari** si archiviano il 14-10 (PA e split payment per natura, un
verbo unico, la forma giuridica nella matrice della natura, i titoli IVA solo
dove la natura li ammette), e il loro erede (D34, 19→22-10) porta la stessa
regola alla **creazione**: le porte di nascita scrivono la sezione intera, la
ditta individuale non perde più in silenzio la sua, e una sezione passata a
una natura che non la prevede è rifiutata, non scartata. **Un cliente manuale
per soggetto e utility** (D33, 15-10): un solo cliente attivo per soggetto +
utility + emittente, misurato sul periodo; un cliente chiuso non si riapre, si
apre una catena nuova; il cliente ha il suo grafo di stati — *«va impedito»*
(Tid). **Un indirizzo fisico, una riga** (25-10): «senza civico» si scrive in un
modo solo, il trova-o-crea cerca sui valori normalizzati e riattiva una riga
spenta, una modifica che collide ha il suo codice. ⚠️ Aperti: D-4
(`COOPERATIVA`) e i titoli IVA fuori regola (PROJECT_CONTEXT § «Aperto»), il
cambio di natura, la catena delle istanze sul PDP (D18), il trasloco di uno
solo (D6 del civico, senza brief). Vedi
[brief-db-dati-fiscali-e-societari-del-soggetto.md](work-done/brief-db-dati-fiscali-e-societari-del-soggetto.md),
[brief-db-dati-societari-in-creazione.md](work-done/brief-db-dati-societari-in-creazione.md),
[brief-db-cliente-manuale-uno-per-soggetto-e-utility.md](work-done/brief-db-cliente-manuale-uno-per-soggetto-e-utility.md),
[brief-db-unicita-civico-indirizzi-dettaglio.md](work-done/brief-db-unicita-civico-indirizzi-dettaglio.md),
[brief-db-cambio-natura-soggetto-conferma-e-pulizia.md](work-in-progress/brief-db-cambio-natura-soggetto-conferma-e-pulizia.md),
[brief-db-catena-istanze-pdp.md](work-in-progress/brief-db-catena-istanze-pdp.md).

**Anello 3 (`vendite`, `magazzino`) — Il documento segue il suo cliente, la
merce segue il documento.** Gli **indirizzi del documento** appartengono al
cliente del documento (D27, 19-10): se il cliente cambia in bozza il DB rifà lo
slot di default, restano solo gli una-tantum, e il controllo è un motivo del
gate d'emissione; slot e ripiego diventano un dato, la scheda di fornitura
segue il cliente, ed emittente e utility sono fermi in modifica su preventivo,
offerta e contratto. In `magazzino` i **Lotti 3 e 3-bis** si archiviano il 14-10
(lato DB applicato a fine settembre, BE/FE del 12/13-10): la merce esce
all'emissione della bolla e rientra alla conferma del reso, al costo
dell'uscita d'origine e sullo stesso lotto e seriale. Lo stesso giorno i motivi
della conferma del reso portano **i numeri**, come la bolla, e il copione del
collaudo a video è scritto. Il 24-10 passa a video il collaudo della
**capability annidata e dei prezzi autorizzati**. ⚠️ Aperti: il collaudo a video
della bolla e del reso (scritto, da eseguire) e dell'inventario, la CI da zero
del magazzino, la merce in viaggio; il reset del rifiuto del prezzo, che sta
solo nel BE del preventivo. Vedi
[brief-db-indirizzi-documento-seguono-il-cliente.md](work-done/brief-db-indirizzi-documento-seguono-il-cliente.md),
[brief-db-magazzino-lotto-3-scarico-da-ddt.md](work-done/brief-db-magazzino-lotto-3-scarico-da-ddt.md),
[brief-db-magazzino-lotto-3-bis-carico-da-reso.md](work-done/brief-db-magazzino-lotto-3-bis-carico-da-reso.md),
[brief-db-reso-motivi-conferma-con-valori.md](work-done/brief-db-reso-motivi-conferma-con-valori.md),
[collaudo-in-app-magazzino-bolla-e-reso.md](work-in-progress/collaudo-in-app-magazzino-bolla-e-reso.md),
[collaudo-in-app-capability-annidata-e-prezzi-autorizzati.md](work-done/collaudo-in-app-capability-annidata-e-prezzi-autorizzati.md),
[piano-be-fe-magazzino-lotto-3.md](work-in-progress/piano-be-fe-magazzino-lotto-3.md).

### Nucleo, contratto delle API e verifica — 26 ottobre

**Anello 0 — L'installazione è un dato: ruoli fissi, ambiente dichiarato,
processi accesi per ambiente.** I **ruoli di sistema** (15-10) fanno parte del
prodotto — `zeroerp_owner`, `zeroerp_app`, `zeroerp_job`, `zeroerp_log` — creati
da un solo script idempotente per CI, scratch e installazione, senza password
di default: chi vuole personalizzare *aggiunge un membro, non rinomina*, e *si
controlla che cosa può fare il ruolo, non come si chiama*. `zeroerp_log` nasce
nella fase dei ruoli (D35, lo stesso giorno), e le tre sedi a mano spariscono.
L'**ambiente** (`SVILUPPO`/`PRODUZIONE`) è un dato scelto all'installazione e
senza default — *SVILUPPO non capita per caso* —, l'accensione dei processi ha
un default per ambiente con l'accensione a mano da interfaccia, sette processi
non si spengono mai, e i BB-madre del provisioning (emittente, BA, cliente,
fornitore, veste, indirizzi, profili) sostituiscono le copie del BE (19-10). Gli
**utenti di sviluppo** sono un insieme fisso creato da un verbo che **rifiuta
di partire in produzione** (22-10). Le **statistiche** di tutte le tabelle hanno
un job notturno con autoverifica (D15, 15-10), e gli **smoke girano ogni notte**
sul DB di sviluppo, dove ci sono i dati (D9-a, 14-10). I presidi dei job
parlano a chi tocca: ogni processo dichiara una **causa di fallimento**
(ambiente → sistemista, programma → sviluppo, configurazione →
amministratore), una corsa con elementi falliti chiude rossa, e dove ogni corsa
rifà tutto il verde di oggi spegne il rosso rientrato (18-10). ⚠️ Aperti: i 2
smoke non verdi su 51 (resi-vendita, nota-credito-resi, senza brief), il
`%TYPE` del primo giro del presidio (PROJECT_CONTEXT § «Aperto»). Vedi
[brief-db-ruoli-di-sistema.md](work-done/brief-db-ruoli-di-sistema.md),
[brief-db-zeroerp-log-nella-fase-ruoli.md](work-done/brief-db-zeroerp-log-nella-fase-ruoli.md),
[brief-db-processi-accensione-per-ambiente.md](work-done/brief-db-processi-accensione-per-ambiente.md),
[brief-be-utenti-di-sviluppo.md](work-done/brief-be-utenti-di-sviluppo.md),
[brief-db-statistiche-tabelle-job-notturno.md](work-done/brief-db-statistiche-tabelle-job-notturno.md),
[brief-db-presidio-job-run-a-chi-tocca.md](work-done/brief-db-presidio-job-run-a-chi-tocca.md),
[brief-db-intermittente-e-verdetto-completo.md](work-done/brief-db-intermittente-e-verdetto-completo.md).

**Anello 0/1 — Chi guarda si calcola una volta, e un parametro uguale per tutti
lo è davvero.** **D-3b chiude il 18-10** e con lei il brief delle forme dei
piani (D26-2): il verbo dell'accredito passa da circa 115 a **50,6 ms**, il
perimetro dell'operatore si calcola **una volta per istruzione** in tutte le
policy ef_whitelist (linee-guida-sql §10.3, con un presidio), il `tx_id` va
sulla connessione di log persistente. Il 21-10 (D36) la stessa regola copre le
famiglie rimaste — cliente, portale, shop, fornitore, email e note — e il
debito del presidio va a zero. I **parametri senza override** (26-10) smettono
di esistere solo come frase di una descrizione: una colonna
`ammette_override`, un guard nei due versi con il suo codice, la lista
dell'amministratore che non mostra più come effettivo un override che nessuno
usa; i dati societari di default restano per emittente. Vedi
[brief-db-plancache-funzioni-con-query-incorporate.md](work-done/brief-db-plancache-funzioni-con-query-incorporate.md),
[brief-db-perimetro-una-volta-famiglie-residue.md](work-done/brief-db-perimetro-una-volta-famiglie-residue.md),
[brief-db-parametri-senza-override.md](work-done/brief-db-parametri-senza-override.md).

**Backend — La documentazione delle API è uguale al codice.** La verifica
(20→24-10) copre **721 rotte su 721** in 17 aree: `order_by` fuori whitelist,
PATCH vuota e paginazione sbagliata danno 400 ovunque, i parametri hanno un
nome solo e niente alias, e l'**Idempotency-Key è obbligatoria su ogni POST che
scrive**, con la soglia letta dal DB — il BE non ricopia la regola — e le chiavi
nella pulizia; nasce la guida delle
[operazioni che non si ripetono](../guide/operazioni-che-non-si-ripetono.md).
PATCH e PUT parlano un dialetto solo (25-10). L'analisi dei difetti di `core`
chiude il 14-10 con tutte le voci. ⚠️ Non bloccanti: due lettori non migrati al
BB. Vedi
[brief-be-verifica-documentazione-api.md](work-done/brief-be-verifica-documentazione-api.md),
[analisi-be-difetti-emersi-verifica-doc-api-core.md](work-done/analisi-be-difetti-emersi-verifica-doc-api-core.md).

**Verifica e qualità — Le fixture passano per le strade vere, gli indicatori
hanno una sede.** I pgTAP smettono di ricopiare la strada «bolla consegnata da
ordine» (36 file) e quella del reso: **nove builder** nuovi — ordine con righe,
bolla senza ordine, reso, ri-consegna, fattura dell'attività — e un centinaio di
file portati senza regressioni (25-10); il criterio: *entra in un builder ciò
che ha una trappola d'ordine, non ciò che serve spesso*. Per strada due «verdi
per sottrazione» chiusi. Vedi
[brief-db-pgtap-bolla-e-reso-costruiti.md](work-done/brief-db-pgtap-bolla-e-reso-costruiti.md),
[brief-db-pgtap-reso-costruito.md](work-done/brief-db-pgtap-reso-costruito.md).

**Qualità BE/FE (23-10) — la valutazione chiude, gli indicatori restano.** La
valutazione dello strato applicativo, aperta il 09-09, chiude con la sola D12
(i portali) aperta, che vive nel suo cantiere. Esce da «In corso» e lascia una
sede viva: [qualita-be-fe-indicatori.md](qualita-be-fe-indicatori.md), con le
lezioni, gli indicatori stampati da `scripts/indicatori-qualita-be-fe.sh` e la
scorecard pesata; il punto d'incontro con il lato DB è la mappa §4. Vedi
[migliorie-generali-BE-FE-da-test-valutazione.md](work-done/migliorie-generali-BE-FE-da-test-valutazione.md).

**Qualità del database (23-10) — gli indicatori hanno la loro sede.** Lo stesso giorno
il lato DB prende il documento gemello:
[qualita-db-indicatori.md](qualita-db-indicatori.md), con le lezioni della
valutazione DB, gli indicatori stampati da `scripts/indicatori-qualita-db.sh`
(il repo; con `--catalogo` anche le viste di presidio di dbdev) e la scorecard
pesata. La valutazione resta aperta in
[migliorie-generali-da-test-valutazione.md](work-in-progress/migliorie-generali-da-test-valutazione.md):
è la lettura zero, e ha ancora voci aperte. La riga «Database» della mappa §4
è agganciata.

**In breve, senza un tema proprio** — due brief nuovi: il `tx_id` inventato
nel giornale delle sospensioni delle pratiche, pronto per il team DB
([brief](work-in-progress/brief-db-pratiche-giornale-tx-id-senza-ripiego.md)),
e la scadenza dei preventivi, che aspetta le decisioni di Tid. pgTAP: **6 rossi** nel registro di dev (erano 7),
**360** nel registro della CI (fermo a 361 dal 22-09: il divario resta il
debito vero), **104** in quello dello scratch (erano 165), su **910 file**
(826 al 13-10). `DataTable` grezze ferme a **28** (9 senza motivazione); il
perimetro dei dati resta a **6 righe**.

## 13 ottobre 2026

> Copre il periodo **1 – 13 ottobre**, fotografato al 13-10 alle 23:59. Tredici
> giorni, **676 changeSet** datati fra l'1 e il 13 (283 in `vendite`, 177 in
> `script`, 78 in `anagrafiche`, 36 in `dbops`, 25 in `config`, 22 in
> `catalogo`, 21 in `80_data`), **sessantacinque documenti entrati in
> `work-done`** e **114 PR** (dalla #1738 alla #1857). *(Corretto il 27-10: la
> prima stesura contava 662 changeSet perché fotografava il commit `2bda3ee3b`
> del ramo BE, che non conteneva i 14 changeSet del 13-10 entrati dal ramo DB
> con le PR #1856 e #1857 — `20261013-59 → -72`, articoli ammessi per documento
> e legami della lineage — pur contando quelle PR.)* Si scrive per **temi**:
> sono nove. Le due voci brevi del 1° e del 4 ottobre, qui sotto, restano: sono
> il dettaglio di due temi (il registro di magazzino, le righe come liste).
>
> ⚠️ Fuori da questa voce, perché nati il **14 ottobre**: la chiusura di
> `brief-db-dati-fiscali-e-societari-del-soggetto.md` e il brief che ne eredita la
> creazione (`brief-db-dati-societari-in-creazione.md`).
>
> ⭐ **Il tema portante è *la regola sta nel DB, e il DB la applica anche
> all'indietro*.** A settembre la sede di un permesso era diventata il verbo che
> scrive; in ottobre la stessa mossa tocca i **documenti**. Che cosa si cambia
> dopo l'emissione, quali righe di una bolla sono ferme, che cosa succede
> annullando un documento che ha legami: ogni regola che stava in un «solo in
> DRAFT» Python o in una frase di un brief scende in un guard o in un verbo. E
> dove prima si bloccava soltanto, ora si **torna indietro con la
> segnalazione**: *«quando si torna indietro ci devono essere le segnalazioni di
> quello che si sta facendo; in avanti le abbiamo bloccate. Un unico
> meccanismo»* (Tid).

**Anello 3 (`vendite`) — Tornare indietro: il documento dopo l'emissione, e
l'annullo che riapre a monte.** Quattro brief in fila, lo stesso oggetto. La
**testata dopo l'emissione** (D26, 11-10): la regola «fuori bozza, che cosa si
cambia» passa dal BE al DB per **famiglie di colonne** (identità bloccata, ciò
che arriva dopo e le note modificabili, stampato e condizioni decise per
documento), con un BB per testate e righe e un lettore del montaggio; il BE
toglie i suoi «solo in DRAFT» — *la logica sta nel DB, il backend non la
ripete*. Le **righe evase di una bolla** (D28, 11-10) sono ferme su articolo,
UdM e quantità: *`qta_evasa` è append-only* era scritto solo in un brief, ora è
un'invariante, e la quantità si corregge col suo verbo, in bozza ed entro il
residuo. L'**annullo con legami** (D29, 11-10): un lettore unico dei legami, un
avviso comune con conferma (`E_DOC_ANNULLO_CON_LEGAMI`) e i verbi
`fn_annulla_<documento>` — *se il documento a valle si annulla, quella cosa
torna disponibile a monte, e non in silenzio*. Infine **annullare la commessa
riapre il documento** (D30, 13-10): il preventivo torna ACCETTATO, l'ordine
torna da mandare, lo stato «evaso» dell'ordine lo decidono le bolle, una riga
ritirata non occupa più il segmento, e nei Passaggi compare il **legame
ritirato** — `ROOT` è il ruolo del documento *dentro ciascuna commessa*. Nella
stessa famiglia: la **data confermata di una riga già spedita non si cambia**
(D-7, con il concetto «spedito» riunito da quattro sedi in un BB) e le date di
consegna si scrivono **in blocco** sulle righe, mai in testata — *la riga
decide, sempre*. ⚠️ Aperto: la commessa vuota lasciata dal push batch
(PROJECT_CONTEXT § «Aperto»). Vedi
[brief-db-testata-dopo-emissione.md](work-done/brief-db-testata-dopo-emissione.md),
[brief-db-ordine-data-consegna-confermata-capability.md](work-done/brief-db-ordine-data-consegna-confermata-capability.md),
[brief-db-ddt-righe-evase-dall-ordine.md](work-done/brief-db-ddt-righe-evase-dall-ordine.md),
[brief-db-annullo-documento-con-legami.md](work-done/brief-db-annullo-documento-con-legami.md),
[brief-db-annullo-a-valle-riapre-a-monte.md](work-done/brief-db-annullo-a-valle-riapre-a-monte.md),
[brief-db-date-consegna-righe-in-blocco.md](work-done/brief-db-date-consegna-righe-in-blocco.md).

**Anello 3 (`vendite`) — Le righe e i componenti: tutte le famiglie con le
stesse regole.** Contratto e offerta avevano le regole delle righe; preventivo,
ordine e DDT no. D19 (08-10) le porta su tutte: componenti «solo in bozza», la
revisione del preventivo che porta anche i componenti spenti — *il componente
spento si porta, spento* —; D20 (09-10) chiude le righe di preventivo e
d'ordine fuori bozza su INSERT, UPDATE e DELETE. L'**esclusione** diventa ciò
che dice il nome: *un'ESCLUSIONE dice solo che il documento non vende
quell'articolo del listino* — colonne di fatturazione vuote per CHECK, non si
modifica, un guard comune per contratto e offerta, e il lister non la propone
più alla fatturazione; *una riga che si fattura dice come si eroga*
(`tipo_erogazione` obbligatoria, via il ripiego silenzioso su `CANONE`). La
riga di listino **propagata** ora lo è davvero: il guard c'era, *mancava chi
scrive il legame* — push ed emissione scrivono `listino_riga_id`, e la copia
Python del controllo si ritira con il suo codice. Le **esclusioni implicite**
(D17, 04-10): una fattura numerata non si cancella e non cambia numero, utente
NULL vuol dire nessun accesso, un presidio sull'invariante del `FORCE` — *sono
giusti oggi, e quando smettono di esserlo non danno errore*. ⚠️ Aperti: la
coerenza listino/versione/emittente della riga di commessa, la provenienza del
prezzo, le righe periodiche del contratto in commessa (D31), il documento che
nasce fuori bozza (D32). Vedi
[brief-db-righe-e-componenti-le-altre-famiglie.md](work-done/brief-db-righe-e-componenti-le-altre-famiglie.md),
[brief-db-righe-e-componenti-debiti-residui.md](work-done/brief-db-righe-e-componenti-debiti-residui.md),
[brief-db-righe-esclusione-solo-non-si-vende.md](work-done/brief-db-righe-esclusione-solo-non-si-vende.md),
[brief-db-contratto-esclusione-non-modificabile.md](work-done/brief-db-contratto-esclusione-non-modificabile.md),
[brief-db-erogazione-obbligatoria-righe-fatturate.md](work-done/brief-db-erogazione-obbligatoria-righe-fatturate.md),
[brief-db-riga-listino-propagata-dalla-commessa.md](work-done/brief-db-riga-listino-propagata-dalla-commessa.md),
[brief-db-ritiro-codice-riga-gia-propagata.md](work-done/brief-db-ritiro-codice-riga-gia-propagata.md),
[brief-db-esclusioni-implicite.md](work-done/brief-db-esclusioni-implicite.md).

**Anello 3 (`vendite`) — L'azienda che emette è quella del cliente.** Ordine,
DDT e reso hanno ora il cliente come preventivo, offerta e contratto (D21,
10-10): il billing account è obbligatorio sull'ordine, sul DDT segue la
causale, sul reso è quello della bolla, con FK composte; un esecutivo derivato
ha il BA della sua sorgente — *vendite = acquisti, e le asimmetrie si chiudono
subito*. Le **sette copie** del guard «emittente del cliente» diventano un BB
parametrico e un codice solo, commessa compresa (D22). E l'**istanza nasce col
billing account** (08/10-10): *la regola giusta è che nascono insieme e deve
essere sempre così* — un'istanza un emittente, un BA un cliente, il preventivo
col BA NOT NULL; i residui (D25) tolgono il resolver per istanza e i filtri che
il contratto rendeva tautologici — *il motivo per cui si tolgono è il
contratto, non il fatto che oggi nessun preventivo sia senza BA*. ⚠️ Aperti:
gli indirizzi del documento che non seguono il cambio di cliente (D27, lato DB
fatto, collaudo e BE/FE), la catena delle istanze su un PDP (D18), un cliente
manuale per soggetto e utility (D33). Vedi
[brief-db-esecutivi-ba-coppia.md](work-done/brief-db-esecutivi-ba-coppia.md),
[brief-db-guard-emittente-ba-unico.md](work-done/brief-db-guard-emittente-ba-unico.md),
[brief-db-istanza-nasce-col-ba.md](work-done/brief-db-istanza-nasce-col-ba.md),
[brief-db-istanza-nasce-col-ba-residui.md](work-done/brief-db-istanza-nasce-col-ba-residui.md).

### Fattura e anagrafiche — 13 ottobre

**Anello 2/3 (`documenti`, fattura) — Il patto fra template e forma regge
quattro versioni in tre giorni.** Il patto di fine settembre (la versione di
template dichiara la forma che legge) viene messo alla prova subito: la fattura
passa dalla forma 2 alla 4 e il template dalla v4 alla **v7** (01→03-10),
ciascuna pubblicata dall'app. Dentro: i **componenti del kit** in fattura in tre
modi (`NASCOSTO`, `DESCRITTIVO`, `VALORIZZATO`) — *il terzo modo non chiede dati
nuovi, chiede di leggere quelli che ci sono* —; l'**esigibilità IVA per cassa
dell'emittente** (RF17 → `D`), con le annotazioni stampate sotto i totali — *il
sistema scriveva I e non lo sapeva*; i flag della distinta che nessuno leggeva
ritirati, e il **plafond che si consuma sul netto** della fattura (una fattura
che ha consumato plafond non si disfa più). I formati di pagina diventano
vocabolari con FK — *un CHECK non si legge da una tendina* — e il render PDF
apre le risorse esterne solo da una **lista chiusa** di asset dell'emittente.
⚠️ Aperti: i riepiloghi IVA dei preventivi, la storicità del regime fiscale,
le domande per il consulente (PROJECT_CONTEXT § «Aperto»). Vedi
[brief-db-esposizione-componenti-kit-in-fattura.md](work-done/brief-db-esposizione-componenti-kit-in-fattura.md),
[brief-db-esigibilita-iva-per-cassa-emittente.md](work-done/brief-db-esigibilita-iva-per-cassa-emittente.md),
[brief-db-bom-flag-quantita-e-kit-in-fattura.md](work-done/brief-db-bom-flag-quantita-e-kit-in-fattura.md),
[brief-db-vocabolari-versione-template.md](work-done/brief-db-vocabolari-versione-template.md),
[brief-be-documenti-risorse-esterne-render-pdf.md](work-done/brief-be-documenti-risorse-esterne-render-pdf.md),
[brief-db-documenti-versione-contesto-template.md](work-done/brief-db-documenti-versione-contesto-template.md).

**Anello 1 (`anagrafiche`) — Il soggetto: ciò che non si inventa e ciò che
dipende dalla natura.** *Il sesso di una persona fisica non si inventa* (10-10):
via il `DEFAULT 'M'` e i `COALESCE`, una `sesso_policy` per natura, e la ditta
individuale nasce finalmente DI, con la sua partita IVA. Le colonne
`character(n)` a lunghezza variabile diventano `varchar` (12 colonne, 16 viste
senza `TRIM`) — *i tamponi a valle non chiudono il difetto* —, e il canale FE
pretende il suo recapito. Da quel giro nasce il cantiere dei **dati fiscali e
societari** (10/11-10): PA e split payment ammessi per natura, un verbo unico
per i dati societari, la forma giuridica legata alla natura, i titoli IVA solo
dove la natura li ammette; lato DB e BE/FE verdi e collaudati l'11-10, al 13-10
ancora in `work-in-progress` con D-4 (`COOPERATIVA`) aperta, archiviato il 14-10. Vedi
[brief-db-sesso-senza-default.md](work-done/brief-db-sesso-senza-default.md),
[brief-db-character-n-spazi-di-riempimento.md](work-done/brief-db-character-n-spazi-di-riempimento.md),
[brief-db-dati-fiscali-e-societari-del-soggetto.md](work-done/brief-db-dati-fiscali-e-societari-del-soggetto.md).

### Permessi e accessi — 13 ottobre

**Anello 0/1 — Permessi: il livello dell'area è un tetto.** La semantica si
ribalta (04→06-10): prima vinceva il livello più specifico, ora *un permesso
specifico può solo restringere quello della sua area, mai allargarlo* — il
tetto entra nei tre resolver, gli override che lo superano restano scritti e
dormienti. L'analisi lo aveva trovato così: *chi disegnasse la cascata solo a
video costruirebbe una schermata che dice «bloccato» mentre l'API risponde
200*. Il pannello diventa master-detail per area e salva solo le sezioni
toccate; la matrice operatori × aree sparisce e i permessi si leggono nella
lista Operatori con «Mostra permessi» — *una seconda lista sugli stessi
operatori sarebbe una copia destinata a divergere*. Ogni scrittura del catalogo
dei permessi **avvisa il backend al commit** (NOTIFY per statement, la cache si
svuota da qualunque scrittore). Il brief del permesso nel verbo è archiviato il
03-10: il modello vive nella guida, il passo 3 resta senza data. Collaudi a
video dei permessi ereditati e della UI verdi il 06-10. Vedi
[brief-db-permessi-tetto-area.md](work-done/brief-db-permessi-tetto-area.md),
[analisi-ui-permessi-operatore.md](work-done/analisi-ui-permessi-operatore.md),
[piano-be-fe-ui-permessi-operatore.md](work-done/piano-be-fe-ui-permessi-operatore.md),
[brief-db-riepilogo-permessi-lista-operatori.md](work-done/brief-db-riepilogo-permessi-lista-operatori.md),
[brief-db-permessi-catalogo-notify-cache.md](work-done/brief-db-permessi-catalogo-notify-cache.md),
[brief-db-permesso-nel-verbo-di-scrittura.md](work-done/brief-db-permesso-nel-verbo-di-scrittura.md).

**Anello 0/1 — Accessi: il secondo fattore chiuso, una veste utilizzabile in
una sede.** Il **TOTP** chiude il 02-10 con BE/FE e collaudo (cancello degli
obblighi, login a due passi, pagina «Sicurezza»): registrare il device chiede
la password, che conta nel freno — *la sessione da sola non lo accende per
conto di un altro* —, e la chiave si ruota con un verbo «confronta e
sostituisci» su una tabella chiusa all'app. «Operatori» diventa l'area
**Accessi**, tre tab che sono una partizione; i verbi dell'amministratore
rifiutano le credenziali di sistema e l'ultimo SUPER_ADMIN (*si rifiuta ciò che
ferma il processo, non ciò che rimedia*); una credenziale senza vesti si può
**eliminare**, e il suo presidio finalmente si spegne. *Accesa e dentro le
date* diventa un BB solo (`fn_veste_utilizzabile`), letto nei cinque punti del
BE — *un frammento Python sarebbe stato la quinta copia*. Portale e shop
entrano con l'email (L-4). La metà OAuth dell'analisi 2FA esce in un piano suo.
⚠️ Aperti: L-5 (revoca della veste, manca il brief DB), il collaudo di D-5,
i provider esterni. Vedi
[autenticazione-due-fattori-e-provider.md](work-done/autenticazione-due-fattori-e-provider.md),
[brief-be-fe-sicurezza-header-token-mfa.md](work-done/brief-be-fe-sicurezza-header-token-mfa.md),
[brief-db-secondo-fattore-totp.md](work-done/brief-db-secondo-fattore-totp.md),
[brief-db-secondo-fattore-riautenticazione-password.md](work-done/brief-db-secondo-fattore-riautenticazione-password.md),
[brief-db-totp-ricifra-segreto.md](work-done/brief-db-totp-ricifra-segreto.md),
[brief-db-codici-cancello-obblighi-e-sfida-totp.md](work-done/brief-db-codici-cancello-obblighi-e-sfida-totp.md),
[brief-db-be-fe-area-accessi.md](work-done/brief-db-be-fe-area-accessi.md),
[brief-db-credenziale-verbi-amministratore.md](work-done/brief-db-credenziale-verbi-amministratore.md),
[brief-db-elimina-credenziale-senza-veste.md](work-done/brief-db-elimina-credenziale-senza-veste.md),
[brief-db-veste-utilizzabile.md](work-done/brief-db-veste-utilizzabile.md),
[brief-db-codici-non-trovato-email-e-permessi.md](work-done/brief-db-codici-non-trovato-email-e-permessi.md),
[collaudo-in-app-consenso-riuso-credenziale.md](work-done/collaudo-in-app-consenso-riuso-credenziale.md),
[piano-be-fe-accessi-credenziale-e-vesti.md](work-in-progress/piano-be-fe-accessi-credenziale-e-vesti.md),
[piano-autenticazione-provider-esterni-oauth.md](work-in-progress/piano-autenticazione-provider-esterni-oauth.md).

### Nucleo, interfaccia e magazzino — 13 ottobre

**Anello 0 — Un solo fuso, valori finiti, una corsa saltata non è una
corsa.** Il **fuso dell'azienda** è un dato solo con una sede sola (09-10):
`CURRENT_DATE` sparisce da 61 funzioni, 6 viste e 25 default, lo `storico`
passa a `timestamptz`, il BE ha un middleware e un `oggi_aziendale()`, il FE una
sede delle date, e pgTAP e vitest girano in un fuso **ostile** — *il fuso di
chi esegue diventa irrilevante; se cambiarlo cambia un risultato, quello è un
difetto*. **170 CHECK** rifiutano `NaN` e infiniti su ogni colonna `numeric`
(09-10). Una corsa **saltata** ha una colonna sua e non conta più come riuscita
— *un filtro sul testo è la seconda sede della stessa regola*. I presidi
parlano a **chi deve agire** (amministratore, sistemista, sviluppo), con un
testo per causa. La lineage si calcola **per seme** e non più per tutto il
sistema (*chi chiede un documento pagava tutti i documenti*), dopo un primo giro
che aveva portato le sette liste da secondi a 0,18 s; le funzioni che
ripianificano a ogni chiamata hanno un brief (D26-2, resta D-3b). I test RLS dei
documenti **costruiscono** il proprio documento (copertura in CI da zero a
reale), sei codici sfilati entrano a catalogo, la ricerca universale non taglia
più a 10.000 righe senza ordine, e il **type checker** del BE va a regime
(registro mypy 620 → 0; in L0 un 500 vecchio di sei mesi). Vedi
[brief-be-db-fe-un-solo-fuso-aziendale.md](work-done/brief-be-db-fe-un-solo-fuso-aziendale.md),
[brief-db-valore-numerico-non-finito-nei-documenti.md](work-done/brief-db-valore-numerico-non-finito-nei-documenti.md),
[brief-db-corsa-saltata-non-e-una-corsa.md](work-done/brief-db-corsa-saltata-non-e-una-corsa.md),
[brief-db-presidi-cosa-significa-cosa-fare.md](work-done/brief-db-presidi-cosa-significa-cosa-fare.md),
[brief-db-presidio-processi-testo-per-causa.md](work-done/brief-db-presidio-processi-testo-per-causa.md),
[brief-db-liste-documento-lineage-lenta.md](work-done/brief-db-liste-documento-lineage-lenta.md),
[brief-db-lineage-seminata-per-chiave.md](work-done/brief-db-lineage-seminata-per-chiave.md),
[brief-db-segment-base-commesse-attivita.md](work-done/brief-db-segment-base-commesse-attivita.md),
[brief-db-plancache-funzioni-con-query-incorporate.md](work-done/brief-db-plancache-funzioni-con-query-incorporate.md),
[brief-db-fixture-rls-documenti-costruiti.md](work-done/brief-db-fixture-rls-documenti-costruiti.md),
[brief-db-codici-sfilati-e-lista-parametri.md](work-done/brief-db-codici-sfilati-e-lista-parametri.md),
[brief-db-ricerca-universale-tetto-10000.md](work-done/brief-db-ricerca-universale-tetto-10000.md),
[brief-db-parametro-data-minima-ritardo-dashboard.md](work-done/brief-db-parametro-data-minima-ritardo-dashboard.md),
[piano-be-type-checker.md](work-done/piano-be-type-checker.md).

**Anello 1 / frontend e Anello 3 (`magazzino`) — Una sede per il drawer, la
merce che esce a video.** Gli **80 drawer** laterali passano da una sede sola
(`AppDrawer`, 03-10): drawer grezzi da 80 a 0, il lint vieta l'import diretto, e
tre drawer che perdevano lavoro in uscita sono corretti. Nessuna icona è più
scritta a mano fuori dalle costanti — *il nome della costante dice il
significato, non il disegno*. I collaudi a video dell'osservabilità e della
casella di ricerca chiudono il 06-10 — *di questo cantiere era provato il
percorso, mai l'esito*. In `magazzino` il registro è un servizio dell'anello 2
(voce del 1° ottobre), e il **BE/FE dei Lotti 3 e 3-bis** è scritto il 12/13-10:
la bolla e il reso muovono la merce dall'interfaccia, con prelievi, rientri e un
BB della sezione merce del documento. ⚠️ Aperti: il collaudo a video dei
blocchi A/B/C e dell'inventario, i motivi della conferma del reso senza valori
(brief DB nuovo), la CI da zero. Vedi
[analisi-fe-chrome-drawer.md](work-done/analisi-fe-chrome-drawer.md),
[censimento-icone-per-significato.md](work-done/censimento-icone-per-significato.md),
[collaudo-in-app-osservabilita-giornale-errori-pallino.md](work-done/collaudo-in-app-osservabilita-giornale-errori-pallino.md),
[collaudo-in-app-casella-ricerca-liste.md](work-done/collaudo-in-app-casella-ricerca-liste.md),
[piano-be-fe-magazzino-lotto-3.md](work-in-progress/piano-be-fe-magazzino-lotto-3.md),
[brief-db-reso-motivi-conferma-con-valori.md](work-done/brief-db-reso-motivi-conferma-con-valori.md).

**In breve, senza un tema proprio** — la valutazione DB prende una parte
qualitativa sul **design** (§2-bis, 04-10), da cui nascono le voci da D17 a
D33: undici chiuse nel periodo (D17, D19…D23, D25, D26, D28…D30), più un giro di D7; nelle migliorie BE/FE chiudono `npm audit` e
`check --deploy` completo in CI e le letture con lo skip, e l'analisi «doc API
contro codice» di `core` ha chiuso tutte le voci (resta da archiviare). pgTAP:
**7 rossi** nel registro di dev, contro i 12 di fine settembre; il registro
della CI è fermo a **361** dal 22-09, quindi il divario resta il debito vero.
`DataTable` grezze da 31 a **28** (9 senza motivazione).

---

## 4 ottobre 2026

**Righe di documento come liste: cantiere chiuso.** Le righe di preventivo,
ordine, DDT, reso, fattura e contratto e la distinta base sono liste
configurabili (97-103): finisce lo scroll orizzontale su tablet e smartphone.
L'ultimo lotto è il contratto: una sorgente sola per le due forme (la funzione
delle righe operative, con chiave di riga e verbi ammessi dal DB), l'unità di
misura della riga corretta a DB, l'anteprima intera ritirata. Nella stessa
chiusura la lettura delle righe sale in un building block di core (lo usa
anche la distinta del catalogo), «leggi prima la testata» diventa un BB con un
test per consumatore, e i default di pagina delle firme backend tornano alla
fonte unica (liste di eventi comprese, con la loro costante) —
[brief-db-liste-righe-documento](work-done/brief-db-liste-righe-documento.md).

## 1 ottobre 2026

**Il registro di magazzino è un servizio dell'anello 2** (decisione di Tid). Con i Lotti 3 e 3-bis
la bolla e il reso di `vendite` scaricano e ricaricano la merce: la mappa lo aveva registrato come
*dipendenza laterale fra processi di anello 3* e lo aveva messo fra le decisioni aperte. Letto sul
codice, la dipendenza era in **due** versi: `vendite` usa il registro, e il registro conosceva
`vendite` (i posting `magazzino.fn_posta_ddt` e `fn_posta_reso` leggono le tabelle della bolla e
del reso). Deciso: lo schema `magazzino` contiene il **registro** (anello 2, come `documenti` e
`pratiche`: predisposto finché `acquisti` non diventa il secondo dominio consumatore) e i
**documenti di magazzino** (anello 3); la regola «mai dipendenze laterali» resta intera. Il verso
inverso è un debito: i posting tornano in `vendite`, e un presidio lo tiene a zero —
[brief-db-magazzino-registro-anello-interno](work-done/brief-db-magazzino-registro-anello-interno.md).

Lo stesso giorno il lavoro è **scritto** (`20261001-18 → -26`, da applicare): i posting in
`vendite`, il cancello `dbops.vw_magazzino_dipendenze_inverse` in CI — e il cancello, al primo
giro, ha trovato un **secondo** verso inverso che il brief dava per assente: la FK
`magazzino.assets.contratto_id` → `vendite.contratti`, mai letta né scritta. Tolta nello stesso
giro (Tid: *se servirà, il legame nasce nel contratto*). ⭐ *Una regola scritta e non letta da
nessun controllo aveva già due eccezioni silenziose.*

---

## settembre 2026

> **Riepilogo del mese** (le voci datate **10**, **14**, **19** e **30 settembre** sono state
> compattate qui il 2026-11-01). Il dettaglio non è andato perso: vive nei brief linkati, tutti in
> `work-done`. ⚠️ **Cinque paragrafi e i quattro «In breve» restano per intero**, in fondo alla voce:
> i primi citano un documento ancora in `work-in-progress` (la valutazione dello strato DB, il piano
> degli accessi, il collaudo degli incassi, il piano PrimeVue), i secondi non hanno un brief a cui
> delegare.
>
> Il mese copre **31 agosto → 30 settembre**: **996 changeSet** (384 dal 31-08 al 10-09, 103
> dall'11 al 14, 109 dal 15 al 19, 400 dal 20 al 30) e **116 documenti chiusi in `work-done`**. ⚠️
> Il **1° ottobre** è fuori: i brief nati quel giorno (esigibilità IVA per cassa, esposizione dei
> componenti del kit in fattura, ricifratura del segreto TOTP) e il cancello degli obblighi, che al
> 30-09 era consegnato a file e da applicare, stanno nelle voci di ottobre.
>
> ⭐ **I temi portanti, uno per voce.** *La catena di verifica* (10-09): la CI che misura davvero,
> i presidi con un catalogo, il perimetro con un criterio, i motivi da un posto solo. *I presidi
> allo specchio* (14-09): tre presidi hanno mentito, e la causa stava nel metro — *un presidio si
> prova dal percorso che lo attraversa*. *Il collaudo in-app che scrive le regole* (19-09): il
> copione degli incassi diventa tre giri e venti decisioni. *Una regola, una sede* (30-09): e la
> sede di un permesso è il verbo che scrive — *il DB calcolava i permessi ma non li applicava*.

### Verifica, presidi e processi automatici

**Anello 0 — I presidi hanno un catalogo, e un contatore che non mente.** Nasce `dbops.presidi`:
un presidio che non ha mai girato non conta come copertura, e *un cancello non deve poter zittire
un altro cancello*. Vedi
[brief-db-un-destinatario-per-i-presidi.md](work-done/brief-db-un-destinatario-per-i-presidi.md).

**Anello 0 — Presidi e fixture: il mondo si costruisce, i presidi del percorso storto esistono.**
C1 (un valore ammesso dal CHECK e mai scritto) e C2 (la `ui_action` a catalogo e il canale che la
realizza) si chiudono; il giro 2 delle fixture porta il BB di composizione del mondo cliente e
nessun file della suite fa più `COMMIT`. D7 chiude il perimetro con fixture che costruiscono i
soggetti, e i rientrati li toglie uno script dal log della corsa. Le analisi dei presidi del
percorso storto e della diagnostica di produzione si chiudono **senza aprire cantieri**. Vedi
[brief-db-presidio-stati-mai-scritti.md](work-done/brief-db-presidio-stati-mai-scritti.md),
[brief-be-presidio-ui-action-e-canale-campi.md](work-done/brief-be-presidio-ui-action-e-canale-campi.md),
[brief-db-fixture-che-costruiscono-giro-2.md](work-done/brief-db-fixture-che-costruiscono-giro-2.md),
[brief-db-fixture-che-costruiscono-d7-d6-d4.md](work-done/brief-db-fixture-che-costruiscono-d7-d6-d4.md),
[analisi-presidi-percorso-storto.md](work-done/analisi-presidi-percorso-storto.md),
[analisi-diagnostica-produzione-senza-accesso-db.md](work-done/analisi-diagnostica-produzione-senza-accesso-db.md).

**Anello 0 — Ciò che la CI non vedeva: trigger generati e giro notturno.** Un dato che viaggia
negli argomenti del trigger non si trova cercando nei corpi: il codice ritirato sollevato da 69
trigger, i lock scritti a mano cancellati dal job, lo storico che cercava la colonna FK sbagliata.
Il registro diventa l'unica sede di un lock, i **job notturni girano in CI** in ordine dichiarato,
e la regola «`valido_al` non precede `valido_dal`» ha una sede sola. Vedi
[brief-db-codici-ritirati-negli-argomenti-dei-trigger.md](work-done/brief-db-codici-ritirati-negli-argomenti-dei-trigger.md),
[brief-db-lock-di-colonna-fuori-registro.md](work-done/brief-db-lock-di-colonna-fuori-registro.md),
[brief-db-storico-colonna-fk-dei-trigger.md](work-done/brief-db-storico-colonna-fk-dei-trigger.md),
[brief-db-job-notturni-in-ci.md](work-done/brief-db-job-notturni-in-ci.md),
[brief-db-guard-date-validita.md](work-done/brief-db-guard-date-validita.md).

**Anello 0 — I processi automatici: un'identità, un contratto di vitalità, «Esegui ora».** Ogni
processo del backend ha un artefatto di deploy e un'identità, quindi un perimetro. La tolleranza
diventa un dato di catalogo, il panorama dice `MUTO` e `MAI_PARTITO`, il listener si presidia
dalla sessione, un guardiano accoda la notifica se il digest tace, e una mail stampata a video è
`SIMULATA`, non inviata. «Esegui ora» entra in esercizio con tre celle di CSV; «Riavvia» resta
dietro D1, perché senza un *host* nel modello riavvierebbe una macchina a caso. Vedi
[brief-db-processi-automatici-identita-e-perimetro.md](work-done/brief-db-processi-automatici-identita-e-perimetro.md),
[brief-db-sveglia-dei-processi.md](work-done/brief-db-sveglia-dei-processi.md),
[brief-db-processi-automatici-residui-be.md](work-done/brief-db-processi-automatici-residui-be.md),
[piano-be-fe-processi-automatici-identita-e-perimetro.md](work-done/piano-be-fe-processi-automatici-identita-e-perimetro.md),
[brief-db-quattro-processi-senza-presidio.md](work-done/brief-db-quattro-processi-senza-presidio.md),
[brief-db-stato-email-console-non-e-inviata.md](work-done/brief-db-stato-email-console-non-e-inviata.md),
[brief-db-avvio-manuale-di-un-processo.md](work-done/brief-db-avvio-manuale-di-un-processo.md),
[piano-be-fe-avvio-manuale-di-un-processo.md](work-done/piano-be-fe-avvio-manuale-di-un-processo.md),
[analisi-riavvio-processi-da-interfaccia.md](work-done/analisi-riavvio-processi-da-interfaccia.md).

**Anello 0 — Osservabilità: l'ultimo miglio, e il pallino in topbar.** Errori tecnici dietro
permesso, Giornale eventi, retention e pallino dei presidi; il verdetto «lotto fermo» nasce a DB
invece di vivere in Python. ⚠️ Restava aperto il `USAGE` di `zeroerp_log` su `dbops` in CI
(PROJECT_CONTEXT). Vedi
[analisi-osservabilita-log.md](work-done/analisi-osservabilita-log.md),
[piano-be-fe-osservabilita-pallino-e-superfici.md](work-done/piano-be-fe-osservabilita-pallino-e-superfici.md),
[brief-db-osservabilita-lotto-fermo-r6-indici.md](work-done/brief-db-osservabilita-lotto-fermo-r6-indici.md),
[brief-db-privilegio-app-job-run-log.md](work-done/brief-db-privilegio-app-job-run-log.md).

### Perimetro, permessi e sicurezza

**Anello 0 + 3 — Il perimetro dei dati smette di fermarsi alla testata, e arriva allo storico.**
L'elenco a mano diventa un **criterio transitivo** (ogni tabella con una FK verso una protetta),
nove famiglie armate, il debito da 33 a 8 righe. Lo storico porta il proprio perimetro: lo scope
**si cattura, non si deriva**, 37 shadow armate, e `dbops.audit_log` ha un cancello alla scrittura.
D13: un BA non ancora collegato appartiene a chi lo sta creando. Vedi
[brief-db-perimetro-emittente-righe-documento.md](work-done/brief-db-perimetro-emittente-righe-documento.md),
[brief-db-viste-security-invoker-criterio.md](work-done/brief-db-viste-security-invoker-criterio.md),
[brief-db-rls-storico-scope-congelato.md](work-done/brief-db-rls-storico-scope-congelato.md),
[brief-db-ba-riserva-emittente-operatore-d13.md](work-done/brief-db-ba-riserva-emittente-operatore-d13.md).

**Anello 0 — Il DB applica i permessi, non solo li calcola.** Il modello *una scrittura = un
verbo*: il verbo dichiara il permesso nella prima riga (`fn_guard_azione`, `fn_guard_livello`,
`fn_guard_super_admin`) e l'app perde la scrittura diretta. Primo caso il magazzino, secondo il
pannello config, dove è emerso chi si alzava i privilegi da Configurazione; ogni `GET` gira in sola
lettura; la sync dell'owner si difende nel corpo. ⚠️ Restava aperto il passo 3, i domini
esistenti. Vedi
[brief-db-permesso-nel-verbo-di-scrittura.md](work-done/brief-db-permesso-nel-verbo-di-scrittura.md),
[brief-db-magazzino-verbi-con-permesso.md](work-done/brief-db-magazzino-verbi-con-permesso.md),
[brief-db-pannello-config-verbo-generico.md](work-done/brief-db-pannello-config-verbo-generico.md),
[brief-be-letture-in-transazione-sola-lettura.md](work-done/brief-be-letture-in-transazione-sola-lettura.md),
[brief-db-registro-owner-e-sync-riservati-al-migratore.md](work-done/brief-db-registro-owner-e-sync-riservati-al-migratore.md).

**Anello 0/1 — Le porte dicono la stessa cosa.** Il catalogo degli oggetti personalizzabili
coincide con le quattro porte (BE, FE, verbo DB, catalogo) e la regola sta in una FK; l'ereditato
del pannello permessi si calcola a DB, dove lo spareggio era in cinque posti; la capability è
annidata, non fusa nel dettaglio. Vedi
[brief-db-be-fe-catalogo-oggetti-permessi.md](work-done/brief-db-be-fe-catalogo-oggetti-permessi.md),
[brief-db-pgtap-permessi-ereditati.md](work-done/brief-db-pgtap-permessi-ereditati.md),
[brief-be-fe-capability-annidata.md](work-done/brief-be-fe-capability-annidata.md),
[brief-db-messaggio-ba-senza-emittente.md](work-done/brief-db-messaggio-ba-senza-emittente.md).

**Trasversale — Sicurezza in profondità, dalla superficie al secondo fattore.** Superficie
pubblica ridotta (gunicorn su loopback, admin Django tolto), segreti fuori da git con gitleaks in
pre-commit e in CI, refresh token nel cookie `HttpOnly` e chiave di cifratura separata dalla
`SECRET_KEY`; il **TOTP** lato DB, con l'obbligo sulla credenziale o sul profilo e l'anti-replay
sul passo. Vedi
[brief-be-fe-sicurezza-header-token-mfa.md](work-done/brief-be-fe-sicurezza-header-token-mfa.md),
[brief-db-secondo-fattore-totp.md](work-done/brief-db-secondo-fattore-totp.md),
[configurazione-django.md](backend/configurazione-django.md).

**Anello 0 + 1 — Il software che serviva dati morti.** Otto voci ritirate — viste coi nomi vecchi,
shadow legacy, tabelle di backup, alias deprecati —, e *«tenere per sicurezza» è la forma da cui
ogni voce era nata*. Dietro, in CI, un GRANT su `django.auth_user` dato a mano su dev: *un
privilegio che esiste su una macchina è un ricordo*. Vedi
[analisi-software-per-dati-morti.md](work-done/analisi-software-per-dati-morti.md).

**Anello 0 — Quando nasce un building block, le copie si ritirano nello stesso giro.**
L'emittente di default è una funzione sola su undici tabelle, le quattro copie di `vendite`
ritirate: *non c'è produzione, non c'è niente da aspettare*. Vedi
[brief-db-emittente-di-default-un-bb-solo.md](work-done/brief-db-emittente-di-default-un-bb-solo.md).

**Anello 0 — Il primo motivo di un controllo esce da un posto solo.**
`script.fn_raise_primo_motivo_se_presente` al posto di tredici copie della stessa coda. Vedi
[brief-db-coda-primo-motivo-in-un-posto-solo.md](work-done/brief-db-coda-primo-motivo-in-un-posto-solo.md),
[brief-db-i-motivi-si-fermano-dentro-la-check.md](work-done/brief-db-i-motivi-si-fermano-dentro-la-check.md).

### Liste e interfaccia

**Anello 1 (`ui`) — Il perimetro emittente arriva ai cataloghi globali.** Sei liste dichiarate
`perimetro_emittente = false`; il valore sta nella colonna del CSV della lista, non in un seed
laterale, che si ritira. Vedi
[brief-db-perimetro-emittente-cataloghi-globali.md](work-done/brief-db-perimetro-emittente-cataloghi-globali.md).

**Anello 1 (`ui`) — La lista dice da sé che cosa è.** La ricerca libera legge il catalogo, la
soglia è una colonna, le misure di pagina hanno un catalogo, le azioni portano un significato e il
FE ne ricava icona e colore. Vedi
[brief-be-ricerca-full-liste-residue.md](work-done/brief-be-ricerca-full-liste-residue.md),
[brief-db-ricerca-full-colonne-permessi.md](work-done/brief-db-ricerca-full-colonne-permessi.md),
[brief-db-ricerca-full-colonne-da-accendere.md](work-done/brief-db-ricerca-full-colonne-da-accendere.md),
[brief-db-be-fe-ricerca-soglia-per-lista.md](work-done/brief-db-be-fe-ricerca-soglia-per-lista.md),
[brief-db-misure-pagina-catalogo.md](work-done/brief-db-misure-pagina-catalogo.md),
[brief-db-icone-azioni-per-significato.md](work-done/brief-db-icone-azioni-per-significato.md),
[brief-db-lista-articoli-colonne-data.md](work-done/brief-db-lista-articoli-colonne-data.md).

**Anello 1 / frontend — Una sola macchina per ogni gesto.** Le `DataTable` grezze riclassificate
(eccezioni vere contro liste a catalogo 83-96, tre troncavano in silenzio), le righe di documento
come liste (97-103) col BB `useFormInline`, i filtri compatti in un drawer su tutte le view, il
verso delle dipendenze fra domini, OpenAPI a zero rilievi. Vedi
[brief-db-liste-datatable-grezze.md](work-done/brief-db-liste-datatable-grezze.md),
[brief-db-liste-righe-documento.md](work-done/brief-db-liste-righe-documento.md),
[brief-fe-filtri-lista-su-schermo-compatto.md](work-done/brief-fe-filtri-lista-su-schermo-compatto.md),
[analisi-fe-regole-standard-violate-dal-codice.md](work-done/analisi-fe-regole-standard-violate-dal-codice.md).

### Documenti, vendite, pagamenti e magazzino

**Anello 2 (`documenti`) — Il patto fra la versione di template e la forma dei dati.** Ogni
versione di template dichiara la forma che legge e si stampa solo se coincide con quella del
builder: *Jinja non si lamenta*. Vedi
[brief-db-documenti-versione-contesto-template.md](work-done/brief-db-documenti-versione-contesto-template.md).

**Anello 3 (`vendite`) — Un documento rotto non tiene più in ostaggio il giro, e l'esito ha casa
propria.** Un documento non emettibile esce dal giro e il lotto prosegue; il trattenuto ha una
sede sola; l'esito di un documento nel lotto è un dato, e la segnalazione dice di quale documento
parla. Al rilancio la discovery rivede le commesse trattenute dal lotto stesso, e a valle di un
task eseguito nessun task si salta. Vedi
[brief-db-uscita-documento-dal-giro.md](work-done/brief-db-uscita-documento-dal-giro.md),
[brief-db-documento-trattenuto-da-un-lotto-vivo.md](work-done/brief-db-documento-trattenuto-da-un-lotto-vivo.md),
[brief-db-il-trattenuto-passa-lo-stesso.md](work-done/brief-db-il-trattenuto-passa-lo-stesso.md),
[brief-db-il-marcatore-scrive-su-un-documento-uscito.md](work-done/brief-db-il-marcatore-scrive-su-un-documento-uscito.md),
[brief-db-esito-gruppo-lotto.md](work-done/brief-db-esito-gruppo-lotto.md),
[brief-be-db-gruppo-key-sulle-segnalazioni.md](work-done/brief-be-db-gruppo-key-sulle-segnalazioni.md),
[brief-residuo-fatturabili-e-bandiere-esito-parziale.md](work-done/brief-residuo-fatturabili-e-bandiere-esito-parziale.md),
[brief-db-rilancio-step-non-rivede-le-proprie-commesse.md](work-done/brief-db-rilancio-step-non-rivede-le-proprie-commesse.md),
[collaudo-in-app-esito-parziale-pull-commessa.md](work-done/collaudo-in-app-esito-parziale-pull-commessa.md),
[brief-be-fan-out-isolato-e-esito-parziale.md](work-done/brief-be-fan-out-isolato-e-esito-parziale.md),
[fatturazione-roadmap.md](work-done/fatturazione-roadmap.md).

**Anello 1 + 3 — La numerazione finisce il trasloco, e l'IVA arriva ai consumatori.** La
commessa passa sui registri, la chiave del contatore è esplicita, il CRUD dei registri c'è; il
risolutore IVA arriva ai consumatori applicativi e il default IVA usa una chiave naturale. Vedi
[brief-db-registri-di-numerazione-emittente-e-trasloco.md](work-done/brief-db-registri-di-numerazione-emittente-e-trasloco.md),
[brief-db-registri-numerazione-chiave-del-contatore.md](work-done/brief-db-registri-numerazione-chiave-del-contatore.md),
[brief-be-fe-crud-registri-di-numerazione.md](work-done/brief-be-fe-crud-registri-di-numerazione.md),
[brief-be-fe-iva-fase-3-consumatori-risolutore.md](work-done/brief-be-fe-iva-fase-3-consumatori-risolutore.md),
[brief-db-default-iva-chiave-naturale.md](work-done/brief-db-default-iva-chiave-naturale.md).

**Anello 1 + 3 — L'articolo dice da dove arriva, la riga d'ordine sa quando, la commessa si
legge.** Le date di consegna richiesta e confermata sulle righe d'ordine (vendite e acquisti), il
modo di approvvigionamento dell'articolo, descrizione, apertura e responsabile della commessa.
⚠️ Dichiarato e non deciso: il verbo per la promessa di consegna. Vedi
[brief-db-modifiche-certe-ciclo-vendita-e-articolo.md](work-done/brief-db-modifiche-certe-ciclo-vendita-e-articolo.md).

**Anello 3 (`vendite`, `pagamenti`) — Le forme che reggono, e annullare vuol dire chiudere.** D14:
la partita di merce si legge per documento, e hanno retto le forme, non i millisecondi; un prezzo
non autorizzato non esce dalla bozza; un lotto si annulla solo se vuoto; le righe di una distinta
`ANNULLATA` escono dalle code. Vedi
[brief-db-partita-merce-per-documento.md](work-done/brief-db-partita-merce-per-documento.md),
[brief-db-preventivi-congelamento-pricing.md](work-done/brief-db-preventivi-congelamento-pricing.md),
[brief-db-annullamento-chiude-la-vita.md](work-done/brief-db-annullamento-chiude-la-vita.md),
[brief-db-righe-distinta-annullata-fuori-dalle-code.md](work-done/brief-db-righe-distinta-annullata-fuori-dalle-code.md).

**Anello 3 (`pagamenti`) — La distinta prende il numero dal registro, e impara a cercare le rate.**
La distinta dice di quale emittente è e prende il numero dal motore dei registri; il lookup
fattura diventa ricco, nasce la lista rate e la modalità multipla — *la domanda vera non è «quale
fattura?» ma «quale rata?»*. Vedi
[brief-db-distinta-numerata-sul-registro.md](work-done/brief-db-distinta-numerata-sul-registro.md),
[brief-db-distinta-ricerca-rate.md](work-done/brief-db-distinta-ricerca-rate.md).

**Anello 3 (`magazzino`) — Dal terreno vuoto alla merce che esce e rientra.** Lotto 1: sorgente
obbligatoria, verso nella quantità, emittente come ancora. Lotto 2: la porta unica del registro,
inventario e rettifica, e il BE/FE. Le anagrafiche di magazzino escono dal pannello config. Lotto
3: la merce esce con la bolla; Lotto 3-bis: rientra col reso, al costo dell'uscita d'origine — *un'asimmetria
fra due versi si chiude subito*. Vedi
[brief-db-magazzino-lotto-1-terreno-vuoto.md](work-done/brief-db-magazzino-lotto-1-terreno-vuoto.md),
[brief-db-magazzino-lotto-2-motore.md](work-done/brief-db-magazzino-lotto-2-motore.md),
[piano-be-fe-magazzino-lotto-2-motore.md](work-done/piano-be-fe-magazzino-lotto-2-motore.md),
[brief-db-magazzino-lotto-2-bis-be-fe.md](work-done/brief-db-magazzino-lotto-2-bis-be-fe.md),
[brief-db-magazzino-anagrafiche-guard-ubicazioni-e-codici.md](work-done/brief-db-magazzino-anagrafiche-guard-ubicazioni-e-codici.md),
[piano-be-fe-magazzino-anagrafiche-fuori-dal-pannello-config.md](work-done/piano-be-fe-magazzino-anagrafiche-fuori-dal-pannello-config.md),
[brief-db-magazzino-lotto-3-scarico-da-ddt.md](work-done/brief-db-magazzino-lotto-3-scarico-da-ddt.md),
[brief-db-magazzino-lotto-3-bis-carico-da-reso.md](work-done/brief-db-magazzino-lotto-3-bis-carico-da-reso.md).

### Rimasti per intero — citano un documento ancora aperto

> Testo com'era nella voce d'origine, indicata fra parentesi.

*(voce del 10 settembre)* **Anello 0 — I pgTAP misurano davvero, e la CI misura la CI.** La suite era un
cancello che si poteva attraversare: `continue-on-error` la rendeva un parere, e
la baseline dei rossi era compilata **a mano** su una macchina di sviluppo — cioè
descriveva quella macchina, non il contratto. Il 9 settembre la baseline della CI
viene **misurata dalla CI** su un database ricostruito da zero, il
`continue-on-error` sparisce, e il ramo di bootstrap **fallisce invece di
passare**. Escono tre difetti d'ambiente che tenevano rossi interi gruppi di file
e due building block di fixture riusabili. ⛔ E si scopre la forma peggiore del
difetto: *un cancello che passa perché non ha misurato niente è peggio di un
cancello assente*. Vedi
[migliorie-generali-da-test-valutazione.md](work-in-progress/migliorie-generali-da-test-valutazione.md).

*(voce del 14 settembre)* **Anello 0 — La postura degli oggetti si presidia per criterio, e il registro
della CI cala.** Le tre `SECURITY DEFINER` di `postgres` senza `search_path` —
una sul percorso di 305 trigger `tx_id` — hanno il pin (12-09), nella timeline
normale e senza superuser, col **prestito di proprietà** via
`fn_sync_functions_owner`. ⚠️ Con una lezione presa dal verso opposto: la forma
«prudente» `pg_catalog, pg_temp` avrebbe **accecato** `dblink`, che vive in
`public`, dentro un `WHEN OTHERS` — spegnendo il tracciamento delle transazioni
**senza un rosso da nessuna parte**. *Una forma canonica uguale per tutte non
esiste: si decide per funzione, guardando ciò che chiama.* Il terzo invariante di
D5 ha ora il suo pgTAP sul catalogo (`test-security-definer-search-path-v1`),
come i primi due. Sul registro della CI il triage è partito **dal perimetro**:
21 file (le `fn_scope_*`, il fail-closed, le `rls/`) morivano nella fixture
perché **cercavano** i soggetti fra i dati esistenti, e su un database
ricostruito `anagrafiche` è a zero — riscritti con fixture che **costruiscono**
il mondo, e nessun ramo `skip` residuo. Il registro passa da 406 (09-09) a 403
(12-09) a **372** (14-09), e i RIENTRATI li toglie ora uno script che legge il
log della corsa, non una mano. Lato applicazione, D15: `skip_area_check` era
**muto** su 15 view che dichiaravano anche `area_funzionale` — sei delle quali
scrivevano senza permesso — e le famiglie hanno deciso quale delle due parole
vale; le due vulnerabilità npm e `weasyprint 70` sanate senza dipendenze nuove.
Vedi
[brief-db-fixture-che-costruiscono-d7-d6-d4.md](work-done/brief-db-fixture-che-costruiscono-d7-d6-d4.md),
[migliorie-generali-da-test-valutazione.md](work-in-progress/migliorie-generali-da-test-valutazione.md) §D4-D7 e §D13,
[migliorie-generali-BE-FE-da-test-valutazione.md](work-done/migliorie-generali-BE-FE-da-test-valutazione.md) §D1, §D15.

*(voce del 19 settembre)* **Anello 3 (`pagamenti`) — Il collaudo in-app scrive venti decisioni di
dominio.** Tre giri in cinque giorni, e ogni giro ha lasciato il modello
diverso da com'era. **D16-D18** (14→15-09): la riga manuale **nasce cercando la
fattura** e compare già `ABBINATA`; «Non riesco ad associarlo» è un gesto
dichiarato e non un ripiego; **Elimina** in bozza fa tornare la quadratura;
sotto `VALIDATA` il contenuto è fermo. **D20** (18→19-09): 🔴 **le righe che
restano indietro hanno un futuro** — una `SOSPESA` o una `SCARTATA` sotto una
distinta registrata non entrava più in nessun conto e non poteva più
diventarlo: ora `fn_posta_riga_tardiva` la riprende, la distinta resta `CHIUSA`
e la quadratura non cambia; e i «Porta a» da `ABBINATA` escono dalla matrice.
⭐ Due cose da tenere: *un pulsante che finisce in errore è un difetto di
modello* — «Registra» era acceso in BOZZA mentre il DB rispondeva
`E_CONTABILE_NON_REGISTRABILE`; e il brief chiude sul **percorso**, l'**esito**
lo prova il copione, che per questo vive in `work-in-progress/` e non in un
brief chiuso. I due piani, DB e BE/FE, sono **chiusi e archiviati il 19-09**:
non resta codice da scrivere. Vedi
[brief-db-riga-manuale-nasce-abbinata-ed-elimina-riga.md](work-done/brief-db-riga-manuale-nasce-abbinata-ed-elimina-riga.md),
[brief-db-validata-e-registrazione-tardiva.md](work-done/brief-db-validata-e-registrazione-tardiva.md),
[brief-db-posting-e-abbinamento-rata.md](work-done/brief-db-posting-e-abbinamento-rata.md),
[brief-be-fe-posting-e-abbinamento-rata.md](work-done/brief-be-fe-posting-e-abbinamento-rata.md),
[collaudo-in-app-incassi-distinte-e-sistemazioni.md](work-in-progress/collaudo-in-app-incassi-distinte-e-sistemazioni.md).

*(voce del 19 settembre)* **Anello 1 (`ui`) — Il frontend: le classi che non esistevano, e il chrome che
sta in una sede sola.** Tre passate il **17-09**, tutte nate guardando i fogli
di stile invece del codice: **21 utility PrimeFlex mai installate** (`w-full` in
245 punti) che non facevano niente; **60 `var()`** che puntavano a nomi di
PrimeVue 3 o a token `--app-*` mai scritti — e queste **facevano eccome**,
perché `border: 1px solid var(--surface-border)` con la variabile assente
annulla l'intera dichiarazione (i pannelli di `pratiche` senza bordi, senza
hover, senza voce selezionata) e il **body era senza font** senza che si
vedesse; **26 identificatori orfani**. Da lì nasce il presidio
`scripts/check_classi_morte.py` (pre-commit: tiene il conto a **zero**) e, il
giorno dopo, il **chrome del dialog in una sede unica** con la sua guardia
(`check-dialog-chrome.mjs`). ⛔ *Un difetto che **toglie** un colore non si
vede*: il testo «sottotono» era testo normale in 135 siti. Nello stesso giro il
frontend prende liste **responsive senza scrollbar orizzontale**, content tab
comprimibili, `app-dialog-lista` e la pagina compatta degli store. Vedi
[frontend/catalogo-building-block-frontend.md](frontend/catalogo-building-block-frontend.md)
e
[piano-migrazione-primevue-5.md](work-in-progress/piano-migrazione-primevue-5.md).

*(voce del 30 settembre)* **Anello 0/1 — La credenziale è una, le porte sono tante.** L'analisi degli
accessi (D-1…D-10, decise il 24-09, chiusa il 28) separa due oggetti: la
**credenziale** (password, tentativi, blocco, sessioni) e la **veste**, la
porta da cui si entra — *cambia la porta, non il ciclo di vita*. Il lato DB
atterra in ~50 changeSet il 25/27-09: lo stato del login esce da
`identita_digitali` e va in `config.credenziali`; tre regole — freno sulla
provenienza, attesa crescente sulla credenziale, **blocco solo da
SUPER_ADMIN** — perché *un blocco deciso da uno sconosciuto non è una
protezione, è un'arma*. Email unica senza maiuscole, una persona una
credenziale, la veste OPERATORE nasce spenta; ⭐ **porta e profili
sganciati** — *la veste attiva dice se la porta è aperta; il binding dice cosa
si può fare dentro*; la risposta del login non rivela se il nome esiste. Il
consenso al riuso della credenziale legge da una funzione sola (*il contesto
dell'errore non è un canale verso il client*). Due corollari sul perimetro: la
RLS delle **mail** applica l'**ambito** (OPERATORE = chi l'ha creata) in AND con
l'emittente — prima un operatore leggeva le mail dei colleghi — e *una mail
inviata non si cancella*; l'**assistente AI** si concede per area come ogni
dominio — *assume i privilegi con cui l'operatore è attivo, e nessuno di
più*. ⚠️ Aperto: i lotti L-2 (blocco dell'admin), L-4 (login per email), L-5,
L-6 del piano BE/FE. Vedi
[analisi-accessi-credenziale-e-vesti.md](work-done/analisi-accessi-credenziale-e-vesti.md),
[brief-db-blocco-login-per-credenziale.md](work-done/brief-db-blocco-login-per-credenziale.md),
[brief-db-credenziale-per-email.md](work-done/brief-db-credenziale-per-email.md),
[brief-db-email-visibilita-per-ambito.md](work-done/brief-db-email-visibilita-per-ambito.md),
[brief-db-area-funzionale-assistente-ai.md](work-done/brief-db-area-funzionale-assistente-ai.md),
[piano-be-fe-accessi-credenziale-e-vesti.md](work-in-progress/piano-be-fe-accessi-credenziale-e-vesti.md).

### Rimasti per intero — «In breve», senza un brief

*(voce del 10 settembre)* **In breve, senza un tema proprio** — il **fondo fattura** con ricalcolo e governo
applicato il 31 agosto; l'**archiviazione delle righe di coda** e la
storicizzazione dei bersagli spariti; il **perimetro delle email** e l'invio di
sistema; i **riferimenti contratto** sugli atti di fattura; tre giri di **seed
liste** (lotto, titolo IVA, admin `ui`); due **design** che preparano il magazzino
— la partita merce generalizzata e la situazione merce di un ordine; e la
migrazione della clausola `ORDER BY` lato backend.

*(voce del 14 settembre)* **In breve, senza un tema proprio** — la **copertura della doc API** rimisurata
il 12-09 (613 rotte, la misura vecchia contava come «coperte» rotte servite da
segnaposto, e `pagamenti` passa da 1/25 a 25/25 con una pagina sola); le
**rotte senza porta** (D7) hanno tutte una risposta scritta (due candidate al ritiro,
una schermata da aprire: il registro email dell'operatore); l'**area funzionale
dell'assistente AI** ha il brief e attende la riga di catalogo, perché la
decisione è che lo usino anche gli operatori; l'analisi dell'osservabilità
riletta contro il repo (B e C erano «mossi da fuori» dal cantiere dei presidi);
in `api.md` cinque voci dicevano ancora «la testata ha la RLS, il figlio no» e
ora il fatto sta in una sede sola; e in `AGENTS.md` tre regole nuove nate da
altrettanti incidenti — *un privilegio su una macchina è un ricordo*,
`unittest.TestCase` non è `SimpleTestCase`, e dove si legge l'errore vero di un
pgTAP in CI (nel log del container, non nella baseline).

*(voce del 19 settembre)* **In breve, senza un tema proprio** — la **revisione delle guide** di
`docs/it/guide/` parte il 19-09 e prosegue oltre questa voce: header standard,
il changelog in testa **dissolto nel corpo** invece che cancellato, accenti,
tabelle rialineate, con le regole in
[standard-guide.md](standard-guide.md); il censimento dei brief aperti in
questa tornata — `brief-db-magazzino-lotto-2-bis-be-fe.md` (BE/FE del Lotto 2),
`brief-db-presidio-stati-mai-scritti.md`,
`brief-be-presidio-ui-action-e-canale-campi.md` e
[brief-db-registri-giornale-catalogo.md](work-done/brief-db-registri-giornale-catalogo.md),
il cui **lato DB è chiuso il 19-09** (`config.registri_giornale`, pgTAP
13/13) — più il copione
[collaudo-in-app-osservabilita-giornale-errori-pallino.md](work-done/collaudo-in-app-osservabilita-giornale-errori-pallino.md),
scritto e **da eseguire**; `vendite.fatturazione_lotti_log` con **17.223 pagine
per 1.225 righe** dopo la retention del 18-09 (fatto datato: un `VACUUM` lo
dirà); lo `.pyc` di `gen_seed_lista` **tracciato in git** e una lista mai
montata, rimossi; `check_i18n_keys` e i guard del frontend (liste, pinia,
drawer, icone, keepalive, DataTable) verdi a ogni giro.

*(voce del 30 settembre)* **In breve, senza un tema proprio** — la verifica «doc API contro codice» su
47 documenti di `core` apre un'analisi BE che chiude in quattro giorni una
ventina di voci (fra cui 90 letture grezze di `request.data` passate al BB
`corpo_oggetto`), con dodici ancora aperte
([analisi-be-difetti-emersi-verifica-doc-api-core.md](work-done/analisi-be-difetti-emersi-verifica-doc-api-core.md));
nelle migliorie BE/FE i primi **test di componente** del frontend (23-09),
`pip-audit` in CI e la schermata del log email (D7); i **copioni di collaudo
in-app** scritti e da eseguire salgono a otto (capability annidata e prezzi,
casella di ricerca, consenso al riuso della credenziale, inventario e
rettifica, permessi ereditati, osservabilità, incassi, UI permessi
operatore); 🔴 dal 21-09 sera la CI su GitHub **non partiva** per un blocco di
billing (fatto datato, dal brief del Lotto 2); invariati il `USAGE` di
`zeroerp_log` su `dbops` in CI e «Riavvia» (D1), entrambi decisioni di Tid.

---

## agosto 2026

> **Riepilogo del mese** (le voci datate **10** e **30 agosto** sono state
> compattate qui il 2026-09-20). Il dettaglio non è andato perso: vive nei brief
> linkati, che sono tutti in `work-done` — e dove un tema non ha un brief, il
> testo resta com'era. Due link puntano ancora a `work-in-progress/`: il brief
> madre degli incassi e il suo collaudo vivono lì per scelta (sono il registro
> delle decisioni e il copione), non per incompiutezza.
>
> Il mese copre **27 luglio → 30 agosto**: venti giorni densi (**460 changeSet**
> fra `00_schema` e `20_code`, 268 in `vendite` e 57 in `pagamenti`) più le due
> settimane del cantiere a cavallo di luglio. ⚠️ Il **31 agosto** era volutamente
> fuori quando queste voci furono scritte: ciò che è atterrato quel giorno — il
> trasloco dei registri, i consumatori BE/FE del risolutore IVA, l'apply del
> fondo fattura — sta nella voce di settembre.

**Anello 3 (vendite) — La nota di credito, e il ramo economico dei resi.** Il
reso portava indietro merce e motivo e **nessun valore**: `resi_righe_accrediti`
e `config.nature_doc_fiscale` chiudono il ramo degli accrediti su DB, BE e FE,
validato a video con un collaudo spuntato riga per riga. Subito dopo cade anche
l'ultimo arco del **lineage** — la nota di credito era collegata alla fattura
che rettifica ma non alla merce che l'aveva causata — e con lui i tre residui
del grafo (il `root` che dipendeva dagli id, la commessa senza origine, la nota
di credito che in lista si chiamava «Fattura»). Vedi
[brief-design-note-credito-resi.md](work-done/brief-design-note-credito-resi.md),
[brief-db-lineage-arco-reso-nota-credito.md](work-done/brief-db-lineage-arco-reso-nota-credito.md),
[brief-db-lineage-residui-root-e-sorgente-ddt.md](work-done/brief-db-lineage-residui-root-e-sorgente-ddt.md).

**Anello 3 (vendite) — La data del documento smette di essere un effetto
collaterale.** Una fattura di luglio prendeva il numero 11 perché la sequenza
era dedotta dal giro: chi decide data e sequenza diventa il **registro**, un
**limite di emissione** evita che un documento nasca non più trasmissibile, e
registro e data prevista si vedono in lista *prima* di generare. ⭐ L'analisi sui
**due motori di numerazione** prende la decisione portante — la commessa passa
sui registri, e la periodicità dentro `config.sistema_codici` **non si fa più**
perché senza la commessa quella colonna non ha più un cliente — e l'esecuzione è
del giorno dopo (voce di settembre). Vedi
[brief-db-numerazione-data-documento-e-sequenza.md](work-done/brief-db-numerazione-data-documento-e-sequenza.md),
[brief-db-limite-emissione-e-data-verificata.md](work-done/brief-db-limite-emissione-e-data-verificata.md),
[analisi-db-numerazione-documenti-e-due-motori.md](work-done/analisi-db-numerazione-documenti-e-due-motori.md).

**Anello 1 + 3 — L'IVA ha un risolutore, e il regime del cliente smette di
essere scritto e mai letto.** La domanda di partenza era stretta (*«su un
omaggio o un reverse charge l'IVA non discende più dall'articolo: è giusto che
si possa modificare?»*); cercandone la risposta è emerso che **l'IVA la
decideva l'articolo e nessun altro** e che le colonne del regime fiscale del
cliente erano compilate dall'operatore e **lette da nessuno**. Il modello non
mette un default sul cliente — l'influenza del soggetto passa **sempre da un
titolo registrato e documentato** (`anagrafiche.soggetti_titoli_iva` con ambiti e
registro movimenti **append-only**, dove anche l'annullo di una forzatura è un
movimento, più il vocabolario `config.tipi_titolo_iva`). Al 30 agosto il lato
**DB è chiuso**; i consumatori applicativi arrivano la settimana dopo. Vedi
[brief-db-be-iva-risolutore-e-regime-cliente.md](work-done/brief-db-be-iva-risolutore-e-regime-cliente.md).

**Anello 3 (`pagamenti`) — Il posting esiste.** Il cantiere si apriva su una
misura sgradevole: *nessuna funzione, in tutto il database, scriveva
`pagamenti.vendite_movimenti`* — e per costruzione il saldo di una fattura era
sempre il totale. Ora il motore c'è: registrazione della contabile, saldo della
rata, guard di transizione e di capienza, **sistemazione delle eccedenze**,
distinta di correzione; e `enti_incasso`, che di row security non ne aveva,
smette di mostrare l'**IBAN** di ogni emittente a qualunque operatore.
⛔ **Ma di questo dominio è provato il percorso, mai l'esito**: lo schema ha
ancora zero righe e il collaudo in-app è **aperto** — è il cantiere che occupa
la voce di settembre. Vedi
[brief-db-posting-e-abbinamento-rata.md](work-done/brief-db-posting-e-abbinamento-rata.md),
[brief-be-fe-posting-e-abbinamento-rata.md](work-done/brief-be-fe-posting-e-abbinamento-rata.md),
[collaudo-in-app-incassi-distinte-e-sistemazioni.md](work-in-progress/collaudo-in-app-incassi-distinte-e-sistemazioni.md).

**Anello 3 (vendite) — Il lavoro che non torna indietro.** Le tre porte di reset
della fatturazione — elimina fattura, riporta il lotto a DRAFT, annulla il lotto
— cancellavano righe su cui era già stato registrato un accredito, e l'esito non
era un rifiuto ma una violazione di chiave esterna **a metà lavoro**. Ma la
parte che si vede è un'altra: il lavoro rimasto indietro ha un **verbo**
(«Riporta da emettere», con la card che si spezza in due per non promettere una
fattura che non c'è) e **«Rendi definitive» è tornata sulla lista Lotti**, dove
sta l'elenco del suo oggetto invece di una card che ne mostrava un altro. Vedi
[brief-db-lavoro-che-non-torna-indietro.md](work-done/brief-db-lavoro-che-non-torna-indietro.md),
[brief-be-fe-rendi-definitive-sui-lotti.md](work-done/brief-be-fe-rendi-definitive-sui-lotti.md),
[brief-db-guard-righe-fattura-rettificate.md](work-done/brief-db-guard-righe-fattura-rettificate.md).

### Errori, presidi e liste — agosto 2026

**Anello 0 — L'errore porta un bersaglio, e la riga di log dice per chi.** Due
cantieri gemelli, stessa idea: un messaggio non serve se non si sa *su cosa*. Il
**Passo 0 dell'osservabilità** rende parlante la riga di `vendite.event_log` —
perimetro emittente, `tx_id`, identità del giro — e la mette sotto RLS **prima**
che esista un endpoint di lettura, perché sui campi di una riga append-only *non
esiste rimedio a posteriori*, mentre policy, indici e viste si aggiungono in
qualunque momento. Il **bersaglio** fa lo stesso sull'errore: dice **su quale
entità**, in una forma che l'interfaccia trasforma in un gesto («vai lì») e chi
diagnostica legge come coordinata. Quattro lati in due giorni, DB → roll-out →
backend → toast con azioni. Vedi
[brief-db-event-log-scope-e-riga-parlante.md](work-done/brief-db-event-log-scope-e-riga-parlante.md),
[brief-db-bersaglio-errore.md](work-done/brief-db-bersaglio-errore.md).

**Anello 0 — I presidi che non presidiavano.** Tre presidi del progetto
cercavano i test con un glob a **un livello solo**: le sottocartelle di schema —
16 file — erano fuori dalla baseline, fuori dal guardrail del preambolo, fuori
dal censimento dei `LIMIT 1`. Dodici erano rossi e nessuno lo sapeva; la
baseline diceva «nessuna regressione» e non mentiva — *quei file non li aveva
guardati*. Sanato il ramo cieco, il debito è stato attaccato: **da 86 rossi su
442 file a 19 su 551**. Nello stesso filone il catalogo dei messaggi smette di
promettere segnaposto che nessun chiamante riempiva (un `%s` che arrivava a
video letterale) e gli **smoke test** prendono una baseline: undici script che
nessuno lanciava, e per un giorno sei erano rossi senza che si notasse. Vedi
[brief-db-pgtap-rami-ciechi.md](work-done/brief-db-pgtap-rami-ciechi.md),
[brief-db-bonifica-baseline-pgtap-vendite.md](work-done/brief-db-bonifica-baseline-pgtap-vendite.md),
[brief-db-segnaposti-messaggi-errore.md](work-done/brief-db-segnaposti-messaggi-errore.md).

**Anello 1 — Il perimetro emittente, e due invarianti che nessuno presidiava.**
Il perimetro dell'emittente fiscale aveva due buchi nello stesso presidio —
l'accesso alle liste e la gerarchia dei billing account — tenuti insieme perché
uno teneva aperto l'altro; chiusi, con la colonna emittente sulle cinque liste
rimaste e nella riga della ricerca universale. Da lì escono due domande di
dominio rimaste implicite: **un billing account può cambiare emittente?** (sì,
finché non ha storia — e il motivo per cui non si può arriva *sulla riga*, non
premendo il pulsante) e **l'emittente della commessa può essere NULL?** (no: la
commessa lo deriva dalla cascata delle sorgenti). Vedi
[brief-db-perimetro-emittente-liste-e-gerarchia-ba.md](work-done/brief-db-perimetro-emittente-liste-e-gerarchia-ba.md),
[brief-db-billing-account-cambio-emittente.md](work-done/brief-db-billing-account-cambio-emittente.md),
[brief-db-emittente-commessa-invariante.md](work-done/brief-db-emittente-commessa-invariante.md).

**Anello 1 (`ui`) — Una regola che non sta dove si legge non esiste.** Il piano
delle liste aveva invertito il rapporto (40 file sul building block, registro
43/43); rimisurato il **30 agosto**, i file sul building block salgono a **53**,
ma quelli con `DataTable` grezza — scesi a 48 il 3 agosto — **risalgono a 57**.
La **«regola zero della lista»** viene allora spostata in cima ad `AGENTS.md`,
dove si legge a inizio sessione: stava in `frontend-standards.md`, che si apre
quando serve e che anzi spiegava *come* configurare una `DataTable`. ⭐ **È il
difetto che vale più del numero — non era nel codice, era nella sede della
regola.**

⚠️ **E il numero, guardato bene, non dice quello che sembra.** Classificati i 57:
**26 sono drawer e dialog** e 15 pannelli o tab annidati — cioè l'**eccezione
che `AGENTS.md` ammette**, non liste fuori standard — **6 sono i wrapper
stessi**, e restano **5 view di lista** più 5 `*SearchTable` di dominio. Col
paginator, il segno della lista vera, i file sono 13 e sei sono wrapper. ⛔ *Il
presidio a un numero solo non separa il debito dalla crescita del frontend*: la
regola resta giusta, il contatore che la accompagna misura un'altra cosa.

**Manutenzione e chiusure.** DDT: le righe a prezzo zero sono ammesse (il
solo-trasporto non è un difetto di prezzo) e il DDT di **ri-consegna** non nasce
più nudo — eredita causale e indirizzi invece di farli ridigitare. `is_attiva`
rispondeva a **due domande con un flag solo** (è la revisione corrente? è ancora
in gioco?): separate, e il filtro «Annullato» è passato da 0 risultati *per
costruzione* a 17. `acquisti` e `magazzino` sono stati **misurati** il 21 agosto
e documentati: modello disegnato, tutte le tabelle a zero righe — e in
`magazzino` un CHECK rendeva inseribili **solo i trasferimenti**. Archiviati per
verifica contro il codice vivo: il documento di progettazione della pipeline
(febbraio) e l'indice attività preventivi.

### Dal 27 luglio al 10 agosto

ℹ️ **Da qui le voci del 27 luglio – 10 agosto**, due settimane a cavallo del mese
dominate da due cantieri trasversali (**la classe dei codici errore** e **i
satelliti della fattura**) e da un cambio di regime nei test: da qui in poi il
pgTAP gira come l'applicazione.

**Anello 0 + 1 — La classe dei codici errore: il significato dell'errore torna a
catalogo.** Il cantiere più grande del mese (05→09 agosto, DB + BE conclusi): il
significato di un errore viveva **solo** in un dizionario Python di 659 voci
scritte a mano, e il catalogo DB non aveva il campo in cui la contraddizione si
sarebbe vista. Ora un codice si registra **a catalogo** in `config.codici_errore`
(**690 voci**) dichiarando **che cosa è** — la sua `classe`, dal vocabolario di
`config.classi_errore` (**10 valori**) — e status HTTP e `ui_action` si
**derivano**; il modulo Python `error_policies_generated.py` è **generato** dal
catalogo e presidiato in CI (`--check`). Tre conseguenze che valgono oltre il
cantiere: il codice viaggia in un **campo strutturato** (`SQLSTATE P0001` con
`CONSTRAINT` valorizzato), letto in un punto solo (`db_error_fields.py`) invece
dei quattro che lo riscrivevano a modo loro; i due registri del debito sono **a
zero** (141 → 0 in tre giorni, 150 decisioni; 57 → 0) e restano in piedi apposta
— *un registro in pari non è un registro inutile*; e l'envelope d'errore porta
`fields`, senza il quale `ui_action: highlight_form_fields` non è azionabile.
Vedi [brief-db-be-classe-codici-errore.md](work-done/brief-db-be-classe-codici-errore.md),
[piano-db-classe-codici-errore.md](work-done/piano-db-classe-codici-errore.md),
[piano-be-classe-codici-errore.md](work-done/piano-be-classe-codici-errore.md),
[brief-db-codice-errore-strutturato.md](work-done/brief-db-codice-errore-strutturato.md),
[brief-db-be-terzo-lato-presidio-codici.md](work-done/brief-db-be-terzo-lato-presidio-codici.md).

**Anello 0 — 🔴 Il pgTAP gira come l'applicazione, ed entra in CI.** Dal 7
agosto il runner di default è l'utente applicativo e non più l'owner: **le
policy RLS sono esercitate a ogni corsa**, e un rosso può essere un **permesso**
o una **policy**, non solo una fixture. I 29 file che hanno davvero bisogno
dell'owner sono marcati uno per uno **con la ragione scritta**; la suite entra
in CI con una baseline sua, perché il DB della CI è ricostruito da zero e i
rossi sono **popolazioni diverse**; tre righe di preambolo diventano
obbligatorie e presidiate da un cancello — *senza, un file diventa verde per
sottrazione*. Debito noto: **86 rossi** su **442 file**. Vedi [brief-db-pgtap-runner-rls-baseline.md](work-done/brief-db-pgtap-runner-rls-baseline.md)
e la guida [pgtap-come-si-scrive-un-test](../guide/pgtap-come-si-scrive-un-test.md).

**Anello 0 — Presidio dei riferimenti morti (04 agosto).** 34 difetti sanati e
cancello in CI: un riferimento a un oggetto DB che non esiste più non arriva più
al merge. ⚠️ Il guardrail gira **dopo** `manage.py migrate` — non spostarlo (a
settembre si prenderà due lezioni, voce di settembre). Vedi [brief-db-bonifica-riferimenti-morti.md](work-done/brief-db-bonifica-riferimenti-morti.md),
[brief-be-bonifica-riferimenti-morti.md](work-done/brief-be-bonifica-riferimenti-morti.md).

**Anello 3 (vendite) — I satelliti della fattura: il documento si racconta per
intero.** Cantiere chiuso su tutte le fasi (29 luglio – 3 agosto): **piano rate**
(`vendite.fatture_scadenze`, generato nello step EMESSA dopo il ricalcolo IVA,
idempotente per costruzione, con lo **snapshot del termine** in testata — ⚠️ non
è uno scadenzario: non esiste stato di pagamento della rata), **snapshot** di
intestazione e indirizzi, **drawer di consultazione** in un round-trip che
orchestra gli **stessi** lettori del PDF (*video e stampa raccontano lo stesso
documento per costruzione*), le **note fattura** come sesto dominio del building
block note (~15 righe di configurazione, zero migration), e il ritiro del
generatore di righe SQL.

Vedi [piano-db-satelliti-fattura.md](work-done/piano-db-satelliti-fattura.md),
[piano-be-fe-satelliti-fattura.md](work-done/piano-be-fe-satelliti-fattura.md),
[brief-db-generazione-scadenze-fattura.md](work-done/brief-db-generazione-scadenze-fattura.md),
[brief-be-fe-drawer-fattura.md](work-done/brief-be-fe-drawer-fattura.md).

**Anello 3 (vendite) — Emissione mirata e ritorno del lotto a DRAFT.** Il giro
accetta un perimetro ristretto ai **gruppi fatturabili** scelti — stesso verbo,
stessa idempotenza: assente = giro di massa invariato — e il lotto può **tornare
a DRAFT** per rifare un giro andato storto. Vedi
[brief-db-emissione-fattura-per-documento-sorgente.md](work-done/brief-db-emissione-fattura-per-documento-sorgente.md),
[brief-be-fe-emissione-fattura-mirata.md](work-done/brief-be-fe-emissione-fattura-mirata.md),
[piano-db-ritorno-lotto-a-draft.md](work-done/piano-db-ritorno-lotto-a-draft.md).

**Anello 2 (documenti) — Ristampa fedele: il terzo percorso.** Ri-renderizzare
un documento **com'era** — versione di template pinnata, anche OBSOLETA, e
`context_json` congelato — senza persistere nulla, distinto dallo **scarica
originale** (il file su storage) e dal **genera nuovo documento** (modello e dati
di oggi, che fino ad allora si chiamava impropriamente «ristampa»). La fedeltà è
dichiarata in header: byte diversi = fedele nel contenuto, non un errore. Vedi
[brief-ristampa-fedele-documenti.md](work-done/brief-ristampa-fedele-documenti.md).

**Anello 1 (`ui`) — Le liste: il rapporto si è invertito.** Il numero scomodo del
piano — 14 liste sullo standard contro 71 con `DataTable` grezza — non c'è più:
**40 file montano il building block**, il registro del presidio è a **43/43**, il
Gruppo A si è chiuso **30/34** il 3 agosto, e i **4 file rimasti sono fermi per
decisione** (cassetti senza endpoint paginato), non per debito.

> 🚨 **Ma il piano non è più tecnico.** `primevue`, `@primeuix/themes` e
> `primeicons` erano **MIT** e passano tutti e tre alla **licenza PrimeUI**
> (community/commerciale, con chiave) dalla nuova major. ZeroErp è **GPL v3
> pubblica**. Non è un rischio di migrazione: è una **decisione di licenza**, e
> non la prende un piano operativo — dal 20 settembre sta fra le «Decisioni
> aperte» della mappa, dove nessun cantiere la può scavalcare.

Vedi [piano-migrazione-primevue-5.md](work-in-progress/piano-migrazione-primevue-5.md)
§1-bis e [consuntivo-personalizzazioni-liste-def.md](work-done/consuntivo-personalizzazioni-liste-def.md).

**Anello 3 (`pagamenti`) — Si apre il cantiere delle contabili di pagamento
(9-10 agosto).** Due scoperte cambiano la scala del lavoro: **nessuna funzione,
in tutto il database, scrive `pagamenti.vendite_movimenti`** — il *posting* è
documentato e non implementato, quindi `fn_get_saldo_fattura` restituisce per
costruzione sempre l'intero totale — e **i cataloghi dello schema erano già
seminati** (la macchina a stati dell'abbinamento `DA_ABBINARE → ABBINATA →
POSTATA` esiste da sempre a catalogo). Decisioni portanti: l'abbinamento vive
**sulla riga contabile e arriva alla rata**, lo stato della rata è **derivato**,
il posting è una madre DB per testata contabile, **lo storno non esiste come
concetto** — è una contabile con importi negativi, e la sicurezza sta in un
controllo simmetrico `0 ≤ Σ ≤ importo` — e il perimetro dei soldi non ancora
attribuiti si deriva **dal conto di incasso**. Vedi [brief-incassi-riconciliazione-rate-promemoria.md](work-in-progress/brief-incassi-riconciliazione-rate-promemoria.md)
e, per il meccanismo dei fondi fattura da ripensare,
[brief-db-fondo-fattura-ricalcolo-e-governo.md](work-done/brief-db-fondo-fattura-ricalcolo-e-governo.md).

**Manutenzione.** Bonifica indici: corrette le viste `dbops`, aggiunte guardie
sull'`apply`, rimossi **48 indici ridondanti** (27 luglio). Commesse: permesso di
cambio stato, **annullamento delle righe manuali** (non cancella: porta a
`ANNULLATA` con motivo obbligatorio), guard di uscita. Lato BE, fan-out isolato
con esito parziale.

---

## luglio 2026

> **Riepilogo del mese** (le voci datate 10, 11, 12 e 26 luglio sono state
> compattate qui il 2026-09-01). Il dettaglio non è andato perso: vive nei brief
> linkati, che sono tutti in `work-done`.

**Anello 3 (vendite) — Il DDT di vendita, e con lui il quinto dominio del motore
documentale.** Nuovo documento del ciclo attivo: testata di trasporto + righe con
**prezzo e IVA opzionali** (il DDT di solo trasporto è legittimo) + componenti
BoM condivisi. Nasce per **evasione** di un ordine confermato — legame 1:N con
**residuo per riga** append-only, dove l'evasione *aggiunge* la quantità evasa
invece di sottrarla — oppure standalone. Stati data-driven
`DRAFT → EMESSO → SPEDITO → CONSEGNATO` (+ `RESO`/`ANNULLATO`), **numero
assegnato all'emissione** e poi immutabile, push a commessa per la fatturazione.
Guida: [gestione-ddt.md](../guide/gestione-ddt.md). Vedi
[brief-db-ddt-vendita-evasione-e-stati.md](work-done/brief-db-ddt-vendita-evasione-e-stati.md),
[brief-be-ddt-vendita.md](work-done/brief-be-ddt-vendita.md),
[brief-fe-ddt-vendita.md](work-done/brief-fe-ddt-vendita.md).

> ℹ️ **Tre cose di questo cantiere non hanno un brief e vivono solo qui.**
>
> - **Stampa PDF DDT — 5° dominio del motore documentale**: template
>   `DDT_VENDITA` pubblicato + builder del contesto (testata, trasporto, righe,
>   totali, note). Anteprima in bozza e documento definitivo all'emissione
>   seguono il pattern degli altri domini (`pdf_mode` data-driven da
>   `stati_doc_ddt`). Export lista DDT (CSV/XLSX) allineato agli ordini.
> - **Addendum SCOPE §15 — emittente memorizzato + RLS**:
>   `vendite.ddt.emittente_fiscale_id` NOT NULL sul documento (mirror
>   ordini/preventivi), ereditata dall'ordine in evasione o risolta dal billing
>   account per lo standalone, con policy `rls_ddt_ef_whitelist` e guard di scope
>   in scrittura — un operatore non emette DDT fuori dal proprio scope.
> - **Due estrazioni per regola del 2**: la factory
>   `build_documenti_sorgente_views` per le 7 view «documenti per sorgente» di
>   ogni dominio (~80 righe risparmiate a dominio) e
>   `add_emittente_scope_condition`, che risolve l'array di scope emittente
>   **una volta** in Python — era 2× per query in 5 repository.

**Anello 3 (vendite) — I resi: il documento di rientro merce.** Sesto documento
del ciclo attivo, nato dal DDT, **senza valori economici** (il ramo nota di
credito è la slice successiva): conferma che riapre il residuo dell'ordine,
annullo come storno, **ri-consegna** parziale e multipla, due code di lavoro
configurabili, azioni data-driven. A chiusura, la **rinuncia alla ri-consegna** —
senza la quale una ri-spedizione mai eseguita lascia l'ordine
`PARZIALMENTE_EVASO` per sempre, senza via d'uscita in-app. Vedi
[brief-db-resi-vendita.md](work-done/brief-db-resi-vendita.md),
[brief-be-fe-resi-vendita.md](work-done/brief-be-fe-resi-vendita.md),
[brief-db-chiusura-riconsegna-reso-definitivo.md](work-done/brief-db-chiusura-riconsegna-reso-definitivo.md).

**Anello 3 (vendite) — La fatturazione di DDT e resi passa a contatore.**
`config.tipi_reso.riapre_residuo` era un flag **logistico** che decideva anche
cosa succedeva ai **soldi**: due domande su una colonna sola. Sostituito da un
**contatore di merce** per riga d'ordine (spedito − reso), che chiude due bug di
doppia fatturazione invisibili alle dashboard — le mostravano come transito
legittimo. Vedi
[brief-db-fatturazione-ddt-resi.md](work-done/brief-db-fatturazione-ddt-resi.md),
[brief-be-fe-ddt-resi-dashboard.md](work-done/brief-be-fe-ddt-resi-dashboard.md).

**Anello 3 (vendite) — Quantità immutabili sulla commessa, e la porta oneri.**
Le quantità già fatturate diventano immutabili. Sopra quella base si apre la
porta oneri, con il modello **articolo↔causale 1:1**: un articolo *è* un onere
perché ha una causale collegata, e così **ogni onere porta la propria IVA**.
Chiusa anche una race sul progressivo degli oneri manuali, dove due operatori
concorrenti ricevevano entrambi 200 OK e un dato spariva in silenzio. Vedi
[brief-db-immutabilita-quantita-e-porta-oneri.md](work-done/brief-db-immutabilita-quantita-e-porta-oneri.md),
[brief-be-fe-immutabilita-quantita-e-porta-oneri.md](work-done/brief-be-fe-immutabilita-quantita-e-porta-oneri.md),
[brief-db-race-segment-key-onere.md](work-done/brief-db-race-segment-key-onere.md).

**Anello 3 (vendite) — Il cockpit: dalle lenti all'azione, e la stampa che non
tiene il lock.** Le tre lenti smettono di essere una fotografia: dalla Dashboard
Competenza si **agisce**. Il punto architetturale non è l'interfaccia ma la
**stampa massiva senza tenere il lock del registro fiscale durante il
rendering** — la stampa diventa un task che *accoda* e il render vive in un
worker che drena. La fattura è il **6° dominio** del motore documentale.
Completano il quadro il **guard di uscita commessa** (chiuderne una con righe
ancora fatturabili era perdita irreversibile di fatturato, invisibile alla
dashboard) e le capability con motivo. Guida:
[cruscotti-fatturazione.md](../guide/cruscotti-fatturazione.md) §7. Vedi
[brief-design-gestione-processi-fatturazione.md](work-done/brief-design-gestione-processi-fatturazione.md),
[brief-db-processi-fatturazione-cockpit.md](work-done/brief-db-processi-fatturazione-cockpit.md),
[brief-be-fe-processi-fatturazione.md](work-done/brief-be-fe-processi-fatturazione.md),
[brief-db-guard-uscita-commessa-e-capabilities.md](work-done/brief-db-guard-uscita-commessa-e-capabilities.md).

**Anello 0 (`dbops`) — La coda lavori generica: la regola del 2 applicata
all'architettura.** `vendite.fatture_stampa_coda` stava per essere seguita da una
seconda tabella-coda per il giro on-demand. Invece di **una tabella per batch** si
è estratta una **coda di job generica**, DB-native, transazionale e senza broker:
è la fondazione asincrona dell'ERP. Guida:
[gestione-code-di-lavoro.md](../guide/gestione-code-di-lavoro.md). Vedi
[brief-design-coda-lavori-generica.md](work-done/brief-design-coda-lavori-generica.md),
[brief-db-coda-lavori-generica.md](work-done/brief-db-coda-lavori-generica.md).

**Anello 1 (`ui`) — La dashboard home, e il secondo consumatore dello schema.**
Card KPI configurabili con lo **stesso impianto a cascata** delle liste (sistema
→ profilo → emittente → utente) e filtro sui permessi dell'operatore. È la
conferma richiesta dal principio 7: il pattern non è stato inventato per la home,
è stato **riusato** perché già decantato dalle liste. Vedi
[brief-db-dashboard-home.md](work-done/brief-db-dashboard-home.md),
[brief-be-fe-dashboard-home.md](work-done/brief-be-fe-dashboard-home.md).

**Anello 3 (vendite) — La genealogia dei documenti, e gli indirizzi come building
block.** Il **lineage** espone il grafo dei documenti come pannello «Passaggi» nei
drawer e come colonne pratica/fase/transito nelle liste: da un documento si risale
a monte e si scende a valle senza uscirne. In parallelo gli **indirizzi documento**
diventano un BB cross-dominio sui 5 domini vendite — sezione inline + drawer di
gestione, **snapshot congelato all'emissione**, auto-assegnazione del default — e
il DDT prende il suo riepilogo IVA (righe senza prezzo escluse: un DDT di solo
trasporto non ha riepilogo). Vedi
[brief-db-lineage-documenti-vendite.md](work-done/brief-db-lineage-documenti-vendite.md),
[brief-be-fe-lineage-documenti-vendite.md](work-done/brief-be-fe-lineage-documenti-vendite.md),
[brief-design-indirizzi-documenti-vendita.md](work-done/brief-design-indirizzi-documenti-vendita.md),
[brief-db-ddt-riepilogo-iva.md](work-done/brief-db-ddt-riepilogo-iva.md).

**Qualità di modello — tre presidi che c'erano e non presidiavano.** (1) Il guard
sulla **sorgente polimorfa** esisteva ma **non era agganciato a nulla**:
agganciato, dati bonificati, convenzione documentata
([sorgente-polimorfa.md](../guide/sorgente-polimorfa.md)) e 13 pgTAP bonificati
(rossi 131 → 111). (2) **Coerenza `tx_id`**: mai pubblicare nella GUC un id non
registrato — il difetto bloccava ogni ambiente *senza* canale di log, CI
compresa, e ora la CI esercita il caso peggiore invece di aggirarlo. (3) **RLS
scope emittente** estesa a `commesse` e `commesse_attivita`. Vedi
[brief-db-guard-sorgente-polimorfa.md](work-done/brief-db-guard-sorgente-polimorfa.md),
[brief-db-bonifica-pgtap-sorgente-polimorfa.md](work-done/brief-db-bonifica-pgtap-sorgente-polimorfa.md),
[brief-db-coerenza-tx-id-non-registrato.md](work-done/brief-db-coerenza-tx-id-non-registrato.md),
[brief-db-rls-commesse.md](work-done/brief-db-rls-commesse.md).

**Trasversale (frontend) — radici i18n uniformi e residui PrimeVue 3.** 21 radici
i18n piatte riportate sotto le rispettive aree: ⚠️ un indirizzo i18n inesistente
non dà errore, **non mostra nulla** — difetto invisibile, e l'archivio aveva due
stili di sistemazione conviventi scelti a caso. Chiusi anche i residui PrimeVue 3
e corretto lo standard che ancora li prescriveva: era debito che **faceva
scrivere codice nuovo sbagliato**. Vedi
[brief-i18n-radici-uniformi.md](work-done/brief-i18n-radici-uniformi.md),
[brief-fe-migrazione-primevue4-tabs.md](work-done/brief-fe-migrazione-primevue4-tabs.md).

---

## giugno 2026

> **Riepilogo del mese** (le voci datate 11, 13-19, 20 e 28 giugno sono state
> compattate qui il 2026-09-01). Copre l'11 → 28 giugno; per il periodo
> precedente vedi «Aggiornamenti ricostruiti dal 26 aprile all'11 giugno».

**⭐ Anello 2 (`pratiche`) — Il motore passa da *predisposto* a *validato dal
primo consumatore*.** È la milestone del mese, e vale più di ciò che è stato
scritto: gli **ordini di vendita** nascono end-to-end (CRUD, conferma, EVASO,
stampa PDF, conversione preventivo/offerta→ordine) e sopra di essi gira la
**pratica PREVENTIVI**, primo consumatore reale del motore — handler
`CONFERMA_VENDITA`, split per natura merce→ordine / servizi→commessa,
smistamento riga-per-riga, commesse multi-sorgente. ⚠️ L'uso reale ha scovato
bug che la «completezza tecnica» non aveva intercettato (handler_params persi,
funzioni di push con NOT NULL violabili, generazione non idempotente, azioni di
processo mai seedate): è la conferma sul campo della lezione «pratiche prima di
vendite». Vedi
[analisi-ordini-vendita.md](work-done/analisi-ordini-vendita.md),
[analisi-pratiche-workflow-v2.md](work-done/analisi-pratiche-workflow-v2.md).

**Anello 2 (`pratiche`) — Workflow v2: le estensioni che l'uso reale ha
chiesto.** Il completamento del flusso diventa **event-driven** (rimosso
l'endpoint manuale) e l'azione che chiude lo step è **risolta da configurazione,
non cablata**. Il documento sorgente si àncora a uno **specifico flusso**, non
alla sola testata. La pratica si chiude solo a flussi obbligatori completati.
L'esito del flusso diventa configurabile (MANUALE / AUTOMATICO / CONTESTUALE), il
giornale porta l'**utente reale** ed è append-only per trigger, e il flusso si
**assegna** a operatore o reparto con policy reparto-first, alimentando una coda
a quattro livelli e il pannello «Le mie attività». Vedi
[brief-design-esito-configurabile-flussi.md](work-done/brief-design-esito-configurabile-flussi.md),
[brief-db-assegnazione-flusso.md](work-done/brief-db-assegnazione-flusso.md),
[brief-design-coda-lavoro-mie-attivita.md](work-done/brief-design-coda-lavoro-mie-attivita.md).

**Anello 3 (vendite) — Il batch di fatturazione diventa automatico end-to-end.**
La pipeline passa da «operativa (manuale)» a batch: driver CRON `run-until-done`,
discovery a **corsie** `(emittente, tipo_doc, utility)`, **sync dello stato
documentale per-step** `1→2→8` — l'IVA è certificata in EMESSA *prima* della
numerazione in DEFINITIVA — e run headless registrate in `job_run_log`. Con
l'hardening del push commesse→fatturazione arriva l'invariante che evita il
«fatturato perso in silenzio»: `APPROVATA + NON_EMESSA ⇒ tipo_doc NOT NULL`,
guard di riga più CHECK di backstop. Vedi
[piano-fix-stato-fattura-pipeline-per-step.md](work-done/piano-fix-stato-fattura-pipeline-per-step.md),
[brief-db-emittibili-lane-tipo-doc-fiscale.md](work-done/brief-db-emittibili-lane-tipo-doc-fiscale.md),
[brief-db-guard-tipo-doc-attivita.md](work-done/brief-db-guard-tipo-doc-attivita.md).

**Qualità di modello — `codice_interno` contro `codice`, su tutto il perimetro.**
Le tabelle di lookup hanno due colonne con destini opposti — `codice_interno`
**immutabile** per la logica, `codice` **mutabile** per il display — e il progetto
le confondeva in due modi speculari: alias bugiardi (`codice_interno AS *_codice`,
che esponeva l'immutabile col nome del mutabile) e hardcode `WHERE codice = 'X'`
dove la logica doveva usare l'altra. Bonificati **21 BUG_DUAL + 7 candidati**,
16 oggetti della pipeline commesse→push→fatturazione, ed è emerso un **bug reale**
(`fn_lookup_utilities_per_ba` tornava zero righe perché `codice ≠ codice_interno`).
Chiuso con un **guardrail CI catalog-based bloccante**. Vedi
[brief-naming-stato-codice-interno.md](work-done/brief-naming-stato-codice-interno.md),
[analisi-hardcoded-codice.md](work-done/analisi-hardcoded-codice.md).

**Manutenzione.** Corretta l'asimmetria del gate EVASO sul ramo commessa
(verificata runtime, non solo applicata) e avviato lo smoke E2E
push commesse→fatturazione. Sospensioni pratica: anti-sovrapposizione e guard
sulla data manuale. Revisione critica del documento di sicurezza AI/agenti
tradotta in piano di allineamento. Vedi
[brief-db-gate-evaso-commessa-asimmetria.md](work-done/brief-db-gate-evaso-commessa-asimmetria.md),
[brief-db-sospensioni-anti-overlap-data-manuale.md](work-done/brief-db-sospensioni-anti-overlap-data-manuale.md),
[analisi-sicurezza-aggiornata.md](work-done/analisi-sicurezza-aggiornata.md).

---

## 29 maggio 2026

Anello 3 (vendite): contratti passati al modello unificato (drop modalità A/B/C, eccezioni `tipo_eccezione`, snapshot versione listino all'attivazione, lock post-attivazione, stato ANNULLATO); nuovo documento **offerte commerciali** (proposta di condizioni quadro → push 1:1 a contratto) sviluppato DB+BE+FE con generazione PDF e allegati; componenti BoM compositi estesi a offerte; valuta su documenti vendite. Vedi [Gestione Offerte commerciali](../guide/gestione-offerte-commerciali.md) e [Gestione Contratti](../guide/gestione-contratti.md).

## Aggiornamenti ricostruiti dal 26 aprile all'11 giugno 2026

| Data         | Evidenza                                                                                                                                                                                                                                                                                      | Impatto sulla mappa                                                                                                |
| ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| 26 aprile    | `dbops.automazione_chiusura_scadenze` chiuso come framework parametrico dopo due consumatori reali (`vendite.listini_versioni`, `vendite.contratti`)                                                                                                                                          | Anello 0 cresce per uso osservato, non per astrazione preventiva.                                                  |
| 27 aprile    | Contratti: Profilo A, immutabilita' post-DRAFT, cessazione data-driven, righe-preview                                                                                                                                                                                                         | Vendite rafforza il sottodominio contratti e consuma il framework di chiusura a scadenza.                          |
| 28 aprile    | Refactor frontend/backend catalogo completato Fasi 1-8, test BE 83/83 e build Vite verdi                                                                                                                                                                                                      | Catalogo resta operativo ma con contratti API/metadata piu' maturi.                                                |
| 29-30 aprile | Refactor amm-software completato per matrici, operatori, permessi, emittenti e policy admin                                                                                                                                                                                                   | Anello 1 amministrativo consolidato; le matrici diventano riferimento UI per configurazioni complesse.             |
| 1 maggio     | Refactor vendite chiuso DB+BE+FE, modello documentato con 1406 test BE e build Vite verde                                                                                                                                                                                                     | Vendite aggiornata a pattern data-driven per lookup, defaults, capability e azioni.                                |
| 2 maggio     | Preventivi rev2 landed: `emittente_fiscale_id` persistito, `istanza_utility_id` obbligatoria, guard coerenza utility/istanza, 4 codici errore                                                                                                                                                 | Preventivi diventano piu' rigorosi sul contesto emittente/utility.                                                 |
| 3 maggio     | Scenario preventivi 2.1 chiuso end-to-end, UI revisioni e riepilogo IVA                                                                                                                                                                                                                       | Vendite avanzata su flusso preventivo operativo.                                                                   |
| 3-4 maggio   | Motore documentale parametrico: DB Fase A, backend Tranche A-K, frontend Tranche L-M; test UI dedicato avviato                                                                                                                                                                                | Nuovo componente `documenti` in Anello 2, operativo tecnicamente ma ancora in test UI.                             |
| 13 maggio    | BoM modello unificato + simmetria listino; componenti BoM (CASO A) estesi a preventivi/ordini/ddt/contratti                                                                                                                                                                                   | I documenti vendite condividono lo stesso modello componenti a 3 livelli (struttura, listino, documento).          |
| 15-21 maggio | Refactor contratti: modello unificato (drop modalità A/B/C, eccezioni `tipo_eccezione`, snapshot versione listino all'attivazione, lock post-attivazione, stato ANNULLATO + overlap parziale)                                                                                                 | Il sottodominio contratti diventa simmetrico ai preventivi e pronto a ricevere l'offerta come sorgente.            |
| 24-27 maggio | Offerte commerciali (DB): testata + eccezioni delta-listino + componenti BoM + utility, 6 stati, `fn_push_offerta_a_contratto` idempotente, vista `is_attiva`, azioni data-driven                                                                                                             | Nuovo documento pre-contrattuale in Anello 3 (vendite): la proposta di condizioni quadro che genera il contratto.  |
| 28-29 maggio | Offerte commerciali (BE+FE): risoluzione prezzo come contratti, generazione documento offerta con allegati, UI uniformata a contratti                                                                                                                                                         | Offerta operativa end-to-end DB+BE+FE; in consolidamento/test UI.                                                  |
| 29 maggio    | Valuta su documenti vendite (`valuta_id` su offerte/contratti/preventivi, default da resolver gestore); guida offerte commerciali pubblicata                                                                                                                                                  | Coerenza valuta cross-documento; documentazione di dominio allineata allo stato reale.                             |
| 2 giugno     | Gate prezzi L1/L2/L3 esteso alle offerte (stesso orchestratore dei contratti); vincoli EXCLUDE anti-overlap ripristinati e governati dal framework `dbops.automazione_overlap`                                                                                                                | Coerenza pricing cross-documento; Anello 0 consolida l'anti-overlap parametrico.                                   |
| 2-4 giugno   | RLS scope emittente fiscale ATTIVA per operatori: `ENABLE` su 10 tabelle documentali + Ondata 2 scrittura (`FOR ALL` + `WITH CHECK`, migration `20260603-16..25`); reset GUC fail-closed a inizio richiesta lato BE                                                                           | Multi-Face Auth passa da "infrastruttura predisposta" a RLS operatori attiva; policy portale/shop restano dry-run. |
| 3-4 giugno   | Ordini di vendita DB+BE+FE: vista lista DEF-8, CRUD, conferma, stampa PDF (modulo stampa generico), conversione preventivo/offerta→ordine, lock cliente; regola del 2 su anagrafiche e core (estrazione BB)                                                                                   | Vendite chiude il documento ordine: il ciclo preventivo/offerta→ordine e' percorribile end-to-end.                 |
| 5 giugno     | Regola del 2 core FE/BE (factory `createCrudStore`, guard-versione, stack geografico); unificazione sconto righe ordini/fatture; riepilogo IVA documenti non fiscali esteso a ordini                                                                                                          | Anello 0/1 frontend consolidano building block condivisi; meno duplicazione cross-dominio.                         |
| 8 giugno     | Univocita' offerta→(contratto XOR ordine) con status 409 coerenti; stato ordine EVASO con transizione automatica CONFERMATO→EVASO                                                                                                                                                             | Il downstream dell'offerta diventa mutuamente esclusivo; il ciclo ordine ha uno stato terminale data-driven.       |
| 9-10 giugno  | Pratica PREVENTIVI: handler `CONFERMA_VENDITA` BE+FE (commit `327140116`); `natura_vendita` su preventivi con split merce→ordine / servizi→commessa; smistamento merce→ordine riga-per-riga; commesse multi-sorgente (1 ROOT + N COLLEGATO); natura di vendita amministrabile da applicazione | Vendite diventa il primo consumatore reale del motore pratiche (Anello 2).                                         |
| 11-12 giugno | Workflow pratiche v2: ripetibilita' flussi, bivi condizionali, lenti contesto, guard chiusura; contesto pratica a 3 livelli (soggetto → ruolo → istanza derivata/filtrata); BB informazioni pratica; azioni di processo pratiche seedate                                                      | `pratiche` passa da "predisposta" a **validata con primo consumatore** (vedi Anello 2).                            |

---

## Sprint storici (marzo – metà aprile 2026)

> Sintesi a livello di milestone delle fondamenta costruite prima del periodo coperto
> dalla tabella sopra. Volutamente **non dettagliata** (niente conteggi test, nomi di
> singoli componenti o numeri di sprint): alcune di queste implementazioni sono state
> in seguito riviste o rifatte diversamente — per lo stato attuale fa fede la
> [mappa](../mappa-concentrica.md), non queste righe. Da fine aprile in poi la cronologia
> prosegue nella tabella sopra.

### Marzo 2026 — fondamenta

- Anello 2 `pratiche`: backend completo (macchina a stati, sospensioni, calcoli tempo), consumabile via REST.
- Anello 0: audit sessioni JWT, request logging, revoca/blacklist token.
- Frontend Sprint 1–7: layout applicativo (sidebar, content tabs, breadcrumb), Amm. Software (operatori, profili reparto, permessi, audit log), building block riutilizzabili (SoggettoForm, autocomplete, composable core), Gestione Geografica (7 tab CRUD), Gestione Soggetti PF/PG/ENTE, pannello config generico, modalita' sola lettura + azioni di processo (permessi livello 1+2), split view, Pratiche v2 frontend.
- Refactor modello concentrico (v3/v4): logica duplicati/CAP/indirizzi/nominativo spostata da frontend a DB/backend.
- Integrazione AI v1 (Anello 4): widget flottante + primi tool lettura/scrittura con conferma.

### Aprile 2026 (fino a metà mese) — domini di vendita e autenticazione

- Gestione Autenticazioni fasi 1–3: email building block, token monouso, reset/invito/cambio password.
- Deprecato il codice errore generico `E_GENERICO` a favore di codici specifici per schema.
- Gestione Clienti v1 + catena automatica istanza fittizia → billing account → cliente.
- Catalogo Articoli + UoM + Listini (DB+BE+FE), poi consolidato e testato.
- Parametri di sistema multi-scope (override personale/emittente).
- Emittenti fiscali CRUD + mapping billing account + matrice utilities; refactor operatore-emittenti 1-a-1 (GUC d'identita').
- Migrazione a `daterange`/`tstzrange` nativo PostgreSQL con vincoli GIST anti-overlap.
- Listini v3: variazioni di massa, alert scadenze, rettifiche controllate; Permessi v2 (`model_permission` a livello oggetto).

---

*Changelog della Mappa Concentrica — ZeroERP. Nuove voci in alto (prosa) o in coda alla tabella del periodo corrispondente.*
