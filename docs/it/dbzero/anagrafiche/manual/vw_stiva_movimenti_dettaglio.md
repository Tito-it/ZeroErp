## 📘 Documentazione Concettuale – Vista `anagrafiche.vw_stiva_movimenti_dettaglio`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti_titoli_iva_movimenti](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva_movimenti) — il registro che proietta
> * [anagrafiche.soggetti_titoli_iva](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva) — il titolo, da cui arrivano soggetto ed emittente
>
> Approfondimento viste:
>
> * [vendite.vw_resi_righe_dettaglio](/dbzero/vendite/views/vw_resi_righe_dettaglio) — la gemella, con lo stesso modo di portare il motivo di blocco
>
> Approfondimento funzioni:
>
> * [script.fn_check_annullo_movimento_titolo_iva](/dbzero/script/funzioni/fn_check_annullo_movimento_titolo_iva) — chi decide il motivo di blocco
> * [anagrafiche.fn_annulla_movimento_titolo_iva](/dbzero/anagrafiche/funzioni/fn_annulla_movimento_titolo_iva) — il verbo che il pulsante chiama

---

### 🎯 Scopo Principale

`anagrafiche.vw_stiva_movimenti_dettaglio` mostra le righe del registro del plafond di un titolo IVA per il drawer
di dettaglio: il movimento, il tipo di titolo, il legame dell'annullo nei due versi e il motivo per cui il pulsante
«Annulla» è spento.

---

### ⭐ Il pulsante si trova già spento, col motivo

L'operatore deve vedere che una forzatura non si può annullare prima di premere, e perché. Il pulsante vive sul
registro di un titolo, quindi il motivo va sulle righe di quel registro: questa vista è la superficie che lo porta.

Il motivo lo dà `script.fn_check_annullo_movimento_titolo_iva`, la stessa funzione che la porta dell'annullo
interroga per rifiutare: il pulsante spento e il rifiuto non possono divergere.

---

### Le colonne che non sono una proiezione

| Colonna | Che cosa dice |
| --- | --- |
| `annulla_movimento_id` | che cosa annulla questa riga, sulle sole righe di annullo |
| `annullato_da_movimento_id` | chi annulla questa riga: il verso inverso, per barrarla e rimandare all'annullo |
| `is_annullo`, `is_annullato` | i due versi come flag |
| `annullo_blocco_codice` | il motivo per cui «Annulla» è spento, come codice macchina della check (non il codice errore); vuoto = annullo ammesso |
| `annullo_blocco_reason_key` | la chiave della frase del motivo |

Il nome dice per quale azione è il blocco: una colonna generica «bloccato» la riuserebbe il prossimo verbo, e
direbbe due cose insieme.

---

### Perimetro e forma

La vista gira coi permessi di chi la legge, e passa dal titolo: è da lì che arrivano soggetto ed emittente, e la
RLS del titolo e del registro decide che cosa si vede. La vista è sicura da sola, senza contare sul servizio che la
interroga.

Proietta e basta: nessun filtro e nessun ordinamento, che sono di chi chiama. La check gira una volta per riga, ed è
la forma prevista per un'azione di riga: si guarda il registro di un titolo, non una lista di tutti.

---

### Test

* `db/pgtap/anagrafiche/test-stiva-movimenti-annullo-v1.sql` — la vista espone il motivo di blocco, e coincide con
  ciò che la porta dell'annullo rifiuta.

---

### Note di migrazione

* 2026-08-30 — nasce con l'annullo delle forzature: prima per questo registro non c'era nessuna vista, e il motivo
  di blocco non poteva arrivare a video.

---

{% include-markdown "signature-core.md" %}
