## 📘 Documentazione Concettuale – Funzione `script.trgfn_righe_natura_vendita`

> 👀 **Vedi anche**
>
> [vendite.preventivi_righe](/dbzero/vendite/tabelle/preventivi_righe) · [vendite.ordini_righe](/dbzero/vendite/tabelle/ordini_righe) · [vendite.ddt_righe](/dbzero/vendite/tabelle/ddt_righe) — le tre tabelle su cui è montata
> [config.nature_vendita](/dbzero/config/manual/nature_vendita) — il vocabolario delle nature
> [script.trgfn_righe_guard_articolo_ammesso](/dbzero/script/manual/trgfn_righe_guard_articolo_ammesso) — il guard delle regole sulle righe, che legge la natura scritta qui

### 🎯 Scopo Principale

(latest review 2026-10-13, brief-db-articoli-ammessi-per-documento A-4; `20261013-14`)

La natura di vendita di una riga (merce, servizio una tantum, servizio ricorrente) è quella
**con cui la riga è stata venduta**. Si scrive quando la riga nasce e quando cambia l'articolo,
poi resta: un cambio di natura dell'articolo in anagrafica non tocca le righe già scritte.

È ciò che permette alle regole sulle righe (un ordine e una bolla ammettono solo merce) di
giudicare la riga per quello che è stata venduta. Se la natura si leggesse viva dall'articolo,
un cambio in anagrafica renderebbe «sbagliata» una riga già venduta, e il passo dopo (la bolla)
la rifiuterebbe per una modifica fatta altrove.

---

### La regola

| Quando | Che natura prende la riga |
| --- | --- |
| **INSERT**, modo `ARTICOLO` | quella dell'articolo, qualunque cosa porti chi scrive |
| **INSERT**, modo `CHIAMANTE` | quella portata da chi scrive, se la porta; altrimenti quella dell'articolo |
| **UPDATE** che cambia l'articolo | quella del nuovo articolo: la riga è diventata un'altra vendita |
| **UPDATE** con lo stesso articolo | questa funzione non la tocca: una scrittura a mano la giudica il lock di colonna (sotto) |

Il modo si sceglie nel montaggio (`TG_ARGV[0]`):

| Tabella | Modo | Perché |
| --- | --- | --- |
| `vendite.preventivi_righe` | `ARTICOLO` | il preventivo è dove la vendita nasce: la natura viene sempre dall'articolo |
| `vendite.ordini_righe` | `CHIAMANTE` | `fn_push_preventivo_a_ordine` porta quella della riga di preventivo |
| `vendite.ddt_righe` | `CHIAMANTE` | `fn_genera_ddt_da_ordine` porta quella della riga d'ordine, `fn_genera_ddt_riconsegna` quella della riga di bolla resa |

⚠️ Il modo `CHIAMANTE` si fida di chi scrive la colonna. Oggi la scrivono solo i tre verbi DB
qui sopra: il backend non conosce la colonna, quindi una riga scritta da lui prende la natura
dell'articolo.

Un modo diverso dai due solleva `E_TRIGGER_ARGOMENTI_INVALIDI`.

---

### Chi rifiuta la natura scritta a mano

Non questa funzione: il **lock di colonna** generato da `dbops.automation_lock_columns`
(`…_a10_lock_columns_upd`, codice `E_RIGA_NATURA_VENDITA_IMMUTABILE`). Il lock viene **prima**
di questo trigger nell'ordine dei nomi, e l'ordine è portante:

```
…_a10_lock_columns_upd          giudica il valore di chi scrive
…_a10_natura_vendita_ins_upd    questo: scrive la natura (nascita, cambio di articolo)
…_a10_regole_articolo_ins_upd  il guard delle regole sulle righe, legge la natura
```

Invertendo lock e scrittura, il lock vedrebbe la natura nuova di un cambio di articolo
legittimo e lo rifiuterebbe.

La regola «non si scrive a mano» sta **solo** nel lock, con la sua porta di manutenzione
(`SET LOCAL zeroerp.allow_lock_columns_override = 'on'`). Fino al `20261013-14` questa funzione
rimetteva anche lei la natura a `OLD` «per difesa», a parità di articolo: era una seconda copia
della regola, e già diversa, perché non conosceva la porta e la richiudeva in silenzio. Il caso
che lo ha mostrato è la riga di preventivo a natura `NULL`: la colonna è nullable (il pregresso
nato prima dell'ereditarietà), e quello stato si costruisce solo dalla porta.

---

### Montaggio

`BEFORE INSERT OR UPDATE OF articolo_id, natura_vendita_id`, fascia `_a10_`, sulle tre tabelle
(`20261013-09`). Nessun altro trigger `BEFORE` delle tre tabelle scrive `articolo_id`.

---
{% include-markdown "signature-core.md" %}
