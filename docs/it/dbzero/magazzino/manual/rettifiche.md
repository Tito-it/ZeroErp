## 📘 Documentazione Concettuale – Tabella `magazzino.rettifiche`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.rettifiche_righe](/dbzero/magazzino/tabelle/rettifiche_righe) — il dettaglio per articolo
> * [magazzino.magazzini](/dbzero/magazzino/tabelle/magazzini) — l'ancora del perimetro
> * [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti) — dove la rettifica finisce
> * [dbops.automation_lock_columns](/dbzero/dbops/tabelle/automation_lock_columns) — da dove nasce il blocco sul magazzino
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — il catalogo dei tipi di documento
>
> Approfondimento funzioni:
>
> * [magazzino.fn_posta_rettifica](/dbzero/magazzino/funzioni/fn_posta_rettifica) — l'operazione che registra la rettifica
> * [magazzino.fn_documento_interno_transizioni](/dbzero/magazzino/funzioni/fn_documento_interno_transizioni) — la matrice degli stati
> * [magazzino.trgfn_documento_interno_guard_transizione](/dbzero/magazzino/funzioni/trgfn_documento_interno_guard_transizione) — chi la fa rispettare
> * [script.trgfn_guard_sorgente](/dbzero/script/funzioni/trgfn_guard_sorgente) — il guard unico della sorgente
>
> Guide:
>
> * [Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls) — il meccanismo comune del perimetro
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello tipo, documento, riga

---

### 🎯 Scopo Principale

**Il documento di rettifica**: la correzione dichiarata di una giacenza, in un magazzino, a
una data, con uno stato (`DRAFT` → `CONFIRM` → `POSTED`, o `CANCEL`). Il dettaglio, quanto
in più o in meno per articolo, sta nelle righe.

⭐ **La correzione a mano è una rettifica**: non esiste un movimento senza operazione a monte,
quindi chi deve sistemare una giacenza scrive qui, e la rettifica diventa la sorgente dei
movimenti (tipo `RETTIFICA`, con la riga che li ha prodotti; causali `RETT_POS` / `RETT_NEG`).

---

### La sorgente della rettifica

Qui la sorgente è **facoltativa**: dice da quale documento l'operazione è nata, se ce n'è
uno. Quando c'è, `sorgente_tipo_id` è il tipo del documento in
[config.sorgenti](/dbzero/config/tabelle/sorgenti), la sua chiave sta in **una sola** fra
`sorgente_id` e `sorgente_uid` (quella che il catalogo dichiara per quel tipo) e
`sorgente_riga`, se scritta, dice la riga di quel documento; senza tipo, tutte vuote
(`chk_mag_rettifiche_sorgente_forma`). Il guard unico
[script.trgfn_guard_sorgente](/dbzero/script/funzioni/trgfn_guard_sorgente) verifica che il
documento esista e sia visibile, e che la riga gli appartenga; basta il documento intero. Un
documento citato qui non si può cancellare finché la citazione resta.

---

### Il magazzino si sceglie alla nascita

**`magazzino_id` non si cambia** dopo la creazione, in nessuno stato (blocco delle colonne,
`E_MAG_DOCUMENTO_MAGAZZINO_IMMUTABILE`): il magazzino di una correzione è **identità**, non un
attributo. Le righe nominano le ubicazioni *di quel* magazzino e il posting scrive il delta
sulla giacenza *di quel* magazzino; spostando la testata le righe resterebbero a puntare a
posizioni che nel magazzino nuovo non esistono, e il database se ne accorgerebbe solo al
posting, con un errore che racconta un'altra storia (`E_MAG_UBICAZIONE_DI_ALTRO_MAGAZZINO`).
Se il magazzino è sbagliato la rettifica si annulla e se ne apre una dove la merce sta
davvero.

⚠️ La **`data`** invece resta modificabile, ed è una decisione esplicita: il database non
congela la testata oltre il magazzino. Il trigger del blocco non lo scrive un changeSet: lo
**genera l'automazione** dalla riga in
[dbops.automation_lock_columns](/dbzero/dbops/tabelle/automation_lock_columns).

---

### Chi può vedere e scrivere

Un operatore vede e scrive le rettifiche dei magazzini del **proprio emittente**
(`rls_rettifiche_ef_whitelist`, via magazzino); righe e note risalgono alla testata.
Meccanismo comune: [Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls).

---

### Il motore

[fn_posta_rettifica](/dbzero/magazzino/funzioni/fn_posta_rettifica) posta il delta **dato** di ogni
riga (`RETT_POS` o `RETT_NEG` secondo il segno), in una transazione; una rettifica negativa
ignora i blocchi (che sono una promessa) ma non la giacenza fisica (`is_rettifica`). La matrice
degli stati è la stessa degli inventari
([fn_documento_interno_transizioni](/dbzero/magazzino/funzioni/fn_documento_interno_transizioni)),
compreso il ritorno da `CONFIRM` a `DRAFT`; la porta `POSTED` la apre solo l'operazione, dentro
il verbo, e il `DELETE` è ammesso solo in `DRAFT`
([trgfn_documento_interno_guard_transizione](/dbzero/magazzino/funzioni/trgfn_documento_interno_guard_transizione)).

---

### Codici errore

* `E_MAG_DOCUMENTO_MAGAZZINO_IMMUTABILE`: si prova a cambiare il magazzino della testata.
* `E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA`: un cambio di stato fuori dalla matrice.
* `E_MAG_DOCUMENTO_POSTED_SOLO_DA_OPERAZIONE`: `POSTED` scritto senza passare dall'operazione.
* `E_MAG_DOCUMENTO_NON_ELIMINABILE`: cancellazione di un documento non in `DRAFT`.

---

### Note di migrazione

* 2026-09-14 — la correzione a mano passa obbligatoriamente da una rettifica; `sorgente_tipo_id`,
  che fino ad allora poteva puntare a un tipo inesistente, riceve la FK verso
  `config.sorgenti` e il guard tipizzato.
* 2026-09-15 — la tabella entra nel primo lotto del magazzino
  (`brief-db-magazzino-lotto-1-terreno-vuoto`, §4.7).
* 2026-09-18 — arriva il posting (`fn_posta_rettifica`).
* 2026-09-22 — `magazzino_id` diventa immutabile; la `data` resta modificabile per decisione
  esplicita (Q-2 del piano BE/FE).
* 2026-09-25 — la porta `POSTED` chiede, oltre alla firma dell'operazione, di girare dentro il
  verbo (`brief-db-magazzino-verbi-con-permesso`).
* 2026-11-08 — la sorgente della testata passa al modello comune (`brief-db-sorgente-documento-e-riga`):
  la chiave del documento in `sorgente_id` o `sorgente_uid`, la riga in `sorgente_riga`, il CHECK
  di forma e il guard unico al posto del guard tipizzato; esce l'indice unico sulla sorgente. I
  movimenti citano il documento `RETTIFICA` e la riga, non più il tipo `RETTIFICA_RIGA`, ritirato
  da `config.sorgenti`.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
