## 📘 Documentazione Concettuale – Vista `catalogo.vw_articoli_componenti_dettaglio`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — i legami della distinta che la vista legge
> * [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — codice e descrizione di kit e componente
> * [config.esposizioni_componente](/dbzero/config/tabelle/esposizioni_componente) — la decodifica dell'esposizione in fattura
> * [ui.lista_definizione](/dbzero/ui/tabelle/lista_definizione) — la lista configurabile che la usa come sorgente
>
> Approfondimento funzioni:
>
> * [script.fn_data_operativa](/dbzero/script/funzioni/fn_data_operativa) — il giorno aziendale della data di chiusura proposta
>
> Guide:
>
> * [Gestione listini](/guide/gestione-listini#53-immutabilita-della-bom-pattern-chiudi-nuova-versione) — chiudi e nuova versione

---

### 🎯 Scopo Principale

Le righe della distinta base, una per legame, con codice e descrizione del kit e del componente, la decodifica
dell'esposizione in fattura e le capability che dicono se e da quando il legame si può chiudere.

È la sorgente unica delle righe della distinta: la lista configurabile `catalogo.articolo_componenti` la legge.
Per cambiare un legame si scrive su `catalogo.articoli_componenti`.

---

### Che cosa aggiunge ai legami

* **Le date** sono `valido_dal` e `valido_al` della tabella, così come sono.
* **Kit e componente** con il loro codice e la descrizione.
* **L'esposizione in fattura** in tre forme: `esposizione_in_fattura`, il codice interno (`NASCOSTO`,
  `DESCRITTIVO`, `VALORIZZATO`) su cui ragiona la logica; `esposizione_in_fattura_codice`, il codice che la
  lista mostra; `esposizione_in_fattura_etichetta_key`, la chiave della traduzione per il frontend.

Tutte le decodifiche sono in `LEFT JOIN`: una riga che non aggancia un articolo o il vocabolario resta visibile.
La vista non filtra su `attivo` né sulla validità: mostra anche i legami spenti, chiusi e futuri.

---

### Le capability di chiusura

Chiudere è l'unica modifica di struttura ammessa su un legame, e la vista dice al frontend come proporla:

* `puo_chiudersi` è vero solo se `valido_al` è vuoto. Un legame che ha già una data di fine, anche futura, conta
  come chiuso, e `motivo_non_chiudibile` vale `RIGA_GIA_CHIUSA`.
* `data_min_chiusura` è `valido_dal`: un legame si chiude al più presto il giorno in cui comincia.
* `data_default_chiusura` è il giorno aziendale, oppure `valido_dal` se il legame comincia nel futuro.

`attivo` non entra nel calcolo: un legame spento si può chiudere come uno acceso.

---

### ⚠️ Che cosa oggi non copre

* **La chiusura proposta può stare nel passato.** La data minima è l'inizio del legame, non il giorno aziendale:
  la capability offre la chiusura all'indietro di un legame già usato, e il database la accetta.
* **La data proposta e la nuova versione.** La chiusura proposta è oggi, e il periodo comprende l'ultimo giorno:
  la nuova versione deve partire da domani, non da oggi, o si sovrappone alla vecchia. Le capability non danno la
  data d'inizio della versione successiva.

---

### Test

* `db/pgtap/catalogo/test-vw-articoli-componenti-dettaglio-capabilities-v1.sql` — le quattro capability su un
  legame aperto, uno chiuso e uno futuro.
* `db/pgtap/vendite/test-vw-righe-dettaglio-sorgente-lista-v1.sql` — come le viste delle righe dei documenti, non
  ordina nel corpo; porta l'esposizione e le quattro capability, e non più le due colonne ritirate.

---

### Note di migrazione

* 2026-04-28 — nascono le capability di chiusura.
* 2026-09-28 — diventa la sorgente unica delle righe della distinta: la lista configurabile e il repository la
  leggono, e il backend ritira la sua copia della capability di chiusura.
* 2026-10-01 — `esposto_in_fattura` lascia il posto a `esposizione_in_fattura`, con codice ed etichetta in coda.
* 2026-10-02 — escono `partecipa_qta` e `determina_qta_padre`, ritirate dalla tabella.

---

{% include-markdown "signature-core.md" %}
