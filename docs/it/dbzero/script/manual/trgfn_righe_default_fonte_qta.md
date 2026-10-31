## 📘 Documentazione Concettuale – Funzione `script.trgfn_righe_default_fonte_qta()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [vendite.contratti_righe](/dbzero/vendite/tabelle/contratti_righe)
> • [vendite.offerte_commerciali_eccezioni](/dbzero/vendite/tabelle/offerte_commerciali_eccezioni)

---
### 🎯 Scopo Principale

> **Ultimo aggiornamento**: 31 ottobre 2026


Normalizza `fonte_quantita_attesa` — *da dove arriva la quantità da fatturare* — portandola
al valore coerente con il `tipo_erogazione` della riga. Fa **due** cose, e solo quelle:

1. riempie la fonte quando non è stata indicata;
2. la **rimette al default** quando il cambio di tipo rende la combinazione attuale vietata.

Non è un guard: non blocca e non solleva mai. La difesa vera è il CHECK di tabella; questa
funzione serve perché la riga non arrivi al CHECK con una combinazione che nessuno ha scelto
consapevolmente.

**È generica per costruzione.** Non nomina nessuna tabella: le basta che la riga abbia le
colonne `tipo_erogazione` e `fonte_quantita_attesa`. Generalizza la precedente
`vendite.trgfn_contratti_righe_default_fonte_qta`, che oggi non esiste più.

---

### Aggancio

`BEFORE INSERT OR UPDATE OF tipo_erogazione, fonte_quantita_attesa`, `FOR EACH ROW`:

| Trigger | Tabella |
|---------|---------|
| `trg_contratti_righe_a10_default_fonte_qta_ins_upd` | `vendite.contratti_righe` |
| `trg_offerte_eccezioni_a10_default_fonte_qta_ins_upd` | `vendite.offerte_commerciali_eccezioni` |

Estenderla a una terza tabella con le stesse due colonne richiede **solo** il `CREATE TRIGGER`.

---

### La matrice dei default

| `tipo_erogazione` | fonte di default |
|---|---|
| `CANONE` | `FISSA` |
| `UNA_TANTUM` | `FISSA` |
| `ORARIO` | `MANUALE` |
| `CONSUMO` | `LETTURE` |
| *(qualsiasi altro, `NULL` compreso)* | `FISSA` |

---

### Regole applicate

**Ramo 1 — fonte nulla.** `fonte_quantita_attesa IS NULL` → applica il default della
matrice. Copre l'`INSERT` senza fonte; sull'`UPDATE` è difensivo, perché la colonna è
`NOT NULL`.

**Ramo 2 — il tipo è cambiato e la combinazione diventa vietata.** Solo in `UPDATE`, solo se
`tipo_erogazione` è effettivamente cambiato e la coppia risultante **non sta in
`config.erogazioni_fonti`** (il vocabolario, letto dalla funzione). Al 2026-10-31 le coppie
ammesse sono:

| `tipo_erogazione` | fonti ammesse |
|---|---|
| `CANONE` | `FISSA`, `DURATA` (`MANUALE` ritirata il 2026-10-29) |
| `UNA_TANTUM` | `FISSA`, `MANUALE` |
| `ORARIO` | `FISSA`, `MANUALE`, `TIMESHEET` |
| `CONSUMO` | `MANUALE`, `LETTURE` |

In quel caso la fonte torna al default del **nuovo** tipo. Le combinazioni solo *insolite* —
non presenti in questa lista — vengono lasciate come sono: la funzione corregge l'illegale,
non l'inconsueto.

---

### ⚠️ Il trigger normalizza, il CHECK presidia

La stessa lista di sette combinazioni vive **due volte**: qui, e nel CHECK di tabella
(`chk_contrighe_coerenza_fonte_erogazione`, e il suo specchio
`chk_offerte_eccezioni_coerenza_fonte_erogazione`). Non è una duplicazione da eliminare: sono
due ruoli diversi.

* **Cambio il tipo** e lascio la fonte incoerente → il trigger la corregge, l'operazione passa.
* **Cambio solo la fonte** verso una combinazione vietata → il ramo 2 **non scatta** (il tipo
  non è cambiato) e la riga arriva al CHECK, che la rifiuta.

Il secondo è il comportamento voluto: chi sceglie esplicitamente una fonte sbagliata deve
ricevere un errore, non una correzione silenziosa.

⚠️ Chi modifica la matrice deve però toccare **entrambi** i punti. Cambiarla solo qui produce
un trigger che porta la riga a un valore che il CHECK poi rifiuta; cambiarla solo nel CHECK
lascia il trigger a normalizzare verso una combinazione non più ammessa. In entrambi i casi
l'errore che l'utente vede non nomina la causa.

---

### Codici errore

Nessuno: la funzione non solleva. Gli errori arrivano dai CHECK di tabella.

---

{% include-markdown "signature-core.md" %}
