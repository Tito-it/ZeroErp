## 📘 Documentazione Concettuale – Vista `magazzino.vw_giacenza`

> 👀 **Vedi anche**
>
> • [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti)
> • [magazzino.vw_giacenza_valorizzata](/dbzero/magazzino/views/vw_giacenza_valorizzata)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

**La giacenza per articolo × magazzino**, calcolata dal ledger: `sum(qta)` sui movimenti.

⭐ Non esiste una tabella «giacenze». È una scelta portante: la giacenza è **sempre** la somma
del ledger, quindi non può divergere da esso e non c'è nessun posto dove correggerla di
nascosto.

---

### ⚠️ Dipende dal fatto che `qta` sia già firmata

La somma è pura: non moltiplica per `causali.segno`. Perché il conto torni, `movimenti.qta`
deve arrivare **già negativa** sugli scarichi — e nessun vincolo lo garantisce (vedi
[magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti)).

Un `CARICO_ACQ` scritto con quantità negativa farebbe **calare** la giacenza, e questa vista
lo sommerebbe senza accorgersene.

---

### Cosa **non** fa

* **Nessun filtro**: somma tutti i movimenti, di ogni data e di ogni causale. Non esiste una
  giacenza «a una certa data» — per quella servirebbe un predicato su `data_mov`.
* **Nessuna riga per articoli mai movimentati**: chi non ha movimenti non compare, invece di
  comparire a zero.
* **Nessuna ubicazione**: la giacenza è per magazzino, non per bin, anche se i movimenti
  portano `ubicazione_id_from/to`.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
