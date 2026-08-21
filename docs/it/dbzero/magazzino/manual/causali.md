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

* **`segno`** (`+1` / `−1`) — carico o scarico. ⚠️ È una **dichiarazione, non un
  meccanismo**: vedi la sezione qui sotto.
* **`richiede_lotto`, `richiede_seriale`, `richiede_magazzino_dest`** — gli obblighi che il
  movimento deve soddisfare. ⚠️ Sono **dichiarazioni**: perché mordano serve un guard che le
  legga. Da verificare prima di attivare il dominio.
* **`impatto_valorizzazione`** — `cmp` aggiorna il costo medio ponderato, `none` no. ⭐ I
  trasferimenti sono `none`, ed è corretto: spostare merce fra due magazzini non cambia il
  valore complessivo, lo sposta.
* **`abilita_billing`** — il movimento può generare una voce fatturabile.

---

### 🔴 `segno` non è applicato da nessuno — e la giacenza dipende da questo

È il punto più importante di questa tabella, e non si vede guardandola: **la colonna `segno`
non entra in nessun calcolo.**

`magazzino.vw_giacenza` — l'unica fonte della giacenza — la calcola così:

```sql
SELECT articolo_id, magazzino_id, sum(qta) FROM magazzino.movimenti GROUP BY 1,2;
```

Un puro `sum(qta)`. Non moltiplica per `causali.segno`, non lo legge affatto.

Perché il conto torni, `movimenti.qta` deve quindi arrivare **già firmata**: negativa sugli
scarichi, positiva sui carichi. Che l'intenzione sia questa lo conferma il vincolo sulla
quantità, che è `qta <> 0` e **non** `qta > 0`.

⚠️ **Ma nulla lo garantisce.** Nessun CHECK, nessun trigger, nessuna funzione lega il segno di
`qta` al `segno` della sua causale. Oggi è scrivibile:

```sql
-- causale CARICO_ACQ (segno +1), quantità negativa: nessun errore
INSERT INTO magazzino.movimenti (articolo_id, magazzino_id, causale_id, qta, ...)
VALUES (..., (SELECT id FROM magazzino.causali WHERE codice='CARICO_ACQ'), -5, ...);
```

Il movimento risulta registrato come **carico** e fa **calare** la giacenza. Non c'è errore,
non c'è avviso: c'è un saldo sbagliato, e la causale — l'unica cosa che direbbe qual era
l'intenzione — non viene consultata da nessuno.

⭐ Da qui il rischio vero: `segno` **sembra** la definizione del comportamento della causale,
e chi legge questa tabella lo dà per acquisito. È invece documentazione di un'intenzione che
il database non fa rispettare.

---

### Le due strade per chiuderlo, da scegliere prima di attivare il dominio

Sono alternative, non complementari, e producono contratti diversi per chi scrive:

1. **Un CHECK che leghi i due segni.** `qta` resta responsabilità del chiamante, ma un segno
   incoerente viene rifiutato. ⚠️ Richiede di leggere la causale dalla riga, quindi non è un
   CHECK di colonna: serve un trigger che si comporti da vincolo, oppure una colonna generata.
   Chi scrive deve continuare a firmare `qta` correttamente — gli si dice solo quando sbaglia.
2. **Un trigger che *derivi* `qta`** dal valore assoluto per il `segno` della causale. Il
   chiamante scrive sempre quantità positive e non può sbagliare il segno. ⚠️ In cambio, un
   `UPDATE` che cambia la causale deve ricalcolare `qta`, e la colonna smette di essere un
   dato scritto per diventarne uno derivato — con tutto ciò che comporta per import e
   correzioni.

⚠️ La prima è più conservativa, la seconda toglie la classe di errore alla radice. La scelta
va fatta **prima** del primo movimento reale: dopo, cambiare la semantica di `qta`
significherebbe rileggere ogni riga già scritta per capire con quale convenzione era stata
registrata.

⭐ Nota di metodo: il difetto gemello di questa tabella —
`chk_mag_movimenti_da_destinazione_distinti`, che rendeva inseribili solo i trasferimenti — è
stato corretto il 2026-08-21 (`20260821-10`) perché aveva **una sola forma giusta possibile**.
Questo no: ha due soluzioni legittime, e per questo resta aperto invece di essere stato deciso
mentre si scriveva la documentazione.

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
