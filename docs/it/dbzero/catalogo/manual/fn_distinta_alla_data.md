## 📘 Documentazione Concettuale – Funzione `catalogo.fn_distinta_alla_data`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — i legami della distinta
>
> Approfondimento funzioni:
>
> * [script.trgfn_componenti_guard_coerenza_bom](/dbzero/script/funzioni/trgfn_componenti_guard_coerenza_bom) — il guard dei componenti di documento che la chiama
> * [vendite.fn_preventivo_riga_componenti_init](/dbzero/vendite/funzioni/fn_preventivo_riga_componenti_init) — uno dei dieci init e preview che la chiamano
> * [catalogo.fn_articolo_padre_di_distinta_da_oggi](/dbzero/catalogo/funzioni/fn_articolo_padre_di_distinta_da_oggi) — l'altra domanda sul padre: se ha una distinta da oggi in poi
> * [script.fn_data_operativa](/dbzero/script/funzioni/fn_data_operativa) — il giorno aziendale, da passare per chiedere la distinta di oggi
>
> Approfondimento viste:
>
> * [catalogo.vw_articoli_dettaglio](/dbzero/catalogo/views/vw_articoli_dettaglio) — `has_componenti_alla_data`, la distinta di oggi

---

### 🎯 Scopo Principale

Restituisce **i legami della distinta di un padre a una data**: le righe di
`catalogo.articoli_componenti` del padre che sono attive e la cui validità contiene quella data. I
due estremi della validità sono compresi: un legame che finisce oggi c'è ancora oggi, uno che
comincia domani non c'è ancora.

---

### ⭐ Una domanda, una sede

«Di quali componenti è fatto il kit a quella data» se la fanno in molti, e la risposta è una:

* gli init e i preview dei componenti dei documenti di vendita (preventivo, ordine, bolla,
  contratto, eccezione d'offerta) scelgono così i componenti da scrivere o da proporre, alla data
  di riferimento del documento;
* il guard dei componenti di documento accetta un componente solo se il suo legame c'è, alla data
  della testata;
* la vista degli articoli dice se il kit ha componenti oggi.

Poiché chiedono alla stessa funzione, un componente che l'init scrive il guard lo accetta, e uno
spento non lo scrive né lo accetta nessuno.

---

### La data non si sottintende

Con la data vuota non risponde «oggi»: non risponde nessun legame. Chi vuole la distinta di oggi
passa il giorno aziendale. Una data implicita farebbe dipendere la risposta da un default che il
chiamante non vede.

---

### ⚠️ Due domande vicine che non sono questa

* «Il kit ha una distinta da oggi in poi?» guarda anche il futuro, e la chiedono i guard del padre
  e la check degli articoli ammessi: è `catalogo.fn_articolo_padre_di_distinta_da_oggi`.
* I componenti di un **listino** non sono la distinta del catalogo a una data: il listino ha la sua
  copia dei legami, con un periodo, e la legge chi calcola il prezzo del kit.

---

### Come legge

`LANGUAGE sql` con corpo `BEGIN ATOMIC`: le tabelle che legge stanno in `pg_depend`. Restituisce
le colonne di struttura del legame (identificativo, componente, coefficiente, obbligatorio,
esposizione in fattura) per nome: una funzione `BEGIN ATOMIC` che restituisse la riga intera della
tabella smetterebbe di funzionare alla prima colonna aggiunta. Il resto si legge dalla tabella per
identificativo. `STABLE`, `SECURITY INVOKER`: la distinta non ha row level security.

Il planner la espande dentro la query che la chiama, quando la data è una colonna, un parametro o
una chiamata di funzione. Se la data è una sottoquery non la espande: per questo la vista calcola il
giorno aziendale una volta, a parte, e lo passa come colonna.

---

### Test

* `db/pgtap/catalogo/test-distinta-alla-data-v1.sql` — i legami a più date (gli estremi, prima
  dell'inizio, con la data vuota), l'espansione nel chiamante, init e preview del preventivo, il
  guard su un legame spento e su uno finito, la vista, e il presidio: nessun corpo di `vendite`,
  `script`, `acquisti`, `magazzino` e nessuna vista ricopia il filtro.

---

### Note di migrazione

* 2026-11-09 — nasce come sede unica del filtro, che era ricopiato nei dieci init e preview e nella
  vista, e che il guard dei componenti chiedeva senza guardare se il legame era attivo
  (brief-db-revisione-catalogo, giro 1-bis).

---

{% include-markdown "signature-core.md" %}
