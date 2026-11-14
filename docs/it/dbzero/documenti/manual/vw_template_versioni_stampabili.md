## 📘 Documentazione Concettuale – Vista `documenti.vw_template_versioni_stampabili`

> **Ultimo aggiornamento**: 14 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.template_documenti](/dbzero/documenti/tabelle/template_documenti) — il modello, che deve essere attivo
> * [documenti.template_documenti_versioni](/dbzero/documenti/tabelle/template_documenti_versioni) — stato, attivo e validità della versione, e il vincolo che non le fa sovrapporre
>
> Approfondimento viste:
>
> * [documenti.vw_template_personalizzati_scarto](/dbzero/documenti/views/vw_template_personalizzati_scarto) — confronta due versioni che stampano oggi
>
> Approfondimento funzioni:
>
> * [documenti.fn_risolvi_template_applicabile](/dbzero/documenti/funzioni/fn_risolvi_template_applicabile) — la porta della stampa
> * [documenti.fn_template_esito_risoluzione](/dbzero/documenti/funzioni/fn_template_esito_risoluzione) — la regola dei due livelli
> * [documenti.fn_personalizza_template_standard](/dbzero/documenti/funzioni/fn_personalizza_template_standard) — la versione da cui parte una copia
> * [script.fn_data_operativa](/dbzero/script/funzioni/fn_data_operativa) — il giorno di oggi nel fuso dell'azienda
>
> Guide:
>
> * [Documenti e Stampe](/guide/documenti-e-stampe) — §3.1, un modello conta solo se può stampare

---

### 🎯 Scopo Principale

Dice quali modelli possono stampare oggi, e con quale versione: una riga per modello. È la sede unica
del predicato «può stampare»: chi deve sapere se un modello stampa legge questa vista, invece di
ripeterne le condizioni.

---

### Che cosa vuol dire «può stampare»

Un modello può stampare se è attivo e ha una versione:

* attiva;
* fuori bozza, cioè `PUBBLICATA` oppure `OBSOLETA`;
* valida alla data operativa, il giorno di oggi nel fuso dell'azienda.

---

### ⭐ Decide la validità, non lo stato

Lo stato separa le versioni che si usano dalla `BOZZA`; il giorno in cui una versione stampa lo dicono
le sue date. La pubblicazione di una versione nuova rende `OBSOLETA` quella in corso nel momento in cui
pubblica, e la chiude alla vigilia della partenza della nuova. Se la nuova parte da una data futura,
fino a quel giorno stampa ancora la vecchia, e dal giorno di partenza la nuova: il modello non resta
mai senza versione nell'intervallo.

---

### Una riga per modello, per costruzione

Le versioni attive fuori bozza di uno stesso modello non possono avere periodi di validità che si
sovrappongono: lo impedisce un vincolo di esclusione sulla tabella delle versioni, che copre sia le
`PUBBLICATA` sia le `OBSOLETA`. Per ogni giorno, quindi, un modello ha al più una versione che stampa.

---

### Chi la legge

* `fn_template_esito_risoluzione` — la regola dei due livelli;
* `fn_risolvi_template_applicabile` — la deduzione del tipo e il modello indicato;
* `fn_personalizza_template_standard`, attraverso la porta della stampa — la versione dello standard
  da cui parte una copia;
* `vw_template_personalizzati_scarto` — le due versioni che confronta.

La vista legge con i permessi di chi la interroga; le tabelle dei modelli non hanno sicurezza di riga.

---

### Test

* `db/pgtap/documenti/test-documenti-template-porta-unica-v1.sql` — il modello attivo con una versione
  pubblicata valida c'è, il modello spento e quello con la sola bozza no.
* `db/pgtap/documenti/test-fn-pubblica-template-documento-versione-v1.sql` — il vincolo copre anche le
  `OBSOLETA`; fra la pubblicazione di una versione futura e la sua partenza stampa la superata; con
  partenza oggi stampa la nuova.

---

### Note di migrazione

* 2026-10-21 — nasce. Prima il predicato era scritto due volte nella funzione di risoluzione e una nel
  backend, che non guardava se il modello è attivo.
* 2026-11-14 — prima la vista chiedeva lo stato `PUBBLICATA`. Fra la pubblicazione di una versione con
  partenza futura e quella partenza non stampava nessuna delle due, e il modello cadeva su
  `E_DOCUMENTI_TEMPLATE_NON_RISOLTO`, contro la decisione del 2026-04-29 che voleva la vecchia in uso
  fino alla partenza della nuova.

---

{% include-markdown "signature-core.md" %}
