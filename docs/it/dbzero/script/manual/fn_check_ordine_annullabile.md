## 📘 Documentazione Concettuale – Funzione `script.fn_check_ordine_annullabile()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [vendite.ordini](/dbzero/vendite/tabelle/ordini)
> • [vendite.ddt](/dbzero/vendite/tabelle/ddt)
> • [vendite.commesse_sorgenti](/dbzero/vendite/tabelle/commesse_sorgenti)
>
Approfondimento funzioni:
> • [script.fn_check_preventivo_annullabile](/dbzero/script/funzioni/fn_check_preventivo_annullabile)
> • [vendite.trgfn_ordini_guard_transizione](/dbzero/vendite/funzioni/trgfn_ordini_guard_transizione)

---
### 🎯 Scopo Principale

(rev 2026-08-21 — funzione rev 2026-08-15)

Elenca i motivi che impediscono di **annullare** un ordine: merce già uscita con un DDT figlio
vivo (MOTIVO 1), oppure ordine già entrato in una commessa (MOTIVO 2).

---

### ⚠️ Qui `sorgente_uid` **è** il legame — al contrario del gemello

Il DDT si aggancia al padre con `ddt.sorgente_uid` (uuid, punta all'`uid` dell'ordine) più
`sorgente_tipo_id`. È la catena diretta, e la colonna è popolata.

⛔ **Non trasportare questa forma sul preventivo**: là la colonna omonima è l'origine *import*
e non il legame al padre. È la stessa parola per due cose diverse, ed è precisamente ciò che
ha tenuto spento per tre changeSet il MOTIVO 1 del gemello.

Il MOTIVO 2 usa invece la chiave **`id::text`**, perché per `ORDINE_VENDITA` il `key_selector`
della sorgente polimorfa dice `id` e non `uid`. Tre legami nella stessa funzione, tre chiavi
diverse: non è disordine, è il modello polimorfo.

---

### 🔴 «Asimmetria latente, oggi non morde» — su dati di test

Fino al 2026-08-15 il MOTIVO 1 contava **anche i DDT annullati**, mentre il gemello sul
preventivo li escludeva già dal 10 agosto.

La lacuna era stata classificata *«asimmetria latente, oggi non morde»* perché **nessun DDT
bloccante risultava annullato** — ⚠️ **ma era una conta su dati di TEST**.

In esercizio annullare un DDT è ordinario: destinatario sbagliato, merce sbagliata, duplicato.
L'ordine il cui unico figlio fosse stato annullato sarebbe rimasto bloccato **per sempre**.

⭐ È il caso da tenere a mente ogni volta che una misura sul database di sviluppo dice «non
succede»: la domanda giusta è *«può succedere?»*, non *«è successo?»*.

---

### ⚠️ Esclude solo l'annullato, non il reso

Il predicato è `is_abortito IS NOT TRUE`. Un DDT in stato **RESO** ha `is_abortito = false` e
**continua a bloccare** — ed è giusto: la merce è tornata, ma il documento è vissuto.

---

### Codici errore

| Codice | Motivo |
|--------|--------|
| `E_ORD_ANNULLA_CON_DDT` | Esiste un DDT figlio vivo |
| `E_ORD_ANNULLA_IN_COMMESSA` | L'ordine è già in una commessa |
| `E_PARAMETRO_INVALIDO` | `ordine_id` nullo o non positivo |

---

### Il pattern `fn_check_*`

**Funzione pura**: `STABLE`, nessuna scrittura, nessun raise di dominio. Ritorna `[]` se
l'azione è permessa, altrimenti un array JSONB ordinato di
`{codice, reason, reason_key, dettaglio}` — l'ordine è quello di gravità, chi solleva prende
il **primo**.

⭐ **Sorgente unica** per il guard di transizione (che solleva) e per
`fn_available_actions_*` (che espone `disabled` + `reasons`): il bottone della UI e il rifiuto
del database non possono divergere, perché leggono lo stesso verdetto.

⚠️ Unica eccezione alla purezza: `id` nullo o `<= 0` solleva `E_PARAMETRO_INVALIDO` — errore
di programmazione, non condizione di dominio.

⚠️ **Documento inesistente ⇒ `[]`, cioè «nessun ostacolo».** La funzione non distingue
«annullabile» da «non esiste»: la decisione è lasciata al chiamante. Nel percorso reale il
guard gira su un `UPDATE` di una riga che esiste per definizione, quindi il caso non si
presenta — ma chi la chiamasse da fuori quel percorso deve saperlo.

---

{% include-markdown "signature-core.md" %}
