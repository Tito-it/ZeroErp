## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_indirizzo_elemento_dettaglio()`

> 👀 **Vedi anche**
>
[anagrafiche.fn_indirizzo_elemento](/dbzero/anagrafiche/manual/fn_indirizzo_elemento)
> [anagrafiche.fn_create_indirizzo](/dbzero/anagrafiche/funzioni/fn_create_indirizzo)

---
### 🎯 Scopo Principale
(18-10-2026 — decisione D-4 di Tid)

**L'indirizzo normalizzato di un elemento** già letto da `fn_indirizzo_elemento`:

| L'elemento porta | Ritorna |
| --- | --- |
| `indirizzo_libero` (non vuoto) | `NULL`: la riga è libera |
| `indirizzo_dettaglio_id` | quello |
| una via (`stradario_id`, oppure una via nuova con comune e CAP) e il civico | il dettaglio risolto da `anagrafiche.fn_create_indirizzo`, che non duplica |

Non controlla i campi di una via nuova: lo fa il backend prima di chiamare, come per
`fn_create_indirizzo`.

Lo chiamano le due madri degli indirizzi; quella del ruolo lo chiama solo per gli indirizzi
che scrive davvero (quelli che il ruolo ha già si saltano prima).

---

{% include-markdown "signature-core.md" %}
