## 📘 Documentazione Concettuale – Trigger function `catalogo.trgfn_articoli_guard_flags_struttura_bom_attiva`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — la tabella su cui il guard è montato
> * [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — i legami di distinta che il guard interroga
> * [dbops.lock_columns_conditional](/dbzero/dbops/tabelle/lock_columns_conditional) — le regole gemelle che spengono gli stessi campi nel form
>
> Approfondimento funzioni:
>
> * [catalogo.fn_articolo_padre_di_distinta_in_vigore](/dbzero/catalogo/funzioni/fn_articolo_padre_di_distinta_in_vigore) — il predicato del primo controllo
> * [catalogo.fn_articolo_componente_di_distinta_in_vigore](/dbzero/catalogo/funzioni/fn_articolo_componente_di_distinta_in_vigore) — il predicato del secondo controllo
> * [catalogo.fn_articolo_primo_padre_da_oggi](/dbzero/catalogo/funzioni/fn_articolo_primo_padre_da_oggi) — il predicato del terzo controllo, e il padre nel messaggio
> * [catalogo.trgfn_articoli_componenti_guard_componente](/dbzero/catalogo/funzioni/trgfn_articoli_componenti_guard_componente) — il lato legame della distinta a un livello
> * [dbops.fn_non_editable_fields](/dbzero/dbops/funzioni/fn_non_editable_fields) — il form, che legge le regole gemelle
>
> Guide:
>
> * [Modello componenti BoM](/dev/manual/modello-componenti-bom) — il modello della distinta a un livello

---

### 🎯 Scopo Principale

Impedisce di cambiare i flag di struttura di un articolo (`is_composito`, `is_solo_componente`,
`requires_serial`) quando il cambio renderebbe incoerente una distinta in vigore, e impedisce a
un componente di diventare composito.

I tre flag decidono il ruolo dell'articolo nella distinta. Cambiarli con legami in vigore lascia
una struttura che nessuno ripara da solo: un padre «non composito» con componenti attivi, che
il calcolo dei prezzi e la fatturazione leggono ancora; un pezzo che diventa vendibile da solo
mentre sta in un kit; una distinta a due livelli.

---

### I tre controlli

Il guard è `BEFORE UPDATE` dei tre flag. Ogni controllo chiama il suo predicato solo se il
flag cambia davvero: un salvataggio che riscrive lo stesso valore passa.

1. **L'articolo è padre.** Se cambiano `is_composito` o `requires_serial`, e l'articolo ha un
   legame attivo in vigore alla data operativa, il cambio è rifiutato
   (`E_BOM_MODIFICA_VIETATA`).
2. **L'articolo è componente.** Se cambia `is_solo_componente`, e l'articolo è componente di
   un legame attivo in vigore alla data operativa, il cambio è rifiutato
   (`E_BOM_MODIFICA_VIETATA`).
3. **Un componente non diventa composito.** Se `is_composito` passa da falso a vero, e
   l'articolo è componente di un legame attivo in vigore **o futuro**, il cambio è rifiutato
   (`E_BOM_COMPONENTE_DIVENTA_COMPOSITO`). Il messaggio porta il codice dell'articolo e quello
   del primo padre per codice. Un legame scaduto è storia e non conta.

Il terzo controllo guarda anche il futuro perché la distinta ha un livello solo: dal giorno in
cui il legame futuro entra in vigore, la distinta ne avrebbe due. Il lato legame della stessa
regola è `catalogo.trgfn_articoli_componenti_guard_componente`, che rifiuta un componente
composito.

---

### ⭐ Guard e form chiamano gli stessi predicati

Ogni controllo chiama un predicato `catalogo.fn_*`, e la regola gemella del form in
`dbops.lock_columns_conditional` chiama lo stesso. Il form spegne il campo se e solo se il guard
rifiuterebbe la modifica. La regola del form sul terzo controllo spegne `is_composito` solo su
un articolo ancora semplice.

---

### Che cosa non giudica

* Le altre colonne strutturali di un articolo usato: le giudica
  `catalogo.trgfn_articoli_guard_struttura_se_usato`. La porta amministratore apre quel guard,
  non questo: dalla correzione di struttura la distinta parla lo stesso.
* L'IVA del kit: la giudica `catalogo.trgfn_articoli_guard_iva_bom_attiva`.

---

### ⚠️ Che cosa oggi non copre

* **Un padre con una distinta solo futura cambia i flag.** Il primo controllo guarda solo i
  legami in vigore oggi: un padre i cui legami partono domani può smettere di essere composito,
  o perdere `requires_serial`. Il terzo controllo, invece, guarda anche il futuro.
* **Il lato padre di «solo componente» non è protetto.** Il secondo controllo impedisce a un
  componente in vigore di cambiare `is_solo_componente`, ma niente impedisce a un padre di
  diventare anche solo componente: l'articolo resta composito e solo componente insieme.
* **I ritorni in vigore non si rigiudicano.** Il guard scatta quando cambia un flag
  dell'articolo, non quando un legame si riaccende, si riapre o arriva alla sua data di inizio.

---

### Codici errore

* `E_BOM_MODIFICA_VIETATA` — primo e secondo controllo: il flag cambia mentre l'articolo è padre
  o componente di un legame in vigore.
* `E_BOM_COMPONENTE_DIVENTA_COMPOSITO` — terzo controllo: un componente di un legame in vigore o
  futuro diventa composito. Il campo è `is_composito`.

---

### Test

* `db/pgtap/catalogo/test-distinta-predicati-guard-e-form-v1.sql` — guard e form chiamano i tre
  predicati, e per articoli costruiti il form spegne la colonna se e solo se il guard rifiuta.
* `db/pgtap/catalogo/test-distinta-un-livello-e-onere-natura-v1.sql` — un componente di una
  distinta in vigore o futura non diventa composito; di una distinta scaduta sì; il form spegne
  `is_composito` sul componente in vigore.
* `db/pgtap/vendite/test-listini-righe-comp-guard-coerenza-bom-v1.sql` — fa da canarino: un
  padre con distinta attiva non torna semplice, e il guard del listino che lo presuppone resta
  irraggiungibile.

---

### Note di migrazione

* 2026-05-22 — nasce, coi primi due controlli.
* 2026-10-13 — si aggiunge il terzo controllo, la distinta a un livello dal lato articolo
  (brief-db-articoli-ammessi-per-documento).
* 2026-11-08 — i tre controlli chiamano i predicati condivisi col form, al posto delle query
  scritte nel corpo (brief-db-revisione-dbops).

---

{% include-markdown "signature-core.md" %}
