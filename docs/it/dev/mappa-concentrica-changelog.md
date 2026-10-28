# Mappa Concentrica — Changelog

> **Ultimo aggiornamento**: 28 ottobre 2026

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
  [brief-modello-documento-vendita.md](work-in-progress/brief-modello-documento-vendita.md)
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
[brief-modello-documento-vendita.md](work-in-progress/brief-modello-documento-vendita.md),
[brief-db-documento-nasce-nello-stato-iniziale.md](work-done/brief-db-documento-nasce-nello-stato-iniziale.md),
[brief-db-scadenza-preventivi.md](work-in-progress/brief-db-scadenza-preventivi.md).

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

## 30 settembre 2026

> Copre il periodo **20 – 30 settembre**. Undici giorni, **400 changeSet**
> datati fra il 20 e il 30 (109 in `script`, 94 in `vendite`, 54 in `90_end`,
> 40 in `dbops`, 34 in `config`, 21 in `ui`, 14 in `magazzino`, 11 in
> `anagrafiche`, 10 in `documenti`), **quaranta documenti chiusi in
> `work-done`** e **109 merge** (dalla PR #1628 alla #1737). Si scrive per
> **temi**: sono dieci.
>
> ⚠️ Fuori da questa voce, perché nati il **1° ottobre**:
> `brief-db-esigibilita-iva-per-cassa-emittente.md`,
> `brief-db-esposizione-componenti-kit-in-fattura.md`,
> `brief-db-totp-ricifra-segreto.md`, e lo spostamento in `work-done` di
> `brief-db-codici-cancello-obblighi-e-sfida-totp.md` — al 30-09 era
> **consegnato a file e da applicare**.
>
> ⭐ **Il tema portante è *una regola, una sede* — e la sede di un permesso è
> il verbo che scrive.** Lo stesso difetto si è presentato in quasi ogni
> cantiere: un fatto scritto in tre, cinque, sette posti che **dissentivano in
> silenzio** (lo spareggio dei profili, la soglia della ricerca, le misure di
> pagina, l'imponibile di riga, la versione del listino in vigore, il prezzo
> autorizzato, le righe lavorabili di una distinta). E sotto, una frase che
> cambia il nucleo: *il DB **calcola** i permessi ma non li **applica*** — da
> qui il modello *una scrittura = un verbo*, con il magazzino come primo caso
> e il pannello config come secondo.

**Anello 0 — Il DB applica i permessi, non solo li calcola.** Il modello sta
in un brief che resta aperto per costruzione
([brief-db-permesso-nel-verbo-di-scrittura.md](work-done/brief-db-permesso-nel-verbo-di-scrittura.md),
D-1…D-5 del 24-09): il verbo dichiara il permesso **nella prima riga** con un
BB unico (`fn_guard_azione` per i processi, `fn_guard_livello` per il CRUD; la
terza forma, `fn_guard_super_admin`, nasce il 25-09 col blocco login), e
l'applicazione perde la scrittura sulle tabelle protette e l'`EXECUTE` sulle
primitive. *Una tabella non è un'operazione*: niente policy RLS sul livello.
Primo caso il **magazzino** (24/25-09): `fn_posta_inventario` e
`fn_posta_rettifica` chiedono `registra_magazzino`, l'app perde la porta
`fn_scrivi_movimento` — *la porta decideva **da dove** si scrive, non **chi***.
Secondo caso il **pannello config** (25→28-09, D-P1…D-P9): «Gestione tabelle»
scrive con **un verbo** che controlla il livello sull'**oggetto della riga**,
la lista ammessa è un dato (`config.tabelle_gestibili`, 87 voci, 63 nel
pannello), e le tabelle con RLS escono — *un verbo generico non sa rimettere un
perimetro*. ⚠️ Strada facendo un difetto vero: chi aveva `TUTTO` su
Configurazione modificava `config.profili_accesso` e **si alzava i privilegi**
— *il verbo applica fedelmente una lista sbagliata* (D-P6: 19 righe fuori;
D-P9: `config.aree_funzionali` in sola lettura per l'app). Il verso opposto lo
chiude il BE: ogni `GET`/`HEAD` gira in `SET TRANSACTION READ ONLY` — *«una
lettura non scrive» passa da promessa del codice a garanzia del DB* (194 GET
provate, nessuna scrive; le GET di dettaglio con parametri restano da vedere
in-app). E la postura: `dbops.sec_functions_owner` è in sola lettura per l'app
e la sync **si difende nel corpo** — *una `SECURITY DEFINER` di `postgres` non
si chiude con l'ACL* (D6-registro, 26-09). ⚠️ Aperto: il **passo 3** (i domini
esistenti), senza data. Vedi
[brief-db-magazzino-verbi-con-permesso.md](work-done/brief-db-magazzino-verbi-con-permesso.md),
[brief-db-pannello-config-verbo-generico.md](work-done/brief-db-pannello-config-verbo-generico.md),
[brief-be-letture-in-transazione-sola-lettura.md](work-done/brief-be-letture-in-transazione-sola-lettura.md),
[brief-db-registro-owner-e-sync-riservati-al-migratore.md](work-done/brief-db-registro-owner-e-sync-riservati-al-migratore.md).

**Anello 0/1 — Le porte dicono la stessa cosa.** Il **catalogo degli oggetti
personalizzabili** (28-09) ora coincide con le **quattro porte** — BE
`model_permission`, FE `READONLY_MODELS`, il verbo DB, il catalogo: prima il
pannello offriva override che nessuno applicava (*un override che **mente***),
e ne applicava altri che non offriva. La regola «override solo su oggetto a
catalogo e non riservato» va a DB con una FK composita, la blacklist Python si
ritira; 27 righe (17 personalizzabili, 10 riservate), `model_permission` su 58
view. ⭐ *Applicato dal FE ma non dal BE*: un `BLOCCATO` che nasconde i
pulsanti e lascia aperta l'API — A e B si chiudono **insieme**, per oggetto.
L'**ereditato** del pannello permessi si calcola a DB (25-09): lo spareggio
era scritto in **cinque** posti, i resolver ora chiamano la stessa funzione;
D-1 i permessi da operatore contano solo i profili della veste `OPERATORE` (un
operatore multi-veste si portava dietro il `PORTALE` del cliente), D-3 *il più
specifico vince* (prima, a parità, `LIMIT 1` sceglieva a caso). E la
**capability annidata** (23/24-09): *il blob sta sotto `capabilities`, non
fuso nel dettaglio* — preventivi riscriveva in Python campi decisi dal DB, ed
era l'**unica sede di metà della regola**: *una regola che non sta dove si
legge non esiste*. Vedi
[brief-db-be-fe-catalogo-oggetti-permessi.md](work-done/brief-db-be-fe-catalogo-oggetti-permessi.md),
[brief-db-pgtap-permessi-ereditati.md](work-done/brief-db-pgtap-permessi-ereditati.md),
[brief-be-fe-capability-annidata.md](work-done/brief-be-fe-capability-annidata.md),
[brief-db-messaggio-ba-senza-emittente.md](work-done/brief-db-messaggio-ba-senza-emittente.md).

### Accessi e sicurezza — 30 settembre

**Anello 0/1 — La credenziale è una, le porte sono tante.** L'analisi degli
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

**Trasversale — Sicurezza in profondità, dalla superficie al secondo
fattore.** Tre passate sul BE e sull'infrastruttura, scritte come *regole, non
opzioni*: il **21-09** la superficie pubblica (gunicorn solo su loopback, rate
limit in Nginx, admin Django tolto — `/admin/` rispondeva 200 —, Swagger solo
se acceso, test `test_superficie_pubblica`); il **26-09** i segreti fuori da
git (`backend/.env` → `.env.example`), **gitleaks** in pre-commit e in CI,
`check --deploy` in CI, `SECRET_KEY` obbligatoria e `DEBUG` spento di default;
il **28-09** HSTS e redirect, **refresh token nel cookie `HttpOnly`** e access
token solo in memoria (10 minuti), chiave di cifratura separata dalla
`SECRET_KEY` — *ruotare la `SECRET_KEY` non spegne più i dati cifrati*. Il
**secondo fattore TOTP** chiude il lato DB il 29-09 (22 changeSet, D-T1…D-T5):
l'obbligo sta sulla credenziale **o** sul profilo (sempre acceso sul
SUPER_ADMIN, garantito da un CHECK), sei verbi del device, ⭐ anti-replay *sul
passo, non sul codice*, sblocco d'emergenza solo dalla sessione del migratore
con traccia. I tre codici del **cancello degli obblighi** sono consegnati a
file il 30-09, **da applicare**. ⚠️ Aperto: il TOTP lato BE/FE (lotti
T-0…T-5, dal 30-09). Vedi
[brief-be-fe-sicurezza-header-token-mfa.md](work-done/brief-be-fe-sicurezza-header-token-mfa.md),
[brief-db-secondo-fattore-totp.md](work-done/brief-db-secondo-fattore-totp.md),
[configurazione-django.md](backend/configurazione-django.md).

