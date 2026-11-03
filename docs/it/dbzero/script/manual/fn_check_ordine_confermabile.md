## 📘 Documentazione Concettuale – Funzione `script.fn_check_ordine_confermabile()`

> **Ultimo aggiornamento**: 3 novembre 2026

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [vendite.ordini_righe](/dbzero/vendite/tabelle/ordini_righe)
> • [config.transizioni_stati_ordini](/dbzero/config/tabelle/transizioni_stati_ordini)
>
Approfondimento funzioni:
> • [script.fn_check_ordine_annullabile](/dbzero/script/funzioni/fn_check_ordine_annullabile) — la gemella, stessa forma
> • [script.fn_check_ddt_emittibile](/dbzero/script/funzioni/fn_check_ddt_emittibile) — il cancello equivalente sul DDT
> • [script.fn_check_preventivo_emettibile](/dbzero/script/funzioni/fn_check_preventivo_emettibile) — il terzo gemello
> • [vendite.trgfn_ordini_guard_transizione](/dbzero/vendite/funzioni/trgfn_ordini_guard_transizione) — chi solleva
> • [script.fn_available_actions_ordine](/dbzero/script/funzioni/fn_available_actions_ordine) — chi spegne il bottone

---

### 🎯 Scopo Principale

(rev 2026-11-03 — il motivo dei soli oneri · funzione nata il 2026-08-29)

Elenca i motivi che impediscono di **confermare** un ordine di vendita. Oggi ne ha due,
in quest'ordine:

1. **soli oneri** (dal 2026-11-03, `20261103-26`, K-2 del brief-db-addebito-trasporto-ordine):
   l'ordine ha righe attive ma **nessuna merce** (`script.fn_natura_e_merce` sulla natura
   congelata). Non si evaderebbe mai: un addebito senza merce si scrive in commessa.
   Codice `E_ORDINE_CONFERMA_SOLO_ONERI`, reason `ORDINE_SOLO_ONERI`, reason_key
   `vendite.ordini.azione_reason.solo_oneri`, valori: il numero dell'ordine. ⚠️ Scatta solo
   con righe attive presenti: l'ordine **vuoto** resta della precondizione della matrice
   (`meta.requires_righe`, `E_ORDINE_CONFERMA_SENZA_RIGHE`), che resta fuori da qui;
2. una riga attiva che porta un **prezzo** ma non l'**aliquota**.

Guard di transizione e capability leggono questa funzione: il motivo nuovo è arrivato a
entrambi senza toccarli.

---

### 🔴 Il difetto che chiude, e perché nessuno lo vedeva

`vendite.vw_ordini_righe_iva_base` filtra soltanto `attivo IS TRUE AND quantita > 0`:
**non guarda né il prezzo né `iva_id`**. Da lì `vw_ordini_riepilogo_iva_dettaglio`
aggrega con `COALESCE(aliquota, 0)`.

Una riga senza aliquota entra quindi nel riepilogo con l'**imponibile pieno** e
l'**imposta a zero**, sotto un codice IVA vuoto — su un ordine confermato e stampato.

⚠️ **Nessun errore, nessun sintomo: solo un numero sbagliato.** È lo stesso difetto già
chiuso sul DDT il 2026-08-28, e chiuso sul preventivo lo stesso giorno di questo.

---

### ⭐ Perché è una funzione dell'**azione**, e non «il check completo dell'ordine»

Gemella di `fn_check_ordine_annullabile`, non di `fn_check_ddt_emittibile`: elenca i motivi
di **una** azione, non tutte le precondizioni del documento.

⛔ **In particolare NON contiene «documento senza righe»**, e la scelta va spiegata perché
sembra un'omissione. Quel motivo non è una regola della conferma: è una precondizione
generica **guidata dalla matrice** — `config.transizioni_stati_ordini`, chiave
`meta.requires_righe` — che `fn_available_actions_ordine` applica a *qualunque* transizione
la dichiari.

⚠️ Al 2026-08-29 `requires_righe` risulta vero su **una sola** transizione
(`DRAFT → CONFERMATO`), quindi portarlo qui dentro sembrerebbe innocuo. Ma è una lettura del
**seed**, non del modello: trasformerebbe un meccanismo data-driven in codice cablato sulla
base di una fotografia. Il motivo resta dov'è.

---

### ⚠️ Il perimetro è **qualunque** ingresso in `CONFERMATO`

