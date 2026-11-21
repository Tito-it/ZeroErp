## 📘 Documentazione Concettuale – Funzione `ui.fn_lista_relazione_ha_attributo`

> **Ultimo aggiornamento**: 21 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.lista_definizione](/dbzero/ui/tabelle/lista_definizione) — lo schema e la relazione di una lista
> * [ui.lista_colonna](/dbzero/ui/tabelle/lista_colonna) — il campo di una colonna
>
> Approfondimento viste:
>
> * [dbops.vw_liste_colonne_campo_orfano](/dbzero/dbops/views/vw_liste_colonne_campo_orfano) — il presidio che la usa su tutto il catalogo
>
> Approfondimento funzioni:
>
> * [ui.trgfn_ui_lista_definizione_a10_valida_vista_sql](/dbzero/ui/funzioni/trgfn_ui_lista_definizione_a10_valida_vista_sql) — la usa per la vista e per le colonne
> * [ui.trgfn_ui_lista_colonna_a10_valida_campo_sorgente](/dbzero/ui/funzioni/trgfn_ui_lista_colonna_a10_valida_campo_sorgente) — la usa per il campo della colonna

---

### 🎯 Scopo Principale

La funzione risponde a una domanda sola: **la relazione di una lista esiste nel suo schema, e ha
questo campo?** È il building block della domanda: i due guard del catalogo, il presidio delle
colonne orfane e il pgTAP del catalogo la chiedono qui, invece di ricopiare la lettura di
`pg_catalog`.

---

### Che cosa risponde

* Vero se nello schema `p_schema` c'è una relazione `p_relazione` che una lista può leggere: una
  vista, una vista materializzata, una tabella o una tabella partizionata. I nomi sono esatti, come
  li tiene `pg_catalog`: maiuscole e spazi contano.
* Con `p_attributo` valorizzato, vero solo se quella relazione ha anche la colonna, viva e non di
  sistema.
* Con `p_attributo` `NULL` si chiede solo la relazione.
* Schema o relazione `NULL`: falso.

Non solleva: chi la chiama decide che cosa fare del no.

---

### Perché una sede sola

La stessa lettura stava in due trigger e in un pgTAP, ciascuno con il suo elenco di tipi di
relazione, e le tabelle partizionate restavano fuori da tutti e tre. Una regola scritta tre volte
risponde in tre modi alla prima correzione fatta in un posto solo.

---

### Test

* `db/pgtap/ui/test-lista-colonna-campo-sorgente-in-vista-v1.sql` — il catalogo intero, letto con la
  funzione.
* `db/pgtap/ui/test-ui-catalogo-liste-v1.sql` — la tabella partizionata accolta, la colonna tolta con
  un DDL vista dal presidio.

---

### Note di migrazione

* 2026-11-21 — nasce, e la leggono i due guard del catalogo delle liste, il presidio delle colonne
  orfane e il pgTAP del catalogo.

---

{% include-markdown "signature-core.md" %}
