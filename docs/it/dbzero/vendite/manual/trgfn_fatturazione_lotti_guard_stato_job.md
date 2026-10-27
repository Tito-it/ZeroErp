## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_fatturazione_lotti_guard_stato_job()`

> 👀 **Vedi anche**
>
> [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti) ·
> [config.stati_lotto_job](/dbzero/config/tabelle/stati_lotto_job) ·
> [config.transizioni_stati_lotto_job](/dbzero/config/tabelle/transizioni_stati_lotto_job)

### 🎯 Scopo
(27-10-2026 — brief `brief-modello-documento-vendita` §15, giro della fattura, F-4)

**La sola regola dei passaggi dello stato del job di un lotto.** Lo stato del job (in
esecuzione, completato, errore) dice com'è andato il lavoro della pipeline, non a che punto
fiscale è il lotto. Lo scrive il runner del backend, negli stessi momenti di sempre; i passaggi
ammessi li dice la matrice in tabella, e questo guard li fa rispettare a chiunque scriva.

### Regole

* Un cambio di stato è ammesso se la matrice ha la riga attiva; riscrivere lo stesso stato passa.
* Completato → errore è ammesso: un lotto già completato e rilanciato male si marca. Errore →
  completato no: la conclusione si guadagna con un giro nuovo.
* Altrimenti `E_LOTTO_PARAMETRO_NON_COERENTE`.
* «Completato solo se il lotto non è fermo» resta del guard
  `vendite.trgfn_fatturazione_lotti_guard_completato`.

Prima la regola era scritta due volte, in disaccordo: nel backend e in una funzione che nessuno
chiamava più (`fn_set_fatturazione_lotto_stato`, ritirata).

---

{% include-markdown "signature-core.md" %}
