## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_offerte_commerciali_default_valuta()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [vendite.offerte_commerciali](/dbzero/vendite/tabelle/offerte_commerciali)
> • [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)
> • [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)
>
Approfondimento funzioni:
> • [vendite.fn_get_valuta_id](/dbzero/vendite/funzioni/fn_get_valuta_id)
> • [vendite.trgfn_preventivi_default_valuta](/dbzero/vendite/funzioni/trgfn_preventivi_default_valuta)
> • [vendite.trgfn_contratti_default_valuta](/dbzero/vendite/funzioni/trgfn_contratti_default_valuta)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Assegna la **valuta** dell'offerta commerciale quando il chiamante non la indica, chiedendola al resolver
canonico `vendite.fn_get_valuta_id`. La regola di risoluzione non è scritta qui: la catena
**billing account → emittente fiscale → gestore** vive in un posto solo, e questo trigger si
limita a invocarla.

È uno dei tre trigger gemelli — preventivi, offerte commerciali, contratti — con **corpo
identico**: cambia solo la tabella su cui sono agganciati. Un documento di vendita non può
nascere senza valuta, e la valuta non può dipendere da chi lo crea.

---

### Aggancio

Trigger `trg_offerte_commerciali_a10_default_valuta_ins` — fase `_a10_`, **`BEFORE INSERT`** su
`vendite.offerte_commerciali`, `FOR EACH ROW`.

⚠️ Solo `INSERT`. In `UPDATE` il trigger non esiste: azzerare `valuta_id` su un documento
già creato non lo fa ricalcolare.

---

### Regole applicate

1. **Skip se già valorizzata.** `NEW.valuta_id IS NOT NULL` → esce subito. È il caso
   normale quando il backend ha già risolto la valuta, o quando il documento nasce da un
   push a partire da un altro documento: il valore esplicito vince sempre.
2. **Mappa l'emittente.** Se `emittente_fiscale_id` è valorizzato, ne ricava il
   `soggetto_ruolo_id` da `anagrafiche.emittenti_fiscali` — perché il resolver ragiona sul
   ruolo, non sulla PK dell'emittente.
3. **Invoca il resolver**: `vendite.fn_get_valuta_id(billing_account_id, emittente_sr_id)`.

---

### ⚠️ Se nulla risolve, l'inserimento fallisce

`fn_get_valuta_id` è **fail-closed**: esaurita la catena BA → emittente → gestore senza
trovare una valuta, solleva `E_CONFIG_MANCANTE` invece di restituire `NULL`.

È la scelta giusta — un documento senza valuta è un documento senza importi — ma va saputa
quando si prepara un ambiente nuovo: finché la configurazione della valuta di gestore non
esiste, **nessun documento di questo tipo può essere creato**, e l'errore parla di
configurazione mancante, non del documento che si stava salvando.

---

### Codici errore

| Codice | Sollevato da | Quando |
|--------|--------------|--------|
| `E_CONFIG_MANCANTE` | `vendite.fn_get_valuta_id` | Nessuna valuta risolvibile lungo la catena BA → emittente → gestore |

La funzione non solleva errori propri.

---

{% include-markdown "signature-core.md" %}