### Controlli automatici e test — 30 settembre

**Anello 0 — Ciò che la CI non vedeva: trigger generati e giro notturno.**
Quattro brief, lo stesso difetto di forma — una funzione generica riceve il
dato **negli argomenti del trigger** e nessuno confronta il vivo con la sede.
`CODICE_NON_MODIFICABILE`, ritirato il 05-08, era ancora sollevato da **69
trigger** col presidio verde, perché guardava i corpi e il codice viaggiava in
`tgargs` — *un valore che viaggia come DATO non si trova cercando CODICE*
(23-09). Il job delle 21:10 **cancellava i lock scritti a mano**: il registro
diventa l'**unica sede** di un lock, un runner solo converge, e *dev non era
fuori modello: era l'unico ambiente in cui il modello girava per intero*
(26-09). Su 5 tabelle il trigger di **storico** cercava una colonna FK col nome
sbagliato e ogni UPDATE di una riga storicizzata moriva — ora il rubinetto
verifica la colonna prima di montare (25-09). E i **job notturni girano in
CI** (26-09): `85_pgagent` è `MARK_RAN` e tutto ciò che faceva solo un job era
invisibile; `dbops.processi` dichiara `ci_ordine`/`ci_procedura`/
`ci_esclusione` e un `ci_apply` chiama in ordine le 11 procedure — al primo
giro ha trovato due tabelle mancanti dalla storicizzazione. *La copia da
togliere non è l'elenco, sono i corpi.* Nella stessa famiglia la regola
«`valido_al` non precede `valido_dal`» prende **una sede sola** montata per
presenza della coppia di colonne (25 tabelle, cinque copie e due codici
ritirati). Vedi
[brief-db-codici-ritirati-negli-argomenti-dei-trigger.md](work-done/brief-db-codici-ritirati-negli-argomenti-dei-trigger.md),
[brief-db-lock-di-colonna-fuori-registro.md](work-done/brief-db-lock-di-colonna-fuori-registro.md),
[brief-db-storico-colonna-fk-dei-trigger.md](work-done/brief-db-storico-colonna-fk-dei-trigger.md),
[brief-db-job-notturni-in-ci.md](work-done/brief-db-job-notturni-in-ci.md),
[brief-db-guard-date-validita.md](work-done/brief-db-guard-date-validita.md).

