## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_ddt_guard_indirizzi_obbligatori()`

> 👀 **Vedi anche**
>
> Tabelle:
> [vendite.ddt](/dbzero/vendite/tabelle/ddt)
> [vendite.ddt_indirizzi](/dbzero/vendite/tabelle/ddt_indirizzi)
> [config.tipi_indirizzi_allowed](/dbzero/config/tabelle/tipi_indirizzi_allowed)
>
> Funzioni correlate:
> [script.fn_indirizzi_obbligatori_mancanti](/dbzero/script/funzioni/fn_indirizzi_obbligatori_mancanti)
>
> Errori:
> [config.messaggi_errore E_INDIRIZZO_DOC_OBBLIGATORIO (id=526)](/dbzero/config/tabelle/messaggi_errore)

---

### 🎯 Scopo Principale

(rev 2026-07-11)

Blocca l'**emissione** di un DDT (transizione a stato `EMESSO`) se manca un tipo
di indirizzo marcato `obbligatorio` per l'ambito `DDT` in
`config.tipi_indirizzi_allowed` — oggi la **destinazione merce `CON`**.

Applicata dal trigger `trg_ddt_a10_guard_indirizzi_obbligatori_upd`
(fase `_a10_`, `BEFORE UPDATE OF stato_doc_ddt_id`).

---

### Perché solo all'emissione (non all'inserimento)

Una bozza legittimamente non ha ancora indirizzi. L'obbligo va verificato al
**cambio di stato** verso l'emissione, non su INSERT. Per questo il guard è su
`BEFORE UPDATE OF stato_doc_ddt_id` e **short-circuita** per stati diversi da
`EMESSO`.

> **DDT-only per ora**: l'analogo su FATTURE non è attivo — nessun percorso
> popola ancora `fatture_indirizzi` (cascata verso fattura = cantiere
> fatturazione). Il metadato `FATT@FATTURE obbligatorio` è comunque seedato e il
> guard fattura si accenderà con quella cascata, riusando lo stesso helper.

---

### Logica

1. Risolve il `codice_interno` dello stato target. Se ≠ `EMESSO` → RETURN NEW.
2. Raccoglie i `tipo_indirizzo_id` già presenti su `vendite.ddt_indirizzi` per
   il DDT.
3. `v_mancanti := script.fn_indirizzi_obbligatori_mancanti('DDT', v_presenti)`.
4. Se `v_mancanti` non è vuoto → `E_INDIRIZZO_DOC_OBBLIGATORIO` con contesto
   JSONB (`ddt_id`, `numero`, `ambito`, `mancanti`).

---

### Casi d'uso

| Scenario | Comportamento |
|---|---|
| DDT da evasione con CON copiato dall'ordine → EMESSO | Passa |
| DDT con indirizzo CON aggiunto a mano → EMESSO | Passa |
| DDT privo di CON → EMESSO | **Errore** `E_INDIRIZZO_DOC_OBBLIGATORIO` |
| Qualsiasi transizione a stato ≠ EMESSO | Passa (short-circuit) |

---

### Errori sollevati

| Codice | id | Quando | Contesto JSONB |
|---|---|---|---|
| `E_INDIRIZZO_DOC_OBBLIGATORIO` | 526 | All'emissione (EMESSO) manca un tipo indirizzo obbligatorio per l'ambito DDT | `ddt_id`, `numero`, `ambito`, `mancanti` |

---

### Note operative

- La regola "quali tipi sono obbligatori" vive in `config.tipi_indirizzi_allowed`
  (colonna `obbligatorio`), non nel codice: cambiare l'obbligo = cambiare il seed.
- I DDT creati direttamente in stato `EMESSO` via INSERT (scorciatoie di test)
  **non** passano da questo guard, che è `BEFORE UPDATE` — coerente con gli altri
  guard di transizione DDT.

---

{% include-markdown "signature-core.md" %}
