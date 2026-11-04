# Brief DB — Ritirare un articolo senza cancellarlo (`obsoleto_dal`)

## ⏭️ Chi riparte — aggiornato al 2026-11-04

**Riparte: team DB**, col censimento delle relazioni (§5): per ogni tabella che sceglie un articolo, dove
è scritta la derivazione e quando. Poi Tid decide i casi aperti del §6 e dà il via allo sviluppo.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ Tid | il modello: vietata la scelta nuova, ammessa la derivazione (2026-11-04) | §3 | — |
| 2 | ✅ Tid | lo strumento: guard sulla riga, non una funzione che il chiamante invoca (2026-11-04) | §4 | — |
| 3 | DB | censimento delle relazioni verso `catalogo.articoli` e della loro derivazione | §5 | — |
| 4 | Tid | O-1…O-5 e il caso della derivazione scritta dopo la riga | §6 | 3 |
| 5 | Tid | via allo sviluppo | — | 4 |
| 6 | DB | changeSet, pgTAP, guida `uso-di-obsoleto` | §7 | 5 |
| 7 | BE / FE | `obsoleto_dal` nel form articolo, picker senza obsoleti, codice di errore a video | §8 | 6 |

Decisioni aperte di Tid: O-1…O-5 (§6), dopo il censimento. Lavoro da committare: questo brief.

> **Chi scrive:** team DB (`dev/db-tid`), 2026-11-04. **A chi:** Tid, poi il team DB, poi BE/FE.
> **Origine:** Tid, 2026-11-04: «per il codice articolo potrebbe essere utile un meccanismo di obsoleto,
> per ritirare l'articolo senza doverlo cancellare».
> **Brief vicini verificati:** `work-done/brief-db-deprecabilita-catalogo-vs-istanze.md` (decisione P1:
> `attivo` ≠ «selezionabile per il nuovo») e `work-done/brief-db-obsoleto-dal-filtro-lookup-e-guard.md`
> (lookup `p_includi_obsoleti`, guard generico): sono il pattern da cui si parte, chiusi, e non coprivano
> gli articoli. `work-done/brief-db-articoli-ammessi-per-documento.md` (A-10): blocca la struttura di
> un articolo usato; asse diverso, nessuna sovrapposizione. `work-in-progress/brief-db-magazzino-tutte-le-scritture-dal-verbo.md`:
> tocca le scritture di magazzino, che qui **non** si bloccano (O-5). Nessun brief aperto sul tema.
> **Ambito:** tocca le righe di tutti i documenti di vendita e d'acquisto. Rientra nel fermo allentato
> (PROJECT_CONTEXT, 2026-10-25) perché poggia su un pezzo comune, il guard generico, montato una volta
> per relazione; ⏳ serve l'ok esplicito di Tid sull'ambito, insieme al via.
> **Sviluppo:** non c'è produzione (2026-11-04). Si va per la strada più corta: niente compatibilità,
> rotture BE ammesse, colonna nuova senza backfill.

---

## 1. Il caso

Un articolo che non si vende più non si può cancellare (ha documenti, movimenti, listini) e non si può
disattivare: `attivo=false` è bloccato da circa trenta trigger `block_deact` su `catalogo.articoli`, e a
ragione. `attivo` vuol dire «riferimento valido», e un articolo usato lo resta per sempre.

Manca l'altro asse: **«si può scegliere per un uso nuovo»**. È lo stesso difetto che
`brief-db-deprecabilita-catalogo-vs-istanze` ha risolto su `tipi_prestazione` e `template_flussi` con
`obsoleto_dal`.

## 2. I fatti di struttura (doc auto-generata, 2026-11-04)

* `catalogo.articoli` non ha `obsoleto_dal`.
* Il pattern esiste: `dbops.fn_get_lookup_codici(…, p_includi_obsoleti)` e il guard generico
  `dbops.trgfn_child_requires_non_obsolete_parent` (`E_CATALOGO_OBSOLETO_NUOVA_ISTANZA`), montato una
  volta per relazione. Oggi il guard **non distingue** una riga nuova da una derivata.
* La derivazione **non è scritta allo stesso modo** su tutte le righe: `vendite.ordini_righe` e
  `vendite.fatture_righe` hanno `sorgente_tipo_id`/`sorgente_uid`, mentre `vendite.ddt_righe` e
  `vendite.preventivi_righe` no.

## 3. Il modello (Tid, 2026-11-04)

`obsoleto_dal date NULL` su `catalogo.articoli`: `NULL` = si sceglie; una data passata = ritirato; una
data futura = ritiro programmato.