**Anello 0 — Presidi e fixture: il mondo si costruisce, i presidi del
percorso storto esistono.** I due brief aperti il 19-09 si chiudono: **C1**
(21-09) — un valore ammesso dal CHECK di una colonna di stato e mai scritto è
*una promessa vuota*, e la scrittura ha smentito il brief (32 colonne, 114
valori invece di 18: c'era una seconda forma di cast) —, e **C2** (22-09) — la
`ui_action` promessa a catalogo e il canale che la realizza viaggiavano su due
binari; sanati 13 codici Python e 49 siti PL/pgSQL, e *il rosso si è spento per
la sanatura, non per il presidio*. Il **giro 2 delle fixture** (23-09) porta il
BB di composizione `fn_pgtap_crea_mondo_cliente()` e i builder di fattura,
gestore, listino…: *ciò che non esiste è la composizione*; nessun file della
suite fa più `COMMIT`. I presidi a catalogo passano da **42 a 49** (C1, C2,
`vw_funzioni_check_codici`, il lotto chiuso con errori, il DDT emesso senza
scarico, il reso confermato senza carico). pgTAP: **12 rossi su 738 file** su
dev (16 su 671 il 19-09); il registro della CI è a **361** (362), mentre le
misure vere — **229 su 687** il 24-09, **227 su 714** nella corsa del 26-09 —
**non sono ancora certificate** nel registro. ⚠️ D7 resta aperto come debito
residuo (18 rossi del lotto 2 tornati lì). Vedi
[brief-db-presidio-stati-mai-scritti.md](work-done/brief-db-presidio-stati-mai-scritti.md),
[brief-be-presidio-ui-action-e-canale-campi.md](work-done/brief-be-presidio-ui-action-e-canale-campi.md),
[brief-db-fixture-che-costruiscono-giro-2.md](work-done/brief-db-fixture-che-costruiscono-giro-2.md).

### Liste e interfaccia — 30 settembre

**Anello 1 (`ui`) — La lista dice da sé che cosa è.** Cinque fatti della
lista scritti in più sedi scendono nel catalogo. La **ricerca libera** di
tutte le liste legge `ricercabile_full` a ogni ricerca (`_DEBITO_RICERCA_A_MANO`
da 32 a 0; Preventivi, Offerte e Contratti cercavano su 2 colonne invece che
su 4; **12 liste cercavano senza dichiararlo**): *cosa si PUÒ cercare* lo dice
il codice, *cosa si CERCA* il catalogo già filtrato dai permessi
(`ui.fn_lista_colonne_ricerca_full`, 23-09). La **soglia** diventa una colonna
(`ricerca_min_caratteri`, 1 sulle 14 liste di configurazione, 3 sulle altre):
«KG» partiva senza `search` e senza errore (26-09). Le **misure di pagina**
hanno un catalogo (`ui.misure_pagina`: 10/25/50/100) — un preset a 15 lasciava
il selettore vuoto, e il resolver *non inventa* più (30-09). Le **azioni
portano un significato, non un glifo**: icona **e** colore escono dal DB e il
FE li ricava dal verbo, un segno per verbo in tutti i domini (27/28-09, 39
righe di `meta` tolte da otto CSV). Vedi
[brief-be-ricerca-full-liste-residue.md](work-done/brief-be-ricerca-full-liste-residue.md),
[brief-db-ricerca-full-colonne-permessi.md](work-done/brief-db-ricerca-full-colonne-permessi.md),
[brief-db-ricerca-full-colonne-da-accendere.md](work-done/brief-db-ricerca-full-colonne-da-accendere.md),
[brief-db-be-fe-ricerca-soglia-per-lista.md](work-done/brief-db-be-fe-ricerca-soglia-per-lista.md),
[brief-db-misure-pagina-catalogo.md](work-done/brief-db-misure-pagina-catalogo.md),
[brief-db-icone-azioni-per-significato.md](work-done/brief-db-icone-azioni-per-significato.md),
[brief-db-lista-articoli-colonne-data.md](work-done/brief-db-lista-articoli-colonne-data.md).

**Anello 1 / frontend — Una sola macchina per ogni gesto.** Le `DataTable`
grezze vengono riclassificate (28-09): dei 44 file, 10 sono eccezioni vere e
le altre diventano liste a catalogo (83-96) — tre **troncavano in silenzio** a
50/100 righe; la catena delle revisioni dell'offerta diventa *un fatto della
riga, fissato alla nascita*. Il registro scende a **31** (11 senza
motivazione). Le **righe di un documento** diventano `<ListaConfigurabile>`
(liste 97-103, lato DB chiuso il 28-09): *il motivo sta nel modello, non nel
dispositivo*; la macchina del form inline è un BB (`useFormInline`, trovata in
dieci sedi perché *lo standard prescriveva la duplicazione*), l'imponibile di
riga passa da otto copie a una, la versione del listino in vigore da sette a
una. I **filtri su schermo compatto** (24-09, 70 view su 70): *un filtro è
stato della LISTA, non decorazione della view*, e *un filtro attivo che non si
vede è una lista che mente per omissione*. L'analisi delle **regole FE violate**
(26-09) mette il verso delle FK fra i domini (`core` non importa più nessun
dominio) e i presidi FE passano da 6 a 13. Lo schema **OpenAPI** è a zero
rilievi drf-spectacular (W001 54 → 0, W002 73 → 0). ⚠️ Aperto: il lotto D
delle righe documento (FE fermo sulla richiesta §9.11 al DB: le righe
AGGIUNTA escono con l'UdM dell'articolo, non della riga). Vedi
[brief-db-liste-datatable-grezze.md](work-done/brief-db-liste-datatable-grezze.md),
[brief-db-liste-righe-documento.md](work-done/brief-db-liste-righe-documento.md),
[brief-fe-filtri-lista-su-schermo-compatto.md](work-done/brief-fe-filtri-lista-su-schermo-compatto.md),
[analisi-fe-regole-standard-violate-dal-codice.md](work-done/analisi-fe-regole-standard-violate-dal-codice.md).

### Magazzino, vendite e documenti — 30 settembre

**Anello 3 (`magazzino`) — Dal motore a video alla merce che esce e
rientra.** Il **Lotto 2** è consegnato intero il 22-09 (CI da zero verde,
prova del lock a due sessioni: *la disponibilità si legge dopo il lock*) e il
suo BE/FE chiude il 23/25-09 (2-bis: capability dei documenti interni,
azione `registra_magazzino`, lucchetto su `magazzino_id`; piano: inventario e
rettifica *una implementazione, due configurazioni*, 19 rotte). Le
**anagrafiche di magazzino escono dal pannello config** (21-09, decisione B):
magazzini, ubicazioni e lotti sono anagrafiche con FK, non vocabolari, con
guard sul padre dell'ubicazione e anti-ciclo. Poi il primo documento vero: il
**Lotto 3** (28-09, 24 changeSet, D-L3-a…k) — la merce esce con la **bolla**,
la sorgente è il **prelievo**, il cambio di stato del DDT è un **verbo**
(`fn_cambia_stato_ddt`), il trasferimento entra al `CONSEGNATO`; e il suo
inverso, il **Lotto 3-bis** (29-09, 19 changeSet): il reso confermato
ricarica al **costo dell'uscita d'origine**, lotto e seriale *si ritrovano,
non si scelgono* — *un'asimmetria fra due versi si chiude subito* (senza il
3-bis la ri-consegna scaricava due volte). ⚠️ Aperto: il **BE/FE dei Lotti 3 e
3-bis** (R-1…R-5: senza, la bolla che muove merce non si emette), CI da zero,
il collaudo a video dell'inventario. Vedi
[brief-db-magazzino-lotto-2-motore.md](work-done/brief-db-magazzino-lotto-2-motore.md),
[piano-be-fe-magazzino-lotto-2-motore.md](work-done/piano-be-fe-magazzino-lotto-2-motore.md),
[brief-db-magazzino-lotto-2-bis-be-fe.md](work-done/brief-db-magazzino-lotto-2-bis-be-fe.md),
[brief-db-magazzino-anagrafiche-guard-ubicazioni-e-codici.md](work-done/brief-db-magazzino-anagrafiche-guard-ubicazioni-e-codici.md),
[piano-be-fe-magazzino-anagrafiche-fuori-dal-pannello-config.md](work-done/piano-be-fe-magazzino-anagrafiche-fuori-dal-pannello-config.md),
[brief-db-magazzino-lotto-3-scarico-da-ddt.md](work-done/brief-db-magazzino-lotto-3-scarico-da-ddt.md),
[brief-db-magazzino-lotto-3-bis-carico-da-reso.md](work-done/brief-db-magazzino-lotto-3-bis-carico-da-reso.md).

**Anello 3 (`vendite`, `pagamenti`) — Le forme che reggono, e annullare vuol
dire chiudere.** **D14 è chiusa il 22-09**: la capability di un DDT pagava le
partite di tutti, ora la partita si legge **per documento**, l'eleggibilità al
push ha una sola implementazione, `vw_contatore_merce` è ritirata e nasce il BB
*le righe di un documento si toccano solo in bozza*. Sette giri applicati,
l'ottavo ritirato lo stesso giorno: hanno retto le **forme**, i millisecondi
erano colore — *il corpo eseguito come query non predice il piano dentro la
funzione*, e 🔴 in `vendite` **82 tabelle su 87 non sono mai state
analizzate**. *Un prezzo non autorizzato non esce dalla bozza* (24-09): cinque
sedi DB che dissentivano più una copia nel BE diventano un BB, e il `REJECTED`
lo guarda finalmente qualcuno. *L'annullamento chiude la vita* (23-09): il
lotto si annulla solo se vuoto, quindi l'annullo **è** lo svuotamento, e
«COMPLETATO con documenti in ERRORE» è impossibile a DB. E in `pagamenti` le
righe di una distinta `ANNULLATA` escono dalle code (30-09): *tre sedi, tre
risposte* diventano una bandiera a catalogo (`righe_lavorabili`) —
`ANNULLATA` vuol dire *non è mai successa*. ⚠️ Aperto: il BE/FE delle righe di
distinta (il brief è in `work-done` ma il suo §10.5 lo dichiara aperto fino al
collaudo). Vedi
[brief-db-partita-merce-per-documento.md](work-done/brief-db-partita-merce-per-documento.md),
[brief-db-preventivi-congelamento-pricing.md](work-done/brief-db-preventivi-congelamento-pricing.md),
[brief-db-annullamento-chiude-la-vita.md](work-done/brief-db-annullamento-chiude-la-vita.md),
[brief-db-righe-distinta-annullata-fuori-dalle-code.md](work-done/brief-db-righe-distinta-annullata-fuori-dalle-code.md).

**Anello 2 (`documenti`) — Il patto fra la versione di template e la forma dei
dati.** *Jinja non si lamenta*: la fattura v3 usciva senza i componenti dei kit
e nessuno se ne accorgeva. Ogni versione di template dichiara ora la forma che
legge (`versione_contesto`, NOT NULL, senza default) e si stampa o si pubblica
solo se coincide con quella del builder — *non è un caso isolato, è il
modello*: con i template per azienda diventa la norma. DB applicato il 30-09
(D-C1…D-C4, backfill su 20 versioni); lo stesso giorno il BE (R-1…R-5: una
costante `CONTEXT_VERSION` per builder, controllo prima del render e alla
pubblicazione) e la fattura alla **forma 2**, con la versione 4 del template che
scorre `riga.componenti`, pubblicata dall'app. ✅ Chiuso il 2026-10-01. Vedi
[brief-db-documenti-versione-contesto-template.md](work-done/brief-db-documenti-versione-contesto-template.md).

**In breve, senza un tema proprio** — la verifica «doc API contro codice» su
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

## 19 settembre 2026

