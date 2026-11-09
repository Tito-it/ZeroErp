## 📘 Documentazione Concettuale – Trigger function `catalogo.trgfn_unita_misura_guard_tipo`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.unita_misura](/dbzero/catalogo/tabelle/unita_misura) — la tabella su cui è montata
> * [catalogo.uom_tipi](/dbzero/catalogo/tabelle/uom_tipi) — le famiglie, e la famiglia `TEMPO`
> * [catalogo.unita_misura_conversioni](/dbzero/catalogo/tabelle/unita_misura_conversioni) — le conversioni che bloccano il cambio di famiglia
>
> Approfondimento funzioni:
>
> * [catalogo.trgfn_uom_conversioni_guard_tipo](/dbzero/catalogo/funzioni/trgfn_uom_conversioni_guard_tipo) — l'altra metà della regola, sul lato delle conversioni
> * [vendite.fn_articolo_erogazioni](/dbzero/vendite/funzioni/fn_articolo_erogazioni) — il lettore di `conta_dal_calendario`
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — registra e solleva gli errori

---

### 🎯 Scopo Principale

Tiene due regole sulla famiglia (`tipo_uom_id`) di un'unità di misura: non cambia se l'unità
compare in una conversione globale, e un'unità che si conta dal calendario è di famiglia
`TEMPO`.

---

### La famiglia di un'unità usata in una conversione

Una conversione globale collega solo unità della stessa famiglia. La regola ha due porte:
`trgfn_uom_conversioni_guard_tipo` controlla la conversione quando la si scrive, questa
funzione controlla l'unità quando le si cambia la famiglia.

Se la famiglia cambia davvero e l'unità compare in almeno una conversione, da una parte o
dall'altra, attiva o no, in qualunque periodo, il cambio è rifiutato (`E_UOM_TIPO_IN_USO`).
Per cambiare famiglia a un'unità usata si tolgono prima le sue conversioni. Un aggiornamento
che riscrive la stessa famiglia passa: il confronto fra famiglia vecchia e nuova sta nella
funzione.

Le due porte reggono anche la concorrenza: il guard delle conversioni legge le unità
bloccandole in condivisione, quindi un cambio di famiglia e una conversione nuova sulla
stessa unità si aspettano, e chi arriva secondo vede ciò che ha scritto il primo.

---

### Il calendario è del tempo

`conta_dal_calendario` (`GIORNO` o `MESE`) dice che un canone a durata misura la quantità
contando il calendario in questa unità. Ha senso solo per un'unità di tempo: con il valore
pieno, la famiglia dell'unità dev'essere quella con codice interno `TEMPO`, altrimenti
`E_UOM_CALENDARIO_NON_TEMPO`. Il controllo vale alla creazione dell'unità e quando cambiano la
famiglia o il conteggio.

---

### Quando scatta

Prima di ogni inserimento, e degli aggiornamenti che scrivono `tipo_uom_id` o
`conta_dal_calendario`. La regola delle conversioni guarda solo gli aggiornamenti; quella del
calendario anche gli inserimenti. Una famiglia che non esiste la rifiuta la chiave esterna.

---

### Codici errore

* `E_UOM_TIPO_IN_USO` — cambio di famiglia su un'unità che compare in una conversione
  globale. Campo `tipo_uom_id`.
* `E_UOM_CALENDARIO_NON_TEMPO` — conteggio dal calendario su un'unità che non è di famiglia
  `TEMPO`. Campo `conta_dal_calendario`.

Area `catalogo`; in `error_log` col nome della funzione.

---

### Test

* `db/pgtap/catalogo/test-uom-fattore-e-regole-v1.sql` — il cambio di famiglia rifiutato con
  una conversione e ammesso senza; il calendario rifiutato su un'unità di massa e ammesso su
  una di tempo.

---

### Note di migrazione

* 2026-11-09 — prende il posto di `catalogo.trgfn_unita_misura_guard_tipo_update`, che
  sollevava un errore tecnico generico e non conosceva il calendario
  (brief-db-revisione-catalogo, giro 2).

---

{% include-markdown "signature-core.md" %}
