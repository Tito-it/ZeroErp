## 📘 Documentazione Concettuale – Funzione `catalogo.fn_articolo_colonne_struttura`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.lock_columns_conditional](/dbzero/dbops/tabelle/lock_columns_conditional) — il registro da cui legge l'elenco
> * [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — la regola «un articolo usato non cambia la sua struttura»
>
> Approfondimento funzioni:
>
> * [catalogo.fn_articolo_correggi_struttura](/dbzero/catalogo/funzioni/fn_articolo_correggi_struttura) — il verbo che la usa per le colonne ammesse
> * [catalogo.trgfn_articoli_guard_struttura_se_usato](/dbzero/catalogo/funzioni/trgfn_articoli_guard_struttura_se_usato) — il guard che ha lo stesso elenco scritto nel montaggio
> * [catalogo.fn_articolo_usato](/dbzero/catalogo/funzioni/fn_articolo_usato) — il predicato delle regole che legge

---

### 🎯 Scopo Principale

Restituisce le colonne strutturali di un articolo: quelle che non cambiano più quando l'articolo
è usato, e che il SUPER_ADMIN può correggere. È l'unico posto da cui si legge l'elenco.

---

### Da dove legge

L'elenco non è scritto qui. Sono le regole **accese** del form in
`dbops.lock_columns_conditional` su `catalogo.articoli` che hanno come condizione il predicato
dell'uso, `catalogo.fn_articolo_usato`. Le colonne che il form spegne quando l'articolo è usato
sono le stesse che la correzione deve poter riaprire.

* L'ordine è quello della dichiarazione nel registro.
* Se il registro non ha regole su quel predicato, l'elenco è vuoto.
* Una regola spenta esce dall'elenco.

La funzione è SECURITY INVOKER: il registro lo legge anche l'app.

---

### Chi la legge

* `catalogo.fn_articolo_correggi_struttura`, per le colonne ammesse nella correzione e per
  quelle che scrive.
* Il backend, per i campi che la scheda dell'articolo riapre in correzione.

Il guard `catalogo.trgfn_articoli_guard_struttura_se_usato` non la può leggere: un trigger non
prende le sue colonne da una funzione, e l'elenco lì è scritto. Un pgTAP confronta le due copie.

---

### ⚠️ Che cosa oggi non copre

* **La porta dipende dalle regole del form.** La regola si riconosce confrontando il testo della
  condizione. Se si spegne una regola del form, il guard continua a bloccare la colonna, ma la
  colonna esce da questo elenco e il verbo di correzione la rifiuta: non si corregge più da
  nessuna parte. Oggi lo segnala solo un pgTAP.

---

### Test

* `db/pgtap/catalogo/test-articolo-colonne-struttura-v1.sql` — la funzione restituisce le colonne
  delle regole accese nell'ordine dichiarato; il guard le nomina tutte; il verbo segue l'elenco,
  anche quando una regola nuova entra nel registro o una regola si spegne.

---

### Note di migrazione

* 2026-10-18 — nasce: prima l'elenco era una costante del verbo di correzione, e la scheda
  dell'articolo lo ricopiava (brief-db-articoli-ammessi-per-documento).

---

{% include-markdown "signature-core.md" %}