> Copre il periodo **15 – 19 settembre**. Cinque giorni, **109 changeSet**
> datati fra il 15 e il 19 (26 in `pagamenti`, 26 in `magazzino`, 22 in
> `vendite`, 10 in `script`, 7 in `dbops`), **diciannove documenti chiusi in
> `work-done`** e **37 merge** (dalla PR #1589 alla #1625). Si scrive per
> **temi**: sono nove.
>
> ⚠️ Il **16 settembre** non ha prodotto né changeSet né commit, e il **20
> settembre** è volutamente fuori: la revisione delle guide di
> `docs/it/guide/` era in corso mentre questa voce veniva scritta.
>
> ⭐ **Il tema portante è il collaudo in-app che scrive le regole.** Il copione
> del giro incassi nasce il 14 settembre come lista di cose da spuntare; in
> questi cinque giorni diventa **tre giri e venti decisioni di dominio**
> (D16…D20) — e in più di un caso aveva ragione la schermata: il modello
> c'era, era l'interfaccia a dire il contrario. È la lezione della voce
> precedente dal verso opposto: *i presidi si provano dal percorso che li
> attraversa, e le regole si provano dalla schermata che le mostra*.

**Anello 0 — «Esegui ora» entra in esercizio, «Riavvia» aspetta di sapere che
cosa è un host.** Far partire un processo dall'interfaccia si consegna il **15
settembre** con **tre celle di CSV e nessun changeSet**: `dbops.processi`
dichiara `avvio_manuale`, `coda_lavori_tipi` prende `ESEGUI_PROCESSO` attivo,
`config.azioni_processo` l'azione `processo_avvia`; lato BE `avvio_manuale.py`
è la **sede unica** del predicato (capability, endpoint e handler lo leggono da
lì) e il FE monta il tab «Sveglie» nel `ProcessoDrawer` col motivo dell'azione
spenta. Collaudo in-app lo stesso giorno: due run `origine = COMMAND` sul
giornale, email `SENT` e ricevute. ⭐ **Il discriminante è che cosa serve
sapere**: «Esegui ora» non ha bisogno di sapere *su quale macchina* gira — un
timer è un comando che parla col DB — mentre un `systemctl restart` **sì**, e
senza un *host* nel modello il pulsante riavvia «un host a caso» alla seconda
macchina, in silenzio. ⇒ «Riavvia» resta dietro **D1** (forma A: nome
dichiarato in `env.sh`, `host` obbligatorio nella richiesta, claim del
drenatore filtrato), **zero righe scritte per scelta**: è fra le «Decisioni
aperte» della mappa. Vedi
[brief-db-avvio-manuale-di-un-processo.md](work-done/brief-db-avvio-manuale-di-un-processo.md),
[piano-be-fe-avvio-manuale-di-un-processo.md](work-done/piano-be-fe-avvio-manuale-di-un-processo.md),
[analisi-riavvio-processi-da-interfaccia.md](work-done/analisi-riavvio-processi-da-interfaccia.md).

**Anello 3 (`magazzino`) — Il terreno vuoto, e il giorno dopo il motore.** Il
**Lotto 1** atterra il 15-09: 26 changeSet che danno al registro `movimenti` la
**sorgente obbligatoria a catalogo** e il **verso nella quantità**
(`trgfn_movimenti_guard_verso`), `movimenti_attesi` al posto di `reservations`,
`valore_giacenza` al posto di `costo_medio`, `lotti` nuova, l'**emittente come
ancora** su `magazzini`/`assets` — più 23 policy RLS, cinque viste
`security_invoker` e cinque pgTAP. Merge PR #1593, BE/FE PR #1595, CI verde
dalle 16:45. ⚠️ **La sera ha insegnato più della scrittura**: sette cose erano
verdi in sessione **per ragioni sbagliate**, e le ha trovate solo il database
ricostruito da zero — la lista è in coda a §5, ed è il punto di partenza
dichiarato del Lotto 2. Il **Lotto 2** («il motore», brief del 17-09 con
**quattordici decisioni** prese da Tid) è applicato su dbdev il **18-09 alle
12:23**: la **porta** `magazzino.fn_scrivi_movimento` (`SECURITY DEFINER`:
unica scrittura del registro, copia del valore, lock in uscita, disponibilità),
il `REVOKE` all'app su `movimenti`/`valore_giacenza` in **tre sedi**, inventario
e rettifica postati dalla porta, `vw_disponibilita`, quattro spie in
`dbops.presidi`, 27 codici `E_MAG_*`, 21 changeSet e dodici pgTAP. ⚠️ Aperto:
pgTAP come applicazione, CI da zero, commit; `requires_lotto` nel drawer
articolo e le operazioni BE/FE. Vedi
[brief-db-magazzino-lotto-1-terreno-vuoto.md](work-done/brief-db-magazzino-lotto-1-terreno-vuoto.md),
[brief-db-magazzino-lotto-2-motore.md](work-done/brief-db-magazzino-lotto-2-motore.md).

**Anello 0 — Quando nasce un building block, le copie si ritirano nello stesso
giro.** L'emittente di default diventa **una funzione sola** in `script`
(`trgfn_default_emittente_fiscale`, undici changeSet, `20260915-36 → -46`)
montata su **undici** tabelle: le **quattro copie di `vendite` sono ritirate**,
tre codici errore ritirati, zero copie in `pg_proc` a database vivo, e il BE
allinea con `E_EMITTENTE_NON_RISOLTO`. La raccomandazione «il BB ora, le copie
quando c'è tempo» è stata **respinta**, e con una ragione che vale come regola:
*non c'è produzione, non c'è niente da aspettare* — un refactor rimandato è un
debito che nessuno rilegge. ⭐ Nello stesso periodo, due BB estratti alla
**seconda** occorrenza: `core/db.sql_lateral_primo_motivo` e
`pagamenti/composables/useAzioniRigaContabile`. Vedi
[brief-db-emittente-di-default-un-bb-solo.md](work-done/brief-db-emittente-di-default-un-bb-solo.md).

### Incassi e distinte — 19 settembre

**Anello 3 (`pagamenti`) — Il collaudo in-app scrive venti decisioni di
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

**Anello 3 (`pagamenti`) — La distinta prende il numero dal registro, e impara
a cercare le rate.** Chiesto da Tid il 15-09: la distinta contabile aveva un
`codice` da `DEFAULT` di colonna, non un numero. Il **motore non si tocca** —
cinque famiglie ci passano già — quello che cambia è **la distinta**, che
diventa `DIS-<sigla>-<anno>-<7 cifre>` e per farlo deve dire **di quale
emittente è** (D1), con la RLS che passa sulla colonna emittente della riga
(D3); ✏️ *il primo numero è uscito a video* il 17-09. Il seguito arriva da un
rilievo del giro in-app dello stesso giorno, e vale come regola: *chi digita un
incasso non riconosce il documento da un numero nudo, e la domanda vera non è
«quale fattura?» ma «quale rata?»* — il lookup fattura diventa **ricco**, nasce
la **lista rate paginata** (primo consumatore dello scadenzario) e la **modalità
multipla** che accumula N rate e genera N righe al salvataggio. ⚠️ Due cose
restano, con destinazione scritta: la **scala di `importo`** (P-8: `numeric`
senza scala, quindi un `CHECK` che **rifiuta** — deciso il 18-09), e il
**`runOnChange` + `dbms:`**, che in Liquibase 5.0.4 fa ri-eseguire il change
**una volta** e il checksum non torna: è così che `20260831-03` è morto dopo il
merge di PR #1598, e i 28 changeSet interessati sono una voce aperta in
`PROJECT_CONTEXT.md`. Vedi
[brief-db-distinta-numerata-sul-registro.md](work-done/brief-db-distinta-numerata-sul-registro.md),
[brief-db-distinta-ricerca-rate.md](work-done/brief-db-distinta-ricerca-rate.md).

### Interfaccia, osservabilità e verifiche — 19 settembre

**Anello 1 (`ui`) — Il perimetro emittente arriva ai cataloghi globali, e il
seed laterale si ritira.** Sei liste in più dichiarate `perimetro_emittente =
false`: con «Tutti gli emittenti» nella combo, *Processi automatici* era
sbarrata dal cancello di perimetro su un registro che **un emittente non ce
l'ha**. Sette globali rientrano, `operatori` e `lista_preset` vengono
certificate `multi_emittente` (colonne 872/873 a catalogo), `list_logs`
proietta la ragione sociale, e il presidio BE tiene i due versi. ⛔ **La
decisione di metodo vale più delle righe**: il valore **non** sta in un CSV
laterale — «il rischio è troppo, si rischia disallineamento con i csv» — ma
nella **colonna** di `lista_definizione.csv`, come `multi_emittente`; il
laterale `20260902-02` è **ritirato** insieme al meccanismo, e l'ordine
**colonna → flag** è scritto nel pgTAP, dove chi accende il flag deve venire a
dichiararlo. Vedi
[brief-db-perimetro-emittente-cataloghi-globali.md](work-done/brief-db-perimetro-emittente-cataloghi-globali.md).

**Anello 0 — Osservabilità: l'ultimo miglio, e il pallino in topbar.** I sette
passi dell'analisi arrivano a codice nello stesso giorno in cui l'analisi si
chiude: `error_log` consultabile dietro permesso (**E**, «Errori tecnici»), il
**Giornale eventi** (**G**), la retention (**D**) e il **pallino dei presidi**
in topbar (**P**). ⭐ Il pezzo che vale più degli altri è il **verdetto «lotto
fermo»**, che smette di vivere in Python e **nasce a DB**: un presidio scritto
a mano sarebbe stata la **seconda sede** dello stesso predicato, quindi si
sposta la sede, non si copia — con la finestra dichiarata finché il BE non
legge il dato nuovo. Con R-6 (una riga `TASK_RUN` che usciva col giorno del
task successivo) e i due indici delle letture trasversali. ⚠️ **Due rossi in CI
la sera del 19-09**, entrambi presidi che hanno funzionato: la lista
`dbops.error_log` entrata nel CSV globale senza dichiararsi nell'elenco del
pgTAP, e un `SELECT` su `maintenance.job_run_log` che esisteva **solo su dev** —
emerso perché i test Django girano ora **come l'applicazione**. Da lì la quarta
occorrenza di *un privilegio che esiste su una macchina è un ricordo*, chiusa
con un blocco in `provision_db_roles.sql` e un pgTAP di postura; 🔴 e resta
aperto, con la sua riga in `PROJECT_CONTEXT.md`, che `zeroerp_log` in CI **non
ha `USAGE` su `dbops`**: ogni test Django lavora con `tx_id = uuid_nil` (16 114
righe `permission denied` nella corsa verde), due strade e la decisione a Tid.
Vedi [analisi-osservabilita-log.md](work-done/analisi-osservabilita-log.md),
[piano-be-fe-osservabilita-pallino-e-superfici.md](work-done/piano-be-fe-osservabilita-pallino-e-superfici.md),
[brief-db-osservabilita-lotto-fermo-r6-indici.md](work-done/brief-db-osservabilita-lotto-fermo-r6-indici.md),
[brief-db-privilegio-app-job-run-log.md](work-done/brief-db-privilegio-app-job-run-log.md).

**Anello 0 — La catena di verifica: D7 chiuso, e due analisi che si chiudono
invece di rimisurare.** **D7** finisce il 19-09: i 21 file del perimetro non
*ricercano* più il mondo nella fixture, lo **costruiscono**
(`dbops.fn_pgtap_crea_emittente_operatore`), e i loro rientrati li toglie
`scripts/pgtap-baseline-ci-rientrati.sh` leggendo il log della corsa, non una
mano — 363 → 362 rossi sul database ricostruito da zero. Il pezzo nuovo di
**D6** ha il suo brief (`sec_functions_owner` e la sync riservati al migratore).
Sullo stesso asse, due analisi si chiudono **senza aprire cantieri**: i
**presidi del percorso storto** — C3 e C4 li ha chiusi il lavoro ordinario, C1 e
C2 hanno un brief di mezza pagina — e la **diagnostica di produzione senza
accesso al DB**, **archiviata senza costruire**, perché una produzione da
diagnosticare oggi non esiste. ⭐ Le due lezioni sono la stessa: *i presidi del
percorso storto non nascono da soli — un'analisi non li sostituisce, li
sostituisce un brief*; e *un'analisi che aspetta una validazione senza data
invecchia senza dirlo*. Le sei domande della diagnostica restano come
**decisione** e non come lavoro, fra le «Decisioni aperte» della mappa. Vedi
[brief-db-fixture-che-costruiscono-d7-d6-d4.md](work-done/brief-db-fixture-che-costruiscono-d7-d6-d4.md),
[analisi-presidi-percorso-storto.md](work-done/analisi-presidi-percorso-storto.md),
[brief-db-registro-owner-e-sync-riservati-al-migratore.md](work-done/brief-db-registro-owner-e-sync-riservati-al-migratore.md),
[analisi-diagnostica-produzione-senza-accesso-db.md](work-done/analisi-diagnostica-produzione-senza-accesso-db.md).

**Anello 1 (`ui`) — Il frontend: le classi che non esistevano, e il chrome che
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

**In breve, senza un tema proprio** — la **revisione delle guide** di
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

---

## 14 settembre 2026

> Copre il periodo **11 – 14 settembre**. Quattro giorni, **103 changeSet**
> (25 in `dbops`, 23 in `vendite`, 10 in `anagrafiche`, 8 in `script`, 4 in
> `storico`) e **undici documenti chiusi in `work-done`**. Anche qui si scrive
> per **temi**: sono sei.
>
> ⚠️ Due brief di questo periodo restano in `work-in-progress` per scelta, non
> per incompiutezza: quello delle **modifiche certe** ha un fatto di modello
> dichiarato e non deciso (il verbo per la promessa di consegna), e quello delle
> **fixture che costruiscono il mondo** tiene in coda il pezzo nuovo di D6.
> Sono linkati dove stanno.
>
> ⭐ **Il tema portante è ancora la CATENA DI VERIFICA, ma stavolta dal verso
> dei presidi che si guardano allo specchio.** Il 10 settembre i presidi avevano
> ricevuto un catalogo e un destinatario; in questi quattro giorni **tre di loro
> hanno mentito** — il digest contava 784 riferimenti morti che non c'erano, un
> listener vivo risultava `MUTO`, un checker dava una risposta diversa per ruolo
> — e in tutti e tre i casi la causa stava nel **metro**, non nel misurato. È
> il motivo per cui la lezione che resta non è «un presidio in più» ma *un
> presidio si prova dal percorso che lo attraversa*.

**Anello 0 — Lo storico porta il proprio perimetro, e il perimetro finisce di
chiudersi.** Il cantiere del perimetro si chiude formalmente l'11 settembre con
l'ultima famiglia armata (`arrotondamenti_scope`) e un ritiro
(`attivita_fatturabili_log`): registro del debito da 33 a **10** righe, tutte
decisioni di modello o cantieri di un altro dominio. Ma il criterio transitivo
**non vede lo `storico`** — le shadow sono gemelle delle madri, non figlie — e
lì il dato vivo di `vendite.fatture` era protetto da due policy mentre **ogni
sua versione precedente era leggibile da chiunque**. La decisione portante è che
lo scope **si cattura, non si deriva**: una riga di storico è un fatto datato,
e il suo perimetro fa parte del fatto — se si ricalcolasse dalla madre viva, il
presente riscriverebbe la visibilità del passato. Ogni shadow prende
`origine_schema` (cinque shadow erano **condivise** fra `vendite` e `acquisti`
senza saperlo: due `BIGSERIAL` nella stessa colonna, e la chiusura dello
snapshot chiudeva quello dell'altro schema) e `scope_emittente_fiscale_id`,
scritti dal trigger una volta sola; la mappa `dbops.storico_scope_policy` dice
per ogni madre *dove* sta lo scope (colonna EF, colonna SR, risalita al padre —
con **ripiego sull'archivio del padre** quando un `DELETE … CASCADE` l'ha già
cancellato — o via billing account), ed è anche il presidio. **37 shadow armate**
con policy generata, 65.751 versioni attribuite, `REVOKE DELETE` all'app su
tutto lo schema, e le shadow nuove nascono armate dal generatore. ⭐
`dbops.audit_log` era la stessa famiglia di difetto e un rimedio **diverso**:
non è un registro di dominio (ci scrivono solo `dbops` e `maintenance`), quindi
il presidio non è una policy ma un **cancello** alla scrittura, più il `REVOKE`
di `UPDATE`/`DELETE` all'app dichiarato nel loop dei grant — *un registro di
audit modificabile da chi è auditato non è un registro*. Nello stesso giro
`shop.ricevute` viene armata (12-09, il debito scende a **8**), il benchmark RLS
«pre/post ENABLE» viene ritirato dalla documentazione perché sbagliato nella
premessa (la canonica è plpgsql: il predicato non è indicizzabile), e il 13-09
cade **D13**: come `zeroerp_app`, l'operatore di un emittente **non di default**
non riusciva a creare un billing account, perché il `RETURNING` chiedeva di
vedere la riga *prima* che il trigger `AFTER` scrivesse il legame e il resolver
ricadeva su un'altra azienda. Ora *un BA non ancora collegato appartiene a chi
lo sta creando* — riserva a tre livelli, e la seconda copia della regola
(`fn_get_emittente_fiscale_pk`) delega; lato BE le tre copie inline della regola
vecchia delegano a `fn_check_ba_visible_for_emittenti`. Vedi
[brief-db-perimetro-emittente-righe-documento.md](work-done/brief-db-perimetro-emittente-righe-documento.md) §12,
[brief-db-rls-storico-scope-congelato.md](work-done/brief-db-rls-storico-scope-congelato.md),
[brief-db-ba-riserva-emittente-operatore-d13.md](work-done/brief-db-ba-riserva-emittente-operatore-d13.md).

**Anello 0 — I processi automatici hanno un contratto di vitalità.** Dei sei
processi che il backend dichiara di svegliare, due avevano un presidio che si
accorge se smettono di girare; gli altri quattro no — e `send_pending_emails`,
che gira ogni cinque minuti, era rimasto **non installato** senza che nessuno se
ne accorgesse. *Il discriminante non è «ogni quanto gira»: è «qualcuno aspetta
l'esito, e in quanto tempo se ne accorge?»*. La tolleranza diventa un dato di
catalogo (`dbops.processi.tolleranza_minuti`, che esce da `sveglie.json`), il
panorama dice `MUTO` e `MAI_PARTITO`, il listener si presidia dalla **sessione**
(`pg_stat_activity` + `application_name`, un fatto e non una dichiarazione), le
email e la coda stampa hanno la loro vista `ZERO`, e un **guardiano pgAgent**
accoda su `coda_lavori` la notifica se il digest stesso tace — *chi guarda il
guardiano*. ⚠️ Il primo digest utile (14-09) ha contato un `MUTO` su un listener
**vivo**: `pg_stat_activity` maschera `backend_start` a chi non è lo stesso
utente della sessione, e il pgTAP non poteva vederlo perché usava la propria
sessione. Corretto leggendo l'**esistenza** della riga, che è visibile a
chiunque, con un test che costruisce la sessione altrui via `dblink`. Sullo
stesso asse, «una mail stampata a video non è una mail inviata»: il digest era
stato dichiarato `SENT` su un host col placeholder SMTP del seed, e ora esiste lo
stato `SIMULATA` (terminale e voluto), con `inviato_at` a NULL. E il cantiere dei
presidi si chiude scoprendo che **il presidio dei presidi mentiva**: 784
riferimenti morti nel digest contro zero nella lettura diretta, perché la
funzione ereditava il `search_path` blindato della `DEFINER` che la chiamava e
non risolveva più `plpgsql_check` in `public` — *una funzione che dipende dal
`search_path` del chiamante non ha un comportamento, ne ha uno per chiamante*.
Il primo settimanale (14-09) ne ha trovato un terzo: il checker dava una
risposta **per ruolo** su una `SECURITY DEFINER` di un altro proprietario
(ottava classe `FP_DEFINER_PRIVILEGIO`, e l'esenzione pgAgent del registro
**segue la macchina**). ⚠️ Nel working tree del 14-09, non ancora consolidato:
`job_liveness` del backend prendeva l'esito dalla riga più recente — cioè dalla
propria corsa in esecuzione — e `last_ok` è sostituito da `in_corso` +
`ultima_conclusa` nelle tre sedi. Aperto: far partire o riavviare un processo
**dall'interfaccia** — «Esegui ora» passa dalla coda e non aspetta l'host, il
brief DB è scritto; «Riavvia» resta dietro la decisione su che cosa sia un host.
✅ *Aggiornamento*: «Esegui ora» è **in esercizio dal 15-09** e l'analisi è
archiviata — il seguito, con la **D1**, sta nella voce del **19 settembre**.
Vedi
[brief-db-quattro-processi-senza-presidio.md](work-done/brief-db-quattro-processi-senza-presidio.md),
[brief-db-stato-email-console-non-e-inviata.md](work-done/brief-db-stato-email-console-non-e-inviata.md),
[brief-db-un-destinatario-per-i-presidi.md](work-done/brief-db-un-destinatario-per-i-presidi.md) §13-§14,
[analisi-riavvio-processi-da-interfaccia.md](work-done/analisi-riavvio-processi-da-interfaccia.md),
[brief-db-avvio-manuale-di-un-processo.md](work-done/brief-db-avvio-manuale-di-un-processo.md).

### Dati non più usati e postura degli oggetti — 14 settembre

**Anello 0 + 1 — Il software che serviva dati morti.** Nato dalla coda del
cantiere dello storico, dove si stava per scrivere codice che mostrasse la
storia di una tabella già dismessa: la domanda diventa *c'è software in
servizio il cui unico lavoro è tenere in vita dati — o nomi — che il modello ha
già lasciato?* Otto voci, tutte chiuse il 12-09: la vista col nome vecchio
`anagrafiche.risorse_umane_auth_user` (una proiezione filtrata su `OPERATORE`
che rispondeva **zero righe** in silenzio su un'identità portale) ritirata con i
lettori DB riscritti sulla **madre** `identita_digitali` e un guard scritto a
mano; le shadow legacy droppate; `dbops._defaults_backup_usercols` e
`public.version_info` **droppate** (la seconda in due giri: nata nel
provisioning come `postgres`, si ritira nel provisioning — *ciò che nasce nel
provisioning si ritira nel provisioning*); l'alias «deprecato»
`get_emittenti_ids` con nove chiamanti, due ripieghi su forme di `meta` che
nessuno scrive più, e `isAdmin` sul frontend. ⛔ La lezione: *«tenere per
sicurezza» è la forma da cui ogni voce di quell'elenco è nata*, e il precedente
mostra dove porta — a un endpoint a 500 e a una policy scritta per sei righe di
test. ⭐ Il giorno dopo la CI ha detto due cose che lo scratch locale non poteva
vedere: le 15 shadow create a mano in `00_schema` nascevano senza
`origine_schema` su un DB da zero (convergenza in `ci_apply`), e sotto c'era una
**seconda causa, non di oggi**: `zeroerp_app` non aveva nessuna sede che gli
desse `django.auth_user` — su dev il GRANT era **dato a mano**, e lo scratch
copiava le ACL di dev insieme allo schema. *Un privilegio che esiste su una
macchina è un ricordo, non una configurazione*: lo schema `django` entra nel
provisioning, il passo in CI si sposta dopo entrambi i migratori, e un pgTAP
pinna la postura. Vedi
[analisi-software-per-dati-morti.md](work-done/analisi-software-per-dati-morti.md).

**Anello 0 — La postura degli oggetti si presidia per criterio, e il registro
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

### Vendite e articoli — 14 settembre

**Anello 3 (vendite) — Il rilancio rivede le proprie commesse.** Trovato dal
collaudo in-app dell'esito parziale, prova 5: ripristinate le ROOT, «Riprova
step» portava il lotto a `COMPLETATO` **senza emettere niente**, perché la
discovery scartava le commesse `TRATTENUTA` — anche quando a trattenerle era il
lotto stesso che stava riprovando. L'auto-esclusione esisteva, ma solo
nell'emit, un cancello più a valle che non veniva mai raggiunto. La parte comune
ai due predicati ha ora **una sede** (`fn_classe_emittibilita_per_giro`, SQL
`IMMUTABLE` che il planner inlina: *una riga trattenuta soltanto dal mio giro,
per il mio giro è pronta*), e gli esiti `ERRORE` **contano nel verdetto** del
lotto. ⭐ Sotto c'era un **secondo difetto**, nell'orchestratore: i task a valle
del pull erano `COMPLETATO` a vuoto e il resolver li saltava come «già fatti»
su un input appena cambiato — *a valle di un task eseguito in questo giro nessun
task si salta*; `RESUME_STEP` era una distinzione senza differenza ed è ritirato.
E sotto ancora: `fn_cleanup_fatture_by_ids` usciva su «zero fatture» e non
liberava **nessuna** attività di un lotto fermo prima della generazione. Il
collaudo chiude verde, e con lui la linea del fan-out **per intero**. Nello
stesso giro `ANNULLATA` prende `applica_lotto` (il catalogo diceva il falso), e
la **roadmap fatturazione** viene archiviata: tre riverifiche in fila avevano
aggiunto un blocco senza togliere il precedente, e il documento si leggeva a
quattro date sovrapposte — lo stato delle voci aperte vive ora in una riga
ciascuna in `PROJECT_CONTEXT.md`. Vedi
[brief-db-rilancio-step-non-rivede-le-proprie-commesse.md](work-done/brief-db-rilancio-step-non-rivede-le-proprie-commesse.md),
[collaudo-in-app-esito-parziale-pull-commessa.md](work-done/collaudo-in-app-esito-parziale-pull-commessa.md),
[brief-be-fan-out-isolato-e-esito-parziale.md](work-done/brief-be-fan-out-isolato-e-esito-parziale.md),
[fatturazione-roadmap.md](work-done/fatturazione-roadmap.md).

**Anello 1 + 3 — L'articolo dice da dove arriva, la riga d'ordine sa quando, la
commessa si legge.** Tre buchi del modello, tutti *certi* perché nessuna delle
decisioni aperte su magazzino e produzione li cambia — ed è il filtro che ha
prodotto il brief: fra due analisi contigue (commessa/produzione e magazzino) si
è estratto ciò che vale in qualunque esito. **Blocco A**: non esisteva alcuna
data di consegna in tutto il database — `vendite.ordini_righe` e
`acquisti.ordini_righe` prendono richiesta e conferma (con la convenzione dei
nomi *non marcato = nostro, marcato = della controparte*), `preventivi_righe` la
sola richiesta, che il push porta sull'ordine; niente CHECK fra le due date e
niente colonna di testata (il `min` lo dà la vista di lista); il **ritardo** vive
in `vw_situazione_merce_ordine`, dove c'è già il residuo, e distingue «in tempo»
da «niente da spedire». **Blocco B**: nasce il vocabolario
`config.modi_approvvigionamento` (acquisto / produzione / stock / non
applicabile) e `catalogo.articoli` prende `modo_approvvigionamento_id`,
`gestito_a_magazzino` (default fail-safe `false`) e `lead_time_giorni` — è il
perno da cui partiranno acquisti e magazzino, il prossimo cantiere. **Blocco C**:
`vendite.commesse` ha `descrizione`, `data_apertura` e un responsabile che è una
**risorsa umana**, come in `pratiche`; `PATCH /commesse/<id>/` e un lookup
dedicato `GET /anagrafiche/risorse-umane/lookup/`. **B-bis**:
`famiglie_documento.colonna_billing_account` diventa facoltativa come
`colonna_serie` — la porta per il primo documento senza cliente, l'ordine di
acquisto. ⭐ Due cose emerse facendolo: il `DEFAULT` di una colonna che punta a
un seed di `80_data` (o a una funzione che lo legge) **non può stare in
`00_schema`** — tre passi, come `natura_vendita_id`; e `E_ATTIVO_REQUIRE`, il
codice del require generato dal framework ATTIVO, è **TECNICO** anche quando il
dato sbagliato l'ha scelto una persona — il service pre-verifica e risponde 400,
candidato allo split. ⚠️ Dichiarato e non deciso: le righe d'ordine si scrivono
solo in `DRAFT`, ma la promessa di consegna si decide alla conferma — serve un
verbo suo. ⚠️ E `fn_crea_revisione_preventivo` non copia la data richiesta sulla
nuova revisione. Vedi
[brief-db-modifiche-certe-ciclo-vendita-e-articolo.md](work-done/brief-db-modifiche-certe-ciclo-vendita-e-articolo.md),
§5.5 e §10.

**In breve, senza un tema proprio** — la **copertura della doc API** rimisurata
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

---

## 10 settembre 2026

> Copre il periodo **31 agosto – 10 settembre**. Undici giorni, **384 changeSet**
> nuovi (175 in `vendite`, 60 in `dbops`, 58 in `script`) e **46 brief chiusi**
> — il ritmo più alto finora. Anche qui si scrive per **temi**: sono otto.
>
> ⚠️ **L'11 settembre è volutamente fuori**, per la stessa ragione del 31 agosto
> nella voce precedente: quel giorno era in corso mentre questa voce veniva
> scritta. Ciò che è atterrato l'11 — la chiusura formale del cantiere del
> perimetro e due slice piccole — entra nella voce successiva.
>
> ⭐ **Il tema portante non è un dominio, è la CATENA DI VERIFICA.** Quattro degli
> otto temi qui sotto riguardano *come si sa che una cosa è vera*: la CI che
> misura davvero, i presidi che hanno un catalogo, il perimetro dei dati che ha
> un criterio invece di un elenco, e i motivi d'errore che escono da un posto
> solo. Il resto del periodo poggia su quelli.

**Anello 0 — I pgTAP misurano davvero, e la CI misura la CI.** La suite era un
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

**Anello 0 — I presidi hanno un catalogo, e un contatore che non mente.** I
presidi del progetto erano una ventina di file che nessun elenco teneva insieme:
per sapere *quanti sono e cosa coprono* bisognava cercarli. Nasce `dbops.presidi`
— il catalogo — con **il contatore onesto**: un presidio che non ha mai girato non
conta come copertura. Il 10 settembre arriva il corollario in CI: *un cancello non
deve poter zittire un altro cancello*, perché un guardrail che fallisce e ne
maschera un secondo lascia passare due difetti al prezzo di uno. Vedi
[brief-db-un-destinatario-per-i-presidi.md](work-done/brief-db-un-destinatario-per-i-presidi.md).

**Anello 0 + 3 — Il perimetro dei dati smette di fermarsi alla testata.** Delle
sei famiglie di documento di `vendite`, **una sola** era protetta fino in fondo:
le righe delle altre cinque erano leggibili da qualunque operatore, e non per
dimenticanza — perché il perimetro era stato scritto come **elenco a mano**, e un
elenco ha per confine ciò che chi lo scriveva aveva in mente. Il cantiere (9 → 11
settembre) arma **nove famiglie**, ritira una tabella residua, e soprattutto
sostituisce l'elenco con un **criterio transitivo**: `dbops.vw_rls_perimetro_scoperto`
più il registro `dbops.rls_perimetro_debito` vedono *ogni* tabella con una FK
verso una protetta, comprese quelle che nasceranno domani. Il debito passa da
**33 a 10 righe**, e le dieci che restano sono decisioni di modello dichiarate,
non lavoro rimandato. ⭐ Nello stesso giro il contesto RLS dei test esce da
venti copie e trova una sede sola (`apri_contesto_operatore`). Vedi
[brief-db-perimetro-emittente-righe-documento.md](work-done/brief-db-perimetro-emittente-righe-documento.md),
[brief-db-viste-security-invoker-criterio.md](work-done/brief-db-viste-security-invoker-criterio.md).

**Anello 0 — I processi automatici hanno un'identità e un perimetro.** I job che
girano da soli — sveglie, code, pipeline — entravano nel database senza dire *chi
sono*: nessuna identità applicativa, quindi nessun perimetro da rispettare e
nessuna riga di log che sapesse attribuirli. Il cantiere (4 → 7 settembre) dà a
ogni processo del backend un **artefatto di deploy** e un'identità, e chiude i
residui lato BE. ⇒ Da qui un processo automatico è un attore come gli altri,
soggetto alle stesse regole. Vedi
[brief-db-processi-automatici-identita-e-perimetro.md](work-done/brief-db-processi-automatici-identita-e-perimetro.md),
[brief-db-sveglia-dei-processi.md](work-done/brief-db-sveglia-dei-processi.md),
[brief-db-processi-automatici-residui-be.md](work-done/brief-db-processi-automatici-residui-be.md),
[piano-be-fe-processi-automatici-identita-e-perimetro.md](work-done/piano-be-fe-processi-automatici-identita-e-perimetro.md).

**Anello 3 (vendite) — Un documento rotto non tiene più in ostaggio il giro di
fatturazione.** Un lotto che incontrava un documento non emettibile si fermava, e
con lui tutti gli altri documenti di quel giro: il difetto di uno diventava il
blocco di tutti. Il tema si apre in tre tempi — **l'uscita dal giro** (un
documento può uscire e il lotto prosegue), **il trattenuto** (una sede sola per la
domanda *«questa riga può entrare in un giro?»*, invece della stessa condizione
riscritta in più punti) e **il marcatore**, che non scrive più su un documento già
uscito. ⭐ La lezione che resta: *una condizione scritta in tre posti diverge, e
diverge in silenzio*. Vedi
[brief-db-uscita-documento-dal-giro.md](work-done/brief-db-uscita-documento-dal-giro.md),
[brief-db-documento-trattenuto-da-un-lotto-vivo.md](work-done/brief-db-documento-trattenuto-da-un-lotto-vivo.md),
[brief-db-il-trattenuto-passa-lo-stesso.md](work-done/brief-db-il-trattenuto-passa-lo-stesso.md),
[brief-db-il-marcatore-scrive-su-un-documento-uscito.md](work-done/brief-db-il-marcatore-scrive-su-un-documento-uscito.md).

**Anello 3 (vendite) — L'esito di un documento nel lotto ha casa propria.**
L'esito di ogni documento dentro un giro si deduceva dagli stati altrui, e sui
giri di massa la deduzione non reggeva. Ora è un dato, con la sua sede, e vale
anche per i giri massivi; la **segnalazione di un lotto dichiara di quale
documento parla**, invece di lasciarlo capire. Chiusi anche due residui di
performance (la `LATERAL` costosa sul riferimento gruppi) e le bandiere
dell'esito parziale. Vedi
[brief-db-esito-gruppo-lotto.md](work-done/brief-db-esito-gruppo-lotto.md),
[brief-be-db-gruppo-key-sulle-segnalazioni.md](work-done/brief-be-db-gruppo-key-sulle-segnalazioni.md),
[brief-residuo-fatturabili-e-bandiere-esito-parziale.md](work-done/brief-residuo-fatturabili-e-bandiere-esito-parziale.md).

**Anello 0 — Il primo motivo di un controllo esce da un posto solo.** Le funzioni
`script.fn_check_*` producono un array di motivi, e chi doveva sollevarne il primo
ricopiava la stessa coda di codice — tredici volte, con tredici occasioni di
divergere. Nasce `script.fn_raise_primo_motivo_se_presente`, e la regola che
decide è una riga: *il codice che sollevo lo sto **leggendo** da un array o lo sto
**scrivendo** come letterale?* ⭐ Sbagliare funzione **non compila** — i tipi non
legano — quindi l'unico modo di sbagliare è non usarla, e quello ha il suo
presidio. Vedi
[brief-db-coda-primo-motivo-in-un-posto-solo.md](work-done/brief-db-coda-primo-motivo-in-un-posto-solo.md),
[brief-db-i-motivi-si-fermano-dentro-la-check.md](work-done/brief-db-i-motivi-si-fermano-dentro-la-check.md).

**Anello 1 + 3 — La numerazione finisce il trasloco, e l'IVA arriva ai
consumatori.** Il 31 agosto atterra l'esecuzione decisa il giorno prima: la
commessa passa **sui registri**, con il prefisso e l'allineamento dei contatori, e
la chiave del contatore diventa esplicita. ⇒ La voce «il trasloco sui registri»
esce dalla roadmap: **è fatta**, CRUD dei registri compreso — che era anche una
voce dei «Previsti». Nello stesso periodo il risolutore IVA arriva ai suoi
consumatori applicativi (fase 3), i titoli IVA del soggetto prendono i movimenti
di annullo, e il default IVA smette di dipendere da un id di seed per passare a
una **chiave naturale**. Vedi
[brief-db-registri-di-numerazione-emittente-e-trasloco.md](work-done/brief-db-registri-di-numerazione-emittente-e-trasloco.md),
[brief-db-registri-numerazione-chiave-del-contatore.md](work-done/brief-db-registri-numerazione-chiave-del-contatore.md),
[brief-be-fe-crud-registri-di-numerazione.md](work-done/brief-be-fe-crud-registri-di-numerazione.md),
[brief-be-fe-iva-fase-3-consumatori-risolutore.md](work-done/brief-be-fe-iva-fase-3-consumatori-risolutore.md),
[brief-db-default-iva-chiave-naturale.md](work-done/brief-db-default-iva-chiave-naturale.md).

**In breve, senza un tema proprio** — il **fondo fattura** con ricalcolo e governo
applicato il 31 agosto; l'**archiviazione delle righe di coda** e la
storicizzazione dei bersagli spariti; il **perimetro delle email** e l'invio di
sistema; i **riferimenti contratto** sugli atti di fattura; tre giri di **seed
liste** (lotto, titolo IVA, admin `ui`); due **design** che preparano il magazzino
— la partita merce generalizzata e la situazione merce di un ordine; e la
migrazione della clausola `ORDER BY` lato backend.

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
> fondo fattura — sta nella voce del 10 settembre.

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
del giorno dopo (voce del 10 settembre). Vedi
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
la voce del 19 settembre. Vedi
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
settembre si prenderà due lezioni, voce del 14 settembre). Vedi [brief-db-bonifica-riferimenti-morti.md](work-done/brief-db-bonifica-riferimenti-morti.md),
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