Il guard chiama questa funzione su `v_codice_a = 'CONFERMATO'`, non sulla coppia
`DRAFT → CONFERMATO`. La matrice ammette il **rientro** da `PARZIALMENTE_EVASO` e da `EVASO`,
e un ordine che torna confermato con una riga senza aliquota produce **lo stesso riepilogo
storto** del percorso diretto.

⭐ *Il vincolo deve avere lo stesso perimetro del consumatore che protegge*: la vista del
riepilogo non sa da dove si arriva.

⚠️ È anche la differenza con la **Regola 2** che gli sta accanto nel guard (riga attiva
obbligatoria), che invece è cablata su `DRAFT → CONFERMATO`. Le due regole hanno perimetri
diversi **di proposito**.

---

### ⚠️ `prezzo_unitario IS NOT NULL` è oggi sempre vero — e si scrive lo stesso

`vendite.ordini_righe.prezzo_unitario` è `NOT NULL`, quindi al momento «riga attiva con
prezzo» coincide con «riga attiva»: **la regola vale di fatto su ogni riga**.

La condizione resta scritta per due ragioni: è la forma **vera** della regola — *dove c'è un
prezzo serve l'aliquota* — e in questo progetto una colonna prezzo è **già** diventata
facoltativa una volta (`20260819-13` su `vendite.ddt_righe_componenti`). Il giorno che
succede qui, la regola è già giusta e nessuno deve accorgersene.

⛔ **Non è, e non poteva essere, un `NOT NULL` di colonna**: `ordini_righe.iva_id` è nullable
e la **bozza deve restare libera**. Il vincolo è alla conferma, non al salvataggio.

---

### ⚠️ Il dettaglio porta il **numero** di riga, non solo l'id

Sono due destinatari diversi: l'`id` serve a chi diagnostica, il `riga_nr` compone la frase
che una persona legge. Nel `VARIADIC` di chi solleva va il **numero** — un id tecnico non si
cerca a mano su un documento.

⚠️ Differenza col gemello sul preventivo: là `preventivi_righe` **non ha `riga_nr`**, e nel
messaggio va la **descrizione**. Le due funzioni non sono copie l'una dell'altra.

---

### Codici errore

| Codice | Motivo |
|--------|--------|
| `E_ORDINE_RIGA_IVA_MANCANTE` | Una riga attiva porta un prezzo ma nessuna aliquota IVA (`CONFLITTO_STATO`, 409) |
| `E_PARAMETRO_INVALIDO` | `ordine_id` nullo o non positivo |

⚠️ Nel contesto **non** va la chiave `campo`: il codice è `CONFLITTO_STATO`, non
`DATO_ERRATO` — la richiesta è «porta l'ordine a `CONFERMATO`», e non c'è un campo di
*quella* richiesta da accendere.

---

### Il pattern `fn_check_*`

**Funzione pura**: `STABLE`, nessuna scrittura, nessun raise di dominio. Ritorna `[]` se
l'azione è permessa, altrimenti un array JSONB ordinato di
`{codice, reason, reason_key, dettaglio}`; chi solleva prende il **primo**.

⭐ **Sorgente unica** per il guard di transizione (che solleva) e per
`fn_available_actions_ordine` (che spegne il bottone ed espone la `reason`): il pulsante
della UI e il rifiuto del database non possono divergere, perché leggono lo stesso verdetto.
Senza il secondo, l'operatore vedrebbe un bottone acceso e prenderebbe un errore al click.

⚠️ Unica eccezione alla purezza: `ordine_id` nullo o `<= 0` solleva `E_PARAMETRO_INVALIDO` —
errore di programmazione, non condizione di dominio.

⚠️ **Ordine inesistente ⇒ `[]`**, cioè «nessun ostacolo»: la funzione non distingue
«confermabile» da «non esiste», e la decisione è del chiamante. Nel percorso reale il guard
gira su un `UPDATE` di una riga che esiste per definizione.

---

### 📌 Debito verso il frontend

La `reason_key` `vendite.ordini.azione_reason.iva_mancante` **non è ancora nei locales** —
la gemella del DDT (`vendite.ddt.azione_reason.iva_mancante`) sì. Finché manca, il tooltip
del pulsante mostra la chiave invece della frase.

Cantiere: `brief-db-be-iva-risolutore-e-regime-cliente.md`, I9.

---

{% include-markdown "signature-core.md" %}
