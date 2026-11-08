## 📘 Documentazione Concettuale – Tabella `magazzino.trasferimenti`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.trasferimenti_righe](/dbzero/magazzino/tabelle/trasferimenti_righe) — il dettaglio per articolo
> * [magazzino.magazzini](/dbzero/magazzino/tabelle/magazzini) — origine e destinazione
> * [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti) — le due righe di uscita e di entrata
> * [vendite.ddt](/dbzero/vendite/tabelle/ddt) — il trasferimento con trasporto, che non passa da qui
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — il catalogo dei tipi di documento
>
> Approfondimento funzioni:
>
> * [magazzino.fn_posta_trasferimento](/dbzero/magazzino/funzioni/fn_posta_trasferimento) — l'operazione che registra il trasferimento
> * [magazzino.trgfn_trasferimenti_guard_stesso_emittente](/dbzero/magazzino/funzioni/trgfn_trasferimenti_guard_stesso_emittente) — origine e destinazione dello stesso emittente
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

**Il documento di trasferimento interno**: lo spostamento di merce dentro lo stesso magazzino,
fra due ubicazioni, oppure fra due magazzini dello stesso emittente, **senza documento di
trasporto**. Dice da dove parte la merce (`magazzino_id_from`), dove arriva
(`magazzino_id_to`), quando e in che stato; il dettaglio per articolo sta nelle righe.

Un trasferimento genera **due movimenti** per riga, `TRASF_OUT` dalla partenza e `TRASF_IN`
nell'arrivo, con la stessa sorgente (il documento `TRASFERIMENTO` e la riga) e causali diverse:
è così che le due righe non collidono nell'identità del registro. Il costo dell'entrata è ereditato da quello
dell'uscita: spostare merce non cambia il suo valore, lo sposta.

---

### Interno, non con trasporto

Il trasferimento con trasporto fra due depositi non è questo documento: è il DDT con causale
`TRASFERIMENTO` ([vendite.ddt](/dbzero/vendite/tabelle/ddt), causali in
`config.causali_trasporto`), che porta il proprio magazzino di partenza e di arrivo.

---

### Due magazzini, un emittente solo

Origine e destinazione devono appartenere allo **stesso emittente**: fra due emittenti
sarebbe una cessione con un documento, non uno spostamento. Lo fa rispettare il guard
[trgfn_trasferimenti_guard_stesso_emittente](/dbzero/magazzino/funzioni/trgfn_trasferimenti_guard_stesso_emittente)
(`E_MAG_TRASFERIMENTO_EMITTENTI_DIVERSI`, con il campo della destinazione acceso nel form).

---

### Lo stesso magazzino è ammesso, la stessa posizione no

Partenza e arrivo possono essere lo **stesso magazzino**: è lo spostamento fra due ubicazioni.
Allora ogni riga deve dire da quale ubicazione parte e in quale arriva, e le due devono essere
diverse: due ubicazioni uguali le rifiuta già la riga, una riga senza le due ubicazioni la
rifiuta la registrazione (`E_MAG_TRASFERIMENTO_STESSA_POSIZIONE`), perché partenza e arrivo
coinciderebbero.

---

### La sorgente del trasferimento

Qui la sorgente è **facoltativa**: dice da quale documento l'operazione è nata, se ce n'è
uno. Quando c'è, `sorgente_tipo_id` è il tipo del documento in
[config.sorgenti](/dbzero/config/tabelle/sorgenti), la sua chiave sta in **una sola** fra
`sorgente_id` e `sorgente_uid` (quella che il catalogo dichiara per quel tipo) e
`sorgente_riga`, se scritta, dice la riga di quel documento; senza tipo, tutte vuote
(`chk_mag_trasferimenti_sorgente_forma`). Il guard unico
[script.trgfn_guard_sorgente](/dbzero/script/funzioni/trgfn_guard_sorgente) verifica che il
documento esista e sia visibile, e che la riga gli appartenga; basta il documento intero. Un
documento citato qui non si può cancellare finché la citazione resta.

---

### Il motore

Gli stati sono quelli degli inventari e delle rettifiche (`DRAFT` → `CONFIRM` → `POSTED`, o
`CANCEL`, con il ritorno da `CONFIRM` a `DRAFT`), dalla stessa matrice
([fn_documento_interno_transizioni](/dbzero/magazzino/funzioni/fn_documento_interno_transizioni)).
[fn_posta_trasferimento](/dbzero/magazzino/funzioni/fn_posta_trasferimento) registra un
trasferimento confermato: per ogni riga scrive l'uscita dal magazzino e dall'ubicazione di
partenza e l'entrata in quelli di arrivo, legate dall'identificativo del trasferimento perché
l'entrata prenda il costo dell'uscita, e porta il documento a `POSTED`, tutto in una
transazione. La porta `POSTED` la apre solo l'operazione, dentro il verbo, e il `DELETE` è
ammesso solo in `DRAFT`
([trgfn_documento_interno_guard_transizione](/dbzero/magazzino/funzioni/trgfn_documento_interno_guard_transizione)).

---

### Chi può vedere e scrivere

Il perimetro poggia sul magazzino di **origine** (`rls_trasferimenti_ef_whitelist`, via
`magazzino_id_from`); la destinazione la copre il guard sullo stesso emittente. Righe e note
risalgono alla testata.
Meccanismo comune: [Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls).

---

### Codici errore

* `E_MAG_TRASFERIMENTO_EMITTENTI_DIVERSI`: origine e destinazione di emittenti diversi.
* `E_MAG_TRASFERIMENTO_STESSA_POSIZIONE`: alla registrazione, una riga nello stesso magazzino
  senza le due ubicazioni.
* `E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA`: un cambio di stato fuori dalla matrice.
* `E_MAG_DOCUMENTO_POSTED_SOLO_DA_OPERAZIONE`: `POSTED` scritto senza passare dall'operazione.
* `E_MAG_DOCUMENTO_NON_ELIMINABILE`: cancellazione di un documento non in `DRAFT`.

---

### Note di migrazione

* 2026-09-14 — esce il doppione delle colonne sorgente (`sorgenti_*` accanto a `sorgente_*`, che
  dicevano la stessa cosa); il CHECK che doveva rifiutare un trasferimento da un magazzino a se
  stesso, scritto in modo da non rifiutare nulla, viene corretto.
* 2026-09-15 — la tabella entra nel primo lotto del magazzino
  (`brief-db-magazzino-lotto-1-terreno-vuoto`, §4.7; analisi carico e scarico, §7-sexies).
* 2026-09-17 — si decide che il trasferimento è solo quello **interno** (D-L2-g): quello con
  trasporto è il DDT.
* 2026-09-28 — arriva il posting (`fn_posta_trasferimento`, `brief-db-magazzino-lotto-3-scarico-da-ddt`);
  lo stesso magazzino in partenza e in arrivo diventa ammesso, con le ubicazioni di partenza e
  di arrivo sulle righe.
* 2026-11-08 — la sorgente della testata passa al modello comune (`brief-db-sorgente-documento-e-riga`):
  la chiave del documento in `sorgente_id` o `sorgente_uid`, la riga in `sorgente_riga`, il CHECK
  di forma e il guard unico al posto del guard tipizzato; esce l'indice unico sulla sorgente. I
  movimenti citano il documento `TRASFERIMENTO` e la riga, non più il tipo `TRASFERIMENTO_RIGA`,
  ritirato da `config.sorgenti`.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
