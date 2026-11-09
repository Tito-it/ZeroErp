## 📘 Documentazione Concettuale – Vista `catalogo.vw_articoli_componenti_dettaglio`

> **Ultimo aggiornamento**: 9 novembre 2026
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
> * [script.fn_data_operativa](/dbzero/script/funzioni/fn_data_operativa) — il giorno aziendale delle date di chiusura
> * [catalogo.trgfn_articoli_componenti_block_modifica_struttura](/dbzero/catalogo/funzioni/trgfn_articoli_componenti_block_modifica_struttura) — la regola della fine che la data minima ripete
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
* `data_min_chiusura` è la più tarda fra `valido_dal` e ieri: la fine di un legame non cambia i giorni già passati,
  e il trigger d'immutabilità rifiuta una fine prima di ieri. Chiudere a ieri è ammesso, ed è il modo di far valere
  da oggi la versione nuova. Un legame che comincia nel futuro si chiude al più presto il giorno in cui comincia.
* `data_default_chiusura` è il giorno aziendale, oppure `valido_dal` se il legame comincia nel futuro.

`attivo` non entra nel calcolo: un legame spento si può chiudere come uno acceso.

---

### ⚠️ Che cosa oggi non copre

* **La data proposta e la nuova versione.** La chiusura proposta è oggi, e il periodo comprende l'ultimo giorno:
  la nuova versione deve partire da domani, non da oggi, o si sovrappone alla vecchia. Chi vuole la versione nuova
  da oggi deve scegliere ieri, la data minima. Le capability non danno la data d'inizio della versione successiva.

---

### Test

* `db/pgtap/catalogo/test-vw-articoli-componenti-dettaglio-capabilities-v1.sql` — le quattro capability su un
  legame aperto, uno chiuso e uno futuro; la data minima è ieri per un legame nato nel passato.
* `db/pgtap/catalogo/test-distinta-storia-e-ritorni-v1.sql` — la prima fine proposta è ieri per un legame nato nel
  passato, `valido_dal` per uno che nasce domani.
* `db/pgtap/vendite/test-vw-righe-dettaglio-sorgente-lista-v1.sql` — come le viste delle righe dei documenti, non
  ordina nel corpo; porta l'esposizione e le quattro capability, e non più le due colonne ritirate.

---

### Note di migrazione

* 2026-04-28 — nascono le capability di chiusura.
* 2026-09-28 — diventa la sorgente unica delle righe della distinta: la lista configurabile e il repository la
  leggono, e il backend ritira la sua copia della capability di chiusura.
* 2026-10-01 — `esposto_in_fattura` lascia il posto a `esposizione_in_fattura`, con codice ed etichetta in coda.
* 2026-10-02 — escono `partecipa_qta` e `determina_qta_padre`, ritirate dalla tabella.
* 2026-11-09 — `data_min_chiusura` passa da `valido_dal` alla più tarda fra `valido_dal` e ieri, come la regola
  della fine nella tabella (brief-db-revisione-catalogo, giro 1).

---

{% include-markdown "signature-core.md" %}
