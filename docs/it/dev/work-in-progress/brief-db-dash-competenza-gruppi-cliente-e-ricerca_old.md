# Brief DB — gruppi fatturabili: identificare e isolare il cliente

> **Tipo**: brief al team DB · **Data**: 2026-08-17 · **Richiedente**: Tid ·
> **Destinazione**: `dev/db-tid` · **Stato**: da valutare, nulla eseguito
>
> **Oggetto**: la lista **gruppi fatturabili** della dashboard Competenza
> (`vendite.vw_dash_competenza_gruppi`, lista configurabile
> `vendite.dash_competenza_gruppi`) deve permettere di **isolare un cliente** e
> di **riconoscerlo senza ambiguità**.
>
> Questo brief dice **cosa serve e perché**, non come farlo: la soluzione — se
> vista, dove, con quali indici, con quale forma di filtro — la decide il team
> DB.

---

## 1. Perché nasce

Sulla dashboard Competenza l'operatore spunta dei **gruppi fatturabili** e preme
«Fattura selezionati». Tutti i gruppi di una stessa selezione finiscono in **un
solo giro**, e lì il database li aggrega: i gruppi dello stesso cliente
confluiscono sulla **stessa fattura**.

Il 2026-08-17 è stata valutata e **scartata** l'ipotesi di spezzare la selezione
in un job per gruppo, proprio perché avrebbe fatto perdere quell'aggregazione
(giri diversi ⇒ lotti diversi ⇒ fatture diverse). Decisione registrata in
`brief-fe-fatturazione-job-concorrenti.md` §9 (D5).

**Il corollario è questo brief.** Se per avere righe sulla stessa fattura devono
stare nella **stessa selezione**, allora comporre quella selezione dev'essere
facile. Oggi non lo è: la lista si può filtrare solo per tipo di documento, e
per raccogliere «tutto di un cliente» bisogna scorrere le pagine a occhio
leggendo la ragione sociale. Su un mese popolato è un lavoro di pazienza in cui
è facile dimenticare una riga — e la riga dimenticata non dà errore, diventa
semplicemente una seconda fattura allo stesso cliente.

## 2. Situazione di partenza (per non farvela cercare)

`vendite.vw_dash_competenza_gruppi` espone oggi, per ogni gruppo:
`competenza_mese`, `gruppo_key`, `tipo_gruppo`, `area_documento`, `riferimento`,
`commessa_id`, `commessa_codice`, `emittente_soggetto_ruolo_id`,
**`cliente_display`**, `stadio`, `n_attivita`, `valore`, `data_attivita_min/max`,
`ha_oneri`, `sorgente_tipo_id`, `sorgente_uid`, `commessa_emittibile`,
`commessa_stato_codice_interno`, `commessa_stato_descrizione`.

Del cliente c'è quindi **solo la stringa da mostrare**: nessun identificativo,
nessun codice, nessun dato fiscale.

## 3. Cosa serve

### 3.1 Poter filtrare la lista per cliente

Deve essere possibile restringere la lista a **un cliente** e ottenere tutti i
suoi gruppi del mese, su qualunque pagina si trovino.

