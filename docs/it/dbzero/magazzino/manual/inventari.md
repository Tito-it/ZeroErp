## 📘 Documentazione Concettuale – Tabella `magazzino.inventari`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.inventari_righe](/dbzero/magazzino/tabelle/inventari_righe) — il dettaglio per articolo
> * [magazzino.magazzini](/dbzero/magazzino/tabelle/magazzini) — l'ancora del perimetro
> * [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti) — dove il conteggio finisce
> * [dbops.automation_lock_columns](/dbzero/dbops/tabelle/automation_lock_columns) — da dove nasce il blocco sul magazzino
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — il catalogo dei tipi di documento
>
> Approfondimento funzioni:
>
> * [magazzino.fn_inventario_piano](/dbzero/magazzino/funzioni/fn_inventario_piano) — che cosa il posting scriverà, riga per riga
> * [magazzino.fn_posta_inventario](/dbzero/magazzino/funzioni/fn_posta_inventario) — l'operazione che registra il conteggio
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

**Il documento di conteggio fisico**: la rilevazione di quanto c'è davvero a scaffale, in un
magazzino, a una data, con uno stato. Il dettaglio per articolo sta nelle righe.

Il conteggio non modifica la giacenza da sé: quando è registrato, diventa la **sorgente** dei
movimenti di allineamento (tipo `INVENTARIO`, con la riga che li ha prodotti), e la giacenza
cambia sul registro. È la catena che tiene il registro come unica fonte: anche una correzione da
inventario è una scrittura tracciata.

---

### Gli stati: bozza, conferma, registrazione

Il documento nasce in `DRAFT`, passa a `CONFIRM` e da lì a `POSTED`; da `DRAFT` o da
`CONFIRM` si può annullare (`CANCEL`). `POSTED` e `CANCEL` sono definitivi. Da `CONFIRM` si
può anche **tornare in bozza**: il piano si legge in `CONFIRM`, e se mostra un errore le righe
si correggono in `DRAFT`.

La matrice degli stati sta in un posto solo,
[fn_documento_interno_transizioni](/dbzero/magazzino/funzioni/fn_documento_interno_transizioni),
la stessa per inventari, rettifiche e trasferimenti: la legge il guard che la fa rispettare e la
leggono i pulsanti del drawer, così l'operatore non vede un'azione che verrebbe rifiutata.

---

### La sorgente dell'inventario

Qui la sorgente è **facoltativa**: dice da quale documento l'operazione è nata, se ce n'è
uno. Quando c'è, `sorgente_tipo_id` è il tipo del documento in
[config.sorgenti](/dbzero/config/tabelle/sorgenti), la sua chiave sta in **una sola** fra
`sorgente_id` e `sorgente_uid` (quella che il catalogo dichiara per quel tipo) e
`sorgente_riga`, se scritta, dice la riga di quel documento; senza tipo, tutte vuote
(`chk_mag_inventari_sorgente_forma`). Il guard unico
[script.trgfn_guard_sorgente](/dbzero/script/funzioni/trgfn_guard_sorgente) verifica che il
documento esista e sia visibile, e che la riga gli appartenga; basta il documento intero. Un
documento citato qui non si può cancellare finché la citazione resta.

---

### Il magazzino si sceglie alla nascita

**`magazzino_id` non si cambia** dopo la creazione, in nessuno stato (blocco delle colonne,
`E_MAG_DOCUMENTO_MAGAZZINO_IMMUTABILE`): il magazzino di un conteggio è **identità**, non un
attributo. Le righe nominano le ubicazioni *di quel* magazzino e
[fn_inventario_piano](/dbzero/magazzino/funzioni/fn_inventario_piano) confronta il contato
con la giacenza *di quel* magazzino; spostando la testata le righe resterebbero a puntare a
posizioni che nel magazzino nuovo non esistono, e il database se ne accorgerebbe solo al
posting, con un errore che racconta un'altra storia
(`E_MAG_UBICAZIONE_DI_ALTRO_MAGAZZINO`). Se il magazzino è sbagliato il conteggio si
annulla e se ne apre uno dove la merce sta davvero.