| Caso | Regola |
| --- | --- |
| riga **nuova** scelta dall'operatore su preventivo, ordine, listino, contratto | ⛔ respinta se l'articolo è obsoleto |
| riga **derivata** da un altro documento (ordine dal preventivo, bolla dall'ordine, fattura dalla bolla, reso) | ✅ passa: non è una scelta |
| cambio dell'articolo su una riga esistente, anche derivata | ⛔ è una scelta nuova |
| magazzino: movimenti, inventari, rettifiche, trasferimenti | ✅ mai bloccato (O-5) |

`attivo` non si tocca: resta `true`, e i `block_deact` non vengono mai sfiorati.

## 4. Lo strumento (Tid, 2026-11-04)

Un **guard sulla riga**, BEFORE INSERT OR UPDATE OF `articolo_id`: se la riga è derivata passa,
altrimenti un articolo obsoleto alla data viene respinto. La derivazione si legge **dalla riga**, mai da
un parametro che il chiamante dichiara: così il guard copre ogni strada (verbi, BE, import) senza che
nessuno debba ricordarsi di chiamare niente.

* Il guard generico `trgfn_child_requires_non_obsolete_parent` si estende con un argomento: la colonna
  che, valorizzata, esenta la riga. Si monta una volta per relazione (tier 2 del pattern).
* Il picker filtra già: `p_includi_obsoleti=false` nella selezione per il nuovo. Il guard è la rete
  sotto il picker.

## 5. Censimento (team DB, prossimo passo)

Per ogni FK verso `catalogo.articoli`, letta da `pg_constraint` (non dai `block_deact`: una tabella senza
`attivo` non ha il trigger e sfuggirebbe):

| Colonna del censimento | Perché |
| --- | --- |
| tabella e colonna FK | il punto di montaggio |
| famiglia: scelta (documento, listino, distinta, promo), magazzino, configurazione dell'articolo | decide se si monta |
| dove è scritta la derivazione: colonna sulla riga, tabella di legame, nessuna | decide l'argomento del guard |
| **quando** è scritta: nello stesso `INSERT` della riga o dopo | ⚠️ un BEFORE INSERT non vede un legame scritto dopo (§6, caso D) |

## 6. Da decidere (Tid, dopo il censimento)

| # | Domanda | Proposta DB |
| --- | --- | --- |
| O-1 | A quale data si confronta `obsoleto_dal`: quella del documento o il giorno della scelta? | il giorno della scelta (`script.fn_data_operativa()`): il ritiro programmato è una scadenza |
| O-2 | La nuova versione di un listino copiata dalla precedente è derivata? | no: un listino nuovo è un impegno nuovo a vendere, e l'obsoleto non si ricopia |
| O-3 | Acquisti: si può ordinare al fornitore un articolo obsoleto? | stessa regola: respinto sulla riga nuova, ammesso su quella derivata |
| O-4 | Distinte: un componente obsoleto in una composizione nuova? | respinto; le righe-componente espanse da una distinta esistente sono derivate e passano |
| O-5 | Magazzino | mai bloccato: la giacenza residua va comunque scaricata |
| D | La derivazione scritta **dopo** la riga (bolla, preventivo: da confermare col censimento) | da proporre dopo il censimento; strade possibili: il verbo che genera scrive il legame sulla riga, oppure un controllo a fine istruzione |

## 7. Sviluppo DB (dopo il via)

* `00_schema`: `ALTER TABLE catalogo.articoli ADD COLUMN obsoleto_dal date NULL` (nessun backfill).
* `20_code`: il guard generico esteso, il montaggio per relazione, `obsoleto_dal` in coda a
  `vw_articoli_dettaglio` e nelle viste dei picker.
* pgTAP che **costruisce** i casi: riga nuova su articolo obsoleto respinta; riga derivata passa; cambio
  di articolo su riga derivata respinto; ritiro programmato (data futura) passa; magazzino passa.
* Guida `uso-di-obsoleto.md`: gli articoli come secondo caso, con la distinzione nuova/derivata.

## 8. Ricadute BE / FE (da dettagliare dopo il §6)

* BE: `obsoleto_dal` nominato in `ARTICOLI_DETAIL_COLUMNS`; `includi_obsoleti=false` nei picker di riga
  nuova; policy per il codice di errore.
* FE: `obsoleto_dal` nel drawer articolo (data, cancellabile per «riattivare»); l'obsoleto riconoscibile in
  lista; il messaggio del guard a video.
