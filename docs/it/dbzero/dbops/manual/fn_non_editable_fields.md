## 📘 Documentazione Concettuale – Funzione `dbops.fn_non_editable_fields`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.lock_columns_conditional](/dbzero/dbops/tabelle/lock_columns_conditional) — le regole di blocco che dipendono dallo stato della riga
> * [dbops.automation_lock_columns](/dbzero/dbops/tabelle/automation_lock_columns) — le colonne bloccate sempre
>
> Approfondimento viste:
>
> * [dbops.vw_non_editable_fields](/dbzero/dbops/views/vw_non_editable_fields) — i blocchi incondizionati, letti dai trigger di lock vivi
>
> Approfondimento funzioni:
>
> * [dbops.fn_lock_columns_divergenze](/dbzero/dbops/funzioni/fn_lock_columns_divergenze) — il confronto fra il lock vivo e il registro
> * [catalogo.fn_articolo_padre_di_distinta_da_oggi](/dbzero/catalogo/funzioni/fn_articolo_padre_di_distinta_da_oggi), [catalogo.fn_articolo_componente_di_distinta_in_vigore](/dbzero/catalogo/funzioni/fn_articolo_componente_di_distinta_in_vigore), [catalogo.fn_articolo_primo_padre_da_oggi](/dbzero/catalogo/funzioni/fn_articolo_primo_padre_da_oggi), [catalogo.fn_articolo_usato](/dbzero/catalogo/funzioni/fn_articolo_usato) — i predicati che le regole dell'articolo condividono coi guard
> * [catalogo.trgfn_articoli_guard_flags_struttura_bom_attiva](/dbzero/catalogo/funzioni/trgfn_articoli_guard_flags_struttura_bom_attiva) — un guard che rifiuta il salvataggio che la funzione annuncia

---

### 🎯 Scopo Principale

Le colonne non modificabili di **una riga precisa**: i blocchi incondizionati della tabella più i
blocchi condizionali che, valutati su quella riga, risultano veri. Restituisce un elenco senza
ripetizioni, in ordine alfabetico, e mai nullo: vuoto se non c'è nessun blocco.

Il backend la usa nelle schede di dettaglio per dire al frontend quali campi presentare in sola
lettura.

---

### Due fonti, una risposta

| Blocco | Da dove | Quando vale |
| --- | --- | --- |
| incondizionato | `dbops.vw_non_editable_fields` (le colonne che un trigger di lock vivo blocca, `codice_interno` compreso) | sempre |
| condizionale | le regole abilitate di `dbops.lock_columns_conditional` per quella tabella | quando la condizione, valutata sull'identificativo della riga, è vera |

Ogni regola condizionale è un'espressione booleana che riceve l'identificativo della riga come
parametro, passato come testo: la conversione al tipo della chiave la fa l'espressione stessa.
L'identificativo entra come parametro, non incollato nel testo, quindi non può iniettare niente;
l'espressione invece viene dal registro e la scrive chi scrive il seed. Una condizione che non dà
vero (falsa o nulla) non blocca.

⚠️ Un'espressione condizionale che fallisce fa fallire la chiamata intera, non solo la sua regola.

---

### ⚠️ Annuncia, non difende

La funzione dice al frontend che cosa è bloccato; a rifiutare il salvataggio sono i trigger del
database. Sono due difese indipendenti di proposito: se l'annuncio manca, il database rifiuta lo
stesso.

⭐ **Perché l'annuncio sia vero, legge le stesse regole di chi difende.** I blocchi incondizionati
vengono dai trigger stessi (`dbops.vw_non_editable_fields`), quindi coincidono con ciò che l'UPDATE
rifiuta. Un blocco condizionale chiama lo **stesso predicato** del guard che rifiuterebbe la
modifica: per l'articolo, i predicati della distinta (`catalogo.fn_articolo_padre_di_distinta_da_oggi`,
`…_componente_di_distinta_in_vigore`, `…_primo_padre_da_oggi`) e `catalogo.fn_articolo_usato`.
Una regola che ricopiasse la condizione del guard prima o poi risponderebbe in un altro modo.

---

### Legge con gli occhi di chi chiama

La funzione gira coi privilegi del chiamante: le tabelle che le espressioni condizionali leggono
devono essere leggibili dal ruolo applicativo, e con la row level security accesa le espressioni
vedono solo le righe del perimetro di chi chiama. È volatile: legge lo stato corrente, e due
chiamate nella stessa transazione possono rispondere diversamente se i dati cambiano in mezzo.

---

### Test

* `db/pgtap/dbops/test-fn-non-editable-fields-conditional.sql` — blocchi incondizionati e
  condizionali insieme, sulla stessa riga.
* `db/pgtap/dbops/test-non-editable-fields-dal-lock-vivo-v1.sql` — i blocchi incondizionati vengono
  dal trigger vivo, `codice_interno` compreso.
* `db/pgtap/catalogo/test-distinta-predicati-guard-e-form-v1.sql` — per i flag di struttura
  dell'articolo il form e il guard rispondono uguale.
* `db/pgtap/catalogo/test-articolo-usato-struttura-v1.sql`,
  `test-distinta-un-livello-e-onere-natura-v1.sql` e `db/pgtap/vendite/test-righe-articolo-ammesso-v1.sql`
  — le regole condizionali dell'articolo e delle righe, lette come le legge il backend.

---

### Note di migrazione

* 2026-05-22 — nasce con il registro dei blocchi condizionali, per i flag di struttura dell'articolo
  bloccati quando l'articolo è padre di una distinta attiva.
* 2026-11-08 — i blocchi incondizionati vengono dai trigger vivi, `codice_interno` compreso, e le
  regole della distinta chiamano i predicati del guard (`20261109-61`, `-64`,
  brief-db-revisione-dbops D25 e D28).

---

{% include-markdown "signature-core.md" %}