⚠️ **Il cliente rilevante è quello su cui si aggrega la fattura**, non
necessariamente quello che oggi compare in `cliente_display`. È il punto che fa
o rompe la funzione: se le due nozioni divergono (es. anagrafiche figlie che
fatturano a un'anagrafica padre), filtrare su quella sbagliata produce una
selezione che **non** corrisponde alla fattura che ne nascerà — cioè
esattamente il contrario dello scopo. La chiave di aggregazione vive in
`vendite.fn_build_fattura_key`.

### 3.2 Poter riconoscere il cliente nella riga

Oltre alla ragione sociale già presente, ogni riga deve poter esporre:

* il **codice del billing account**;
* l'**identificativo fiscale** (codice fiscale / partita IVA).

**Perché**: l'identificativo fiscale è ciò che distingue due omonimi **prima**
di emettere, non dopo. Su una schermata il cui passo successivo è una fattura,
riconoscere il soggetto sbagliato è un errore che si scopre a documento emesso.

### 3.3 Poter cercare nella lista

Deve essere possibile trovare una riga per: **riferimento del documento** (es.
`ORD0005174`), **codice commessa**, **identificativo fiscale**, **codice
billing account**, **ragione sociale**.

Serve a rispondere a *«dov'è finito questo documento»*, che è una domanda
diversa da *«dammi tutto di questo cliente»* — la prima è una ricerca, la
seconda è il filtro del §3.1. Sono due bisogni distinti, non due modi di fare la
stessa cosa.

### 3.4 Le due colonne nuove disponibili nel catalogo della lista

Codice BA e identificativo fiscale devono essere **disponibili** fra le colonne
della lista configurabile `vendite.dash_competenza_gruppi`, **non accese di
default**: la lista è già larga, e chi ne ha bisogno se le accende.

## 4. Vincoli da rispettare (il «cosa», non il «come»)

1. **Un gruppo resta una riga.** Se l'aggiunta dei dati del cliente moltiplicasse
   le righe, cambierebbero il conteggio e i totali della lista, e il
   «seleziona tutto» della pagina raccoglierebbe doppioni da mandare a
   fatturare. È il vincolo più importante.
2. **I totali di perimetro seguono filtro e ricerca.** La lista ha una riga di
   riepilogo (`vendite.vw_dash_competenza_gruppi_riepilogo`: numero gruppi,
   attività, valore, gruppi con oneri) che oggi segue già il filtro per tipo.
   Deve seguire anche i nuovi: un totale che descrive un perimetro diverso dalla
   lista sopra di sé è peggio di nessun totale.
3. **I facet non seguono il filtro.** Le voci del filtro esistente sono calcolate
   sui dati del perimetro col loro conteggio, e non si restringono quando si
   sceglie un valore (altrimenti scegliendo un tipo le altre voci sparirebbero
   dalla tendina). Se si introduce un elenco clienti, stessa regola.
4. **Nessuna apertura di visibilità.** Il filtro e la ricerca non devono rendere
   raggiungibili clienti o gruppi fuori dallo scope dell'operatore: il perimetro
   resta quello che la lista già applica oggi.
5. **La lista è paginata e ordinabile server-side.** Filtro, ricerca e
   ordinamento devono restare deterministici alla paginazione (regola del
   tiebreaker, `frontend-standards.md` §«Paginazione deterministica»). Se le
   colonne nuove diventano ordinabili, vale anche per loro.
6. **Ricerca server-side**, secondo
   `docs/it/dev/Policy-ricerca-e-paginazione(API-DB).md`.

## 5. Cosa NON serve — perimetro chiuso

* **Nessun cambio al motore di fatturazione**: né alla chiave di aggregazione
  (`fn_build_fattura_key`), né ai lotti, né alla pipeline. Questo brief riguarda
  soltanto **come si legge e si filtra la lista** dei gruppi fatturabili.
* **Niente sulle altre liste** della dashboard (commesse, errori): il bisogno
  nasce sulla lista dei gruppi, che è l'unica su cui si seleziona per fatturare.
* **Il limite di 200 gruppi per chiamata di fatturazione** è lato backend
  (`parse_gruppi`) e non è oggetto di questo brief.

## 6. Definizione di «fatto»

* [ ] scelto un cliente, la lista mostra **tutti** i suoi gruppi fatturabili del
      mese, e solo quelli;
* [ ] il cliente su cui si filtra è **lo stesso** su cui il motore aggrega la
      fattura (§3.1);
* [ ] la riga può mostrare codice billing account e identificativo fiscale, ed
      entrambi sono **disponibili ma spenti** di default nel catalogo colonne;
* [ ] cercando un riferimento documento, un codice commessa, un identificativo
      fiscale, un codice BA o una ragione sociale si trova la riga attesa;
* [ ] il numero di righe e i totali di riepilogo restano coerenti fra loro e col
      filtro applicato;
* [ ] paginazione e ordinamento restano deterministici.

## 7. Dipendenze a valle

Backend e frontend partono **dopo**: il backend per i parametri dell'endpoint
della lista, il frontend per i controlli a video (filtro cliente come scelta
strutturata, ricerca libera) e per la regola di interfaccia che ne consegue —
**ogni cambio di filtro o di ricerca azzera la selezione in corso**, perché
fatturare righe che non si hanno davanti è l'incidente che si vuole evitare.

Dettaglio del seguito FE in
`brief-fe-fatturazione-job-concorrenti.md` §10.

## 8. Riferimenti

| Cosa | Dove |
| --- | --- |
| Vista lista gruppi (stato attuale) | `docs/it/dbzero/vendite/views/vw_dash_competenza_gruppi.md` |
| Vista riepilogo di perimetro | `docs/it/dbzero/vendite/views/vw_dash_competenza_gruppi_riepilogo.md` |
| Chiave di aggregazione della fattura | `docs/it/dbzero/vendite/funzioni/fn_build_fattura_key.md` |
| Decisione D5 che genera il bisogno | `docs/it/dev/work-done/brief-fe-fatturazione-job-concorrenti.md` §9 (chiuso il 2026-08-17, la §10 no) |
| Seguito FE | stesso brief, §10 |
