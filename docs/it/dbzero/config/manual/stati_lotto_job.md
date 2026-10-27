## 📘 Documentazione Concettuale – Tabella `config.stati_lotto_job`

> 👀 **Vedi anche**
>
> [config.transizioni_stati_lotto_job](/dbzero/config/tabelle/transizioni_stati_lotto_job) ·
> [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti) ·
> [vendite.trgfn_fatturazione_lotti_guard_stato_job](/dbzero/vendite/funzioni/trgfn_fatturazione_lotti_guard_stato_job)

### 🎯 Scopo
(27-10-2026 — brief `brief-modello-documento-vendita` §15, giro della fattura, F-4, P-1)

**Il vocabolario dello stato del job di un lotto di fatturazione**: in esecuzione, completato,
errore. È l'asse del lavoro della pipeline, distinto dallo stato fiscale del lotto (bozza,
emessa, definitiva…).

Il lotto porta il **codice** dello stato (`stato_lotto`), legato a questa tabella da una chiave
esterna sul codice: i valori ammessi li dice il vocabolario, non un elenco scritto nella tabella
del lotto. I passaggi ammessi stanno in [`config.transizioni_stati_lotto_job`](/dbzero/config/tabelle/transizioni_stati_lotto_job).

Seed dal CSV `80_data/sql/config/stati_lotto_job.csv`.

---

{% include-markdown "signature-core.md" %}