⚠️ La **`data`** invece resta modificabile, ed è una decisione esplicita: il database non
congela la testata oltre il magazzino. Il trigger del blocco non lo scrive un changeSet: lo
**genera l'automazione** dalla riga in
[dbops.automation_lock_columns](/dbzero/dbops/tabelle/automation_lock_columns).

---

### Chi può vedere e scrivere

Un operatore vede e scrive gli inventari dei magazzini del **proprio emittente**
(`rls_inventari_ef_whitelist`, via magazzino); le righe e le note risalgono alla testata.
Meccanismo comune: [Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls).

---

### Il motore: piano, posting, porte

* **Il piano**: [fn_inventario_piano](/dbzero/magazzino/funzioni/fn_inventario_piano) dice, riga per
  riga e posizione per posizione, che cosa il posting scriverà (`INV_INIZIALE`, `RETT_POS`,
  `RETT_NEG`, `INVARIATA`, `NON_CONTATA`, `NON_POSTABILE`): si legge al passaggio a `CONFIRM`.
* **Il posting**: [fn_posta_inventario](/dbzero/magazzino/funzioni/fn_posta_inventario) posta la
  **differenza** alla grana della riga, con la causale decisa dal piano, in una transazione:
  se una riga fallisce non resta niente, e una sola riga `NON_POSTABILE` ferma tutto il
  documento.
* **La porta `POSTED`**: la apre solo l'operazione, firmandosi per quel documento e girando
  dentro il verbo; l'applicazione da sola non può segnare un inventario come registrato
  ([trgfn_documento_interno_guard_transizione](/dbzero/magazzino/funzioni/trgfn_documento_interno_guard_transizione)).
* **Il `DELETE`** è ammesso solo in `DRAFT`, e le righe se ne vanno con la testata: un
  documento già registrato lascerebbe orfani i movimenti che ha prodotto. Le righe seguono lo
  stato della testata
  ([trgfn_documento_interno_righe_guard_testata](/dbzero/magazzino/funzioni/trgfn_documento_interno_righe_guard_testata)).
* ⚠️ Un debito di nome: gli indici `ix_mag_invetario_stato_inventario` e `ix_mag_invetario_data`
  portano il refuso «invetario». Un indice del passato non si rinomina in corsa: quando servirà,
  si cancella e si ricrea col nome giusto.

---

### Codici errore

* `E_MAG_DOCUMENTO_MAGAZZINO_IMMUTABILE`: si prova a cambiare il magazzino della testata.
* `E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA`: un cambio di stato fuori dalla matrice.
* `E_MAG_DOCUMENTO_POSTED_SOLO_DA_OPERAZIONE`: `POSTED` scritto senza passare dall'operazione.
* `E_MAG_DOCUMENTO_NON_ELIMINABILE`: cancellazione di un documento non in `DRAFT`.

---

### Note di migrazione

* 2026-09-15 — la tabella entra nel primo lotto del magazzino
  (`brief-db-magazzino-lotto-1-terreno-vuoto`, §4.7).
* 2026-09-17 — esce lo stato `COUNTING`: non cambiava nessuna regola.
* 2026-09-18 — arrivano piano e posting; da `CONFIRM` si torna in `DRAFT`; il CHECK sullo stato,
  che portava lo stesso refuso «invetario» dell'indice, prende il nome `chk_mag_inventari_stato`.
* 2026-09-22 — `magazzino_id` diventa immutabile; la `data` resta modificabile per decisione
  esplicita (Q-2 del piano BE/FE). La matrice degli stati passa in
  `fn_documento_interno_transizioni`.
* 2026-09-25 — la porta `POSTED` chiede, oltre alla firma dell'operazione, di girare dentro il
  verbo (`brief-db-magazzino-verbi-con-permesso`).
* 2026-11-08 — la sorgente della testata passa al modello comune (`brief-db-sorgente-documento-e-riga`):
  la chiave del documento in `sorgente_id` o `sorgente_uid`, la riga in `sorgente_riga`, il CHECK
  di forma e il guard unico al posto del guard tipizzato. Esce l'indice unico
  `uq_mag_invetario_sorgente_fk`: nessuna regola di dominio vuole un inventario per documento. I
  movimenti di allineamento citano il documento `INVENTARIO` e la riga, non più il tipo
  `INVENTARIO_RIGA`, ritirato da `config.sorgenti`.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
