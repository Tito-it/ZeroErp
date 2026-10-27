## 📘 Documentazione Concettuale – Tabella `config.transizioni_stati_lotto_job`

> 👀 **Vedi anche**
>
> [config.stati_lotto_job](/dbzero/config/tabelle/stati_lotto_job) ·
> [vendite.trgfn_fatturazione_lotti_guard_stato_job](/dbzero/vendite/funzioni/trgfn_fatturazione_lotti_guard_stato_job)

### 🎯 Scopo
(27-10-2026 — brief `brief-modello-documento-vendita` §15, giro della fattura, F-4)

**I passaggi dello stato del job di un lotto**: una riga attiva = un passaggio ammesso.

| Da | A | Quando |
| --- | --- | --- |
| in esecuzione | completato | il giro è andato bene |
| in esecuzione | errore | il giro è andato male |
| completato | in esecuzione | parte un giro nuovo |
| errore | in esecuzione | parte un giro nuovo |
| completato | errore | un rilancio andato male si marca |

Errore → completato non c'è: la conclusione si guadagna con un giro, che passa da «in
esecuzione». Riscrivere lo stesso stato non è un passaggio.

La legge il guard [`vendite.trgfn_fatturazione_lotti_guard_stato_job`](/dbzero/vendite/funzioni/trgfn_fatturazione_lotti_guard_stato_job)
a ogni scrittura dello stato. Seed dal CSV `80_data/sql/config/transizioni_stati_lotto_job.csv`.

---

{% include-markdown "signature-core.md" %}
