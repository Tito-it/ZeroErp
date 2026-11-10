## 📘 Documentazione Concettuale – Funzione `catalogo.fn_articolo_colonne_struttura`

> **Ultimo aggiornamento**: 9 novembre 2026
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

### ⭐ È la dichiarazione

L'elenco è scritto qui, e solo qui: le otto colonne, nell'ordine in cui il guard dell'uso cerca la
prima cambiata (composito, solo componente, natura di vendita, causale onere, tipologia di
listino, gestito a magazzino, a lotti, a matricola). La funzione è una costante, `IMMUTABLE`.

Le regole del form in `dbops.lock_columns_conditional` non decidono più niente per la porta: se
una regola si spegne o se ne aggiunge una, le colonne correggibili restano queste. Il nome
leggibile di ogni colonna lo dà `catalogo.fn_articolo_flag_etichetta`.

---

### Chi la legge

* `catalogo.fn_articolo_correggi_struttura`, per le colonne ammesse nella correzione e per
  quelle che scrive.
* Il backend, per i campi che la scheda dell'articolo riapre in correzione.

* Il guard `catalogo.trgfn_articoli_guard_struttura_se_usato`, nel corpo, per cercare la prima
  colonna cambiata.

Due copie non si possono leggere da qui, e le confronta un pgTAP: l'elenco `UPDATE OF` del
trigger del guard (un trigger non prende le sue colonne da una funzione) e le regole del form sul
predicato dell'uso.

---

### Test

* `db/pgtap/catalogo/test-articolo-colonne-struttura-v1.sql` — la funzione restituisce le colonne
  delle regole accese nell'ordine dichiarato; il guard le nomina tutte; il verbo segue l'elenco,
  anche quando una regola nuova entra nel registro o una regola si spegne.

---

### Note di migrazione

* 2026-10-18 — nasce: prima l'elenco era una costante del verbo di correzione, e la scheda
  dell'articolo lo ricopiava (brief-db-articoli-ammessi-per-documento).
* 2026-11-09 — diventa la dichiarazione: non legge più le regole del form, e spegnerne una non
  toglie la colonna alla porta (brief-db-revisione-catalogo, giro 3).

---

{% include-markdown "signature-core.md" %}
