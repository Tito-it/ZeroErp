## 📘 Documentazione Concettuale – Trigger function `ui.trgfn_ui_lista_colonna_a10_valida_campo_sorgente`

> **Ultimo aggiornamento**: 21 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.lista_colonna](/dbzero/ui/tabelle/lista_colonna) — la colonna che si scrive, e la sua `origine_campo`
> * [ui.lista_definizione](/dbzero/ui/tabelle/lista_definizione) — la vista, lo schema e la dichiarazione della lineage
>
> Approfondimento viste:
>
> * [dbops.vw_liste_colonne_campo_orfano](/dbzero/dbops/views/vw_liste_colonne_campo_orfano) — ciò che il guard non vede: il DDL sulla vista, i nomi della lineage
>
> Approfondimento funzioni:
>
> * [ui.fn_lista_relazione_ha_attributo](/dbzero/ui/funzioni/fn_lista_relazione_ha_attributo) — la domanda «la relazione ha il campo?»
> * [ui.trgfn_ui_lista_definizione_a10_valida_vista_sql](/dbzero/ui/funzioni/trgfn_ui_lista_definizione_a10_valida_vista_sql) — il controllo gemello sulla vista, che riverifica le colonne
>
> Guide:
>
> * [Configurazione delle liste](/guide/configurazione-liste) — il catalogo delle colonne

---

### 🎯 Scopo Principale

Il trigger verifica, quando una colonna di lista si scrive, che il suo `campo_sorgente` esista dove
la colonna dice di leggerlo (`origine_campo`): un nome sbagliato si ferma al salvataggio invece che
alla prima apertura della lista.

---

### Quando controlla

Parte alla nascita della colonna e quando cambiano `campo_sorgente`, `origine_campo` o `lista_id`, i
tre campi da cui dipende la risposta. Non controlla le colonne senza campo (un'azione, una cella
composta dal frontend). Un campo vuoto non lo giudica lui: lo rifiuta il vincolo
`chk_lista_colonna_campo_sorgente_non_vuoto`, che il guard lascia parlare perché dice la cosa giusta.

---

### Che cosa vale come campo vero

* **Colonna `VISTA`**: una colonna non di sistema e non cancellata della relazione della lista
  (`vista_sql` nello schema `schema_dati`), chiesta a
  [fn_lista_relazione_ha_attributo](/dbzero/ui/funzioni/fn_lista_relazione_ha_attributo): vista,
  vista materializzata, tabella o tabella partizionata. Un'omonima in un altro schema non conta. Il
  controllo salta su una lista senza vista (le celle le riempie il backend) e su una lista spenta:
  una lista registrata prima della sua vista accoglie le colonne, e le verifica quando si riaccende
  ([valida_vista_sql](/dbzero/ui/funzioni/trgfn_ui_lista_definizione_a10_valida_vista_sql)).
* **Colonna `LINEAGE`**: la lista dichiara `legge_lineage`, su ogni lista, accesa o spenta. Il nome
  del campo non lo verifica il guard: il catalogo delle liste non dipende da una vista di `vendite`,
  e il nome lo confronta con la sintesi della lineage il presidio
  [vw_liste_colonne_campo_orfano](/dbzero/dbops/views/vw_liste_colonne_campo_orfano).

---

### ⚠️ Che cosa oggi non copre

* **Una vista che perde una colonna con un DDL non fa ripartire il controllo**: nessun trigger di
  `ui` lo vede. Lo vede il presidio, che confronta ogni lista accesa con la sua relazione.

---

### Codici errore

* `E_UI_CAMPO_SORGENTE_NON_TROVATO` — il campo di una colonna `VISTA` non è nella relazione della
  lista, nel suo schema. La frase porta il campo e la relazione qualificata.
* `E_UI_LINEAGE_NON_DICHIARATA` — una colonna `LINEAGE` su una lista che non dichiara la lineage.
  La frase porta la colonna e la lista.

---

### Test

* `db/pgtap/ui/test-lista-colonna-campo-sorgente-in-vista-v1.sql` — un campo che esiste solo
  nell'omonima di un altro schema è rifiutato (saltato, e dichiarato, se la gemella storica non
  c'è); la colonna vera passa; ogni campo del catalogo sta dove la colonna dice di leggerlo.
* `db/pgtap/ui/test-ui-catalogo-liste-v1.sql` — la colonna `LINEAGE` su una lista che non la
  dichiara, la colonna accolta su una lista spenta, la tabella partizionata.
* `db/pgtap/ui/test-fn-lista-colonne-ricerca-full-v1.sql` — il campo vuoto lo rifiuta il vincolo.
* `db/pgtap/vendite/test-colonne-lineage-liste-v1.sql` — le colonne della lineage sulle liste dei
  documenti.

---

### Note di migrazione

* 2026-05-06 — nasce, col catalogo delle colonne.
* 2026-09-27 — la vista si cerca nel suo schema: prima bastava un'omonima in qualunque schema.
* 2026-10-11 — sono ammessi i nomi della sintesi della lineage, usciti dalle viste di lista.
* 2026-11-21 — il campo si giudica secondo `origine_campo`: la lineage solo dove la lista la
  dichiara, senza leggere la vista di `vendite`; la relazione dal building block, partizionate
  comprese; salto sulle liste spente; via il salto delle azioni, che non hanno campo per vincolo.

---

{% include-markdown "signature-core.md" %}
