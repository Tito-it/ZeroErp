## 📘 Documentazione Concettuale – Tabella `magazzino.causali`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti)
> • [magazzino.ambito_causale](/dbzero/magazzino/tabelle/ambito_causale)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

**La causale decide come si comporta un movimento.** Non è un'etichetta descrittiva: è la
riga di configurazione che stabilisce segno, obblighi e impatto sulla valorizzazione.

È uno dei due soli oggetti popolati dello schema: **10 righe** da seed.

| Codice | Segno | Valorizzazione |
|---|---:|---|
| `CARICO_ACQ` | +1 | `cmp` |
| `SCARICO_VEN` | −1 | `cmp` |
| `TRASF_OUT` / `TRASF_IN` | −1 / +1 | `none` |
| `RETT_POS` / `RETT_NEG` | +1 / −1 | `cmp` |
| `ODL_USCITA_MAT` / `ODL_ENTRATA_MAT` | −1 / +1 | `cmp` |
| `ASSET_INSTALL` / `ASSET_RIENTRO` | −1 / +1 | `cmp` |

---

### Le colonne che governano il comportamento

* **`segno`** (`+1` / `−1`) — carico o scarico. ⚠️ Vedi l'avvertenza in
  [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti): **nessun vincolo lo lega al
  segno di `movimenti.qta`**, quindi oggi la coerenza è affidata a chi scrive.
* **`richiede_lotto`, `richiede_seriale`, `richiede_magazzino_dest`** — gli obblighi che il
  movimento deve soddisfare. ⚠️ Sono **dichiarazioni**: perché mordano serve un guard che le
  legga. Da verificare prima di attivare il dominio.
* **`impatto_valorizzazione`** — `cmp` aggiorna il costo medio ponderato, `none` no. ⭐ I
  trasferimenti sono `none`, ed è corretto: spostare merce fra due magazzini non cambia il
  valore complessivo, lo sposta.
* **`abilita_billing`** — il movimento può generare una voce fatturabile.

---

### ⭐ `TRASF_OUT` e `TRASF_IN` sono **due** causali

Un trasferimento è modellato come **due movimenti** — uno in uscita e uno in entrata — non
come un movimento solo con due magazzini. È coerente con il ledger: ogni riga descrive
l'effetto su *un* magazzino.

⚠️ La colonna `movimenti.magazzino_id_dest` sembra suggerire il contrario, ed è il punto in
cui il modello va chiarito prima dell'attivazione: le due rappresentazioni non possono
convivere senza una regola che dica quale vale.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
