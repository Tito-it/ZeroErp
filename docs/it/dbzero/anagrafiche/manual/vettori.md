## 📘 Documentazione Concettuale – Tabella `anagrafiche.vettori`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)
> • [config.tipi_ruoli](/dbzero/config/tabelle/tipi_ruoli)
> • [vendite.ddt](/dbzero/vendite/tabelle/ddt)
>
Approfondimento funzioni:
> • [anagrafiche.trgfn_vettori_guard_ruolo_vettore](/dbzero/anagrafiche/funzioni/trgfn_vettori_guard_ruolo_vettore)
> • [anagrafiche.trgfn_vettori_gen_codice](/dbzero/anagrafiche/funzioni/trgfn_vettori_gen_codice)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Dettaglio del **ruolo vettore** (`VT`): chi trasporta la merce. È referenziata da
`vendite.ddt.vettore_soggetto_ruolo_id`, dove compare sul documento di trasporto insieme a
mittente e destinatario.

Segue il pattern di tutti i dettagli di ruolo del progetto: **FK 1:1 al `soggetto_ruolo`**
(`uq_vettori_ruolo`), non al soggetto. Lo stesso soggetto può essere cliente *e* vettore, e
sono due ruoli distinti con dettagli distinti.

`trgfn_vettori_guard_ruolo_vettore` impedisce di agganciare la riga a un ruolo che non sia
`VT`.

---

### ⚠️ Oggi è **vuota**

Misurato il 2026-08-21: **zero righe**. Il ruolo esiste nel modello, il DDT ha la sua colonna,
ma nessun vettore è ancora stato anagrafato.

Va letta come predisposizione: il documento di trasporto può già indicare un vettore, ma nella
pratica corrente non lo fa.

---

### Il codice si genera da solo — **dal 2026-08-21**

`codice` è `NOT NULL` e `UNIQUE` (`uq_vettori_codice`). Fino al 2026-08-21 **nessuno lo
generava**: niente riga in `config.sistema_codici`, nessun trigger. Un `INSERT` che lo ometteva
falliva con una violazione di vincolo (`23502`), senza nessun codice `E_*` a spiegarlo — mentre
`trgfn_vettori_normalize`, un no-op, dichiarava nel proprio `COMMENT` che la generazione era
«demandata al sistema_codici».

Oggi la riga in `config.sistema_codici` c'è (prefisso `VET`, 7 cifre) e l'automazione ha
generato sequenza, funzione e trigger. Una volta scritto, il codice è immutabile
(`trg_vettori_a10_lock_columns_upd`).

---

### Struttura

`uid` (uuidv7) come chiave esterna stabile, `codice`, `descrizione` (⚠️ **`NOT NULL` senza
default**: va sempre valorizzata), `attivo`, `meta`, `tx_id`, `storicizza` e l'audit standard.

C'è anche `trg_vettori_a10_delete_block_dlt`: i vettori **non si cancellano**, si disattivano —
un DDT storico non deve perdere il riferimento a chi ha trasportato la merce.

---

{% include-markdown "signature-core.md" %}
