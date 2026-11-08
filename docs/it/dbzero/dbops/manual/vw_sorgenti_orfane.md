## 📘 Documentazione Concettuale – Vista `dbops.vw_sorgenti_orfane`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — il catalogo dei bersagli
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — dove la vista è iscritta
>
> Approfondimento funzioni:
>
> * [dbops.fn_sorgenti_orfane](/dbzero/dbops/funzioni/fn_sorgenti_orfane) — chi la calcola
> * [dbops.fn_sorgenti_orfane_perimetro](/dbzero/dbops/funzioni/fn_sorgenti_orfane_perimetro) — su quali tabelle
> * [script.trgfn_guard_sorgente](/dbzero/script/funzioni/trgfn_guard_sorgente) — il guard unico, che impedisce di scrivere un orfano
> * [script.trgfn_sorgente_in_uscita](/dbzero/script/funzioni/trgfn_sorgente_in_uscita) — il lato «in uscita», che impedisce di crearne cancellando l'origine
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello del collegamento tipo + chiave
> * [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — come si legge un presidio che deve restare vuoto

---

### 🎯 Scopo Principale

Le righe la cui provenienza punta a un record che non c'è più. **Deve restare vuota.** Ogni riga dice
la tabella, l'identificativo della riga, la grammatica della tabella, il **livello** a cui manca
l'origine (`DOCUMENTO`, `RIGA`, `DETTAGLIO`), il tipo e le colonne della provenienza, e la tabella
dove il record manca.

---

### Che cosa vuol dire una riga

Un movimento di magazzino, una riga d'ordine, una testata dicono da quale documento nascono: un tipo a
catalogo, la chiave del documento e, dove serve, la riga e il dettaglio. Il collegamento non è una
chiave esterna e non può esserlo, perché il bersaglio cambia con il tipo. Il guard unico impedisce
di **scrivere** una provenienza che non si risolve, e il lato «in uscita» impedisce di cancellare
un'origine ancora referenziata (o cancella i figli con lei); questa vista trova gli orfani nati per
altre strade, **dopo**: una tabella senza guard, una cancellazione fatta a trigger spenti.

⛔ Il rimedio non è cancellare la riga orfana: è capire chi ha cancellato il bersaglio. Di norma è
una cancellazione fuori dalle porte, perché i documenti registrati non si eliminano.

---

### Il presidio

Nel catalogo dei presidi è di natura `ZERO`, guardata ogni settimana, con perimetro `DEFINER`: la
funzione che la calcola gira coi privilegi del proprietario e attraversa la row level security,
perché un orfano in una tabella protetta va visto comunque. Il perimetro delle tabelle esaminate si
legge da `dbops.fn_sorgenti_orfane_perimetro`.

---

### Test

* `db/pgtap/dbops/test-sorgenti-orfane-v1.sql` — un'origine che manca produce una riga, a ognuno
  dei tre livelli e in tutte e due le grammatiche; il conteggio del presidio la vede; la riga di
  catalogo dei presidi ha natura, perimetro e cadenza attesi.

---

### Note di migrazione

* 2026-09-18 — nasce con il secondo lotto del magazzino (`brief-db-magazzino-lotto-2-motore`).
* 2026-11-06 — l'origine si cerca a tre livelli (documento, riga, dettaglio), nella grammatica di
  ogni tabella: nascono le colonne `grammatica`, `livello`, `sorgente_id`, `sorgente_riga` e
  `sorgente_dettaglio`.
* 2026-11-08 — esce la grammatica del guard tipizzato, ritirato: le tabelle che lo montavano sono
  passate al guard unico.

---

{% include-markdown "signature-core.md" %}
