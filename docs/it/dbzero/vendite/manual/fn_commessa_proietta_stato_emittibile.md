## 📘 Documentazione Concettuale – Funzione `vendite.fn_commessa_proietta_stato_emittibile(bigint)`

> 👀 **Vedi anche**
>
> [vendite.commesse](/dbzero/vendite/tabelle/commesse) ·
> [vendite.stati_commessa](/dbzero/vendite/tabelle/stati_commessa) ·
> [vendite.fn_rendi_commessa_emittibile](/dbzero/vendite/funzioni/fn_rendi_commessa_emittibile) ·
> [vendite.fn_cambia_stato_commessa](/dbzero/vendite/funzioni/fn_cambia_stato_commessa) ·
> guida [Il modello del documento di vendita](/guide/modello-documento-di-vendita) §5 (i passaggi di processo)

### 🎯 Scopo
(26-10-2026 — brief `brief-modello-documento-vendita` §14, giro della commessa, C-2)

**Il passaggio della push allo stato emittibile.** Dopo un invio riuscito la push approva le
righe di quel giro, e la commessa diventa pronta per la fatturazione. È la conseguenza
dell'invio, non una scelta di chi lo lancia: per questo non chiede l'azione
`cambia_stato_commessa` che l'operatore usa per lo stesso passaggio («rendi pronta»). Il permesso
è quello della push, che il backend controlla.

### Regole

* Lo stato di destinazione lo dice il vocabolario: lo stato con `emittibile` vero, uno solo
  (altrimenti `E_CONFIG_MANCANTE`).
* Una commessa già emittibile: niente.
* Lo scrive con la sola scrittura comune, attraverso la porta. La matrice e le condizioni le
  giudica il guard di transizione: da una commessa chiusa o annullata il passaggio non c'è
  (`E_COMMESSA_STATO_TRANSIZIONE_INVALIDA`), e serve almeno una riga approvata da emettere.
* Gira coi diritti del proprietario, come le proiezioni gemelle di preventivo, ordine e offerta.

### Chi la chiama

[`vendite.fn_rendi_commessa_emittibile`](/dbzero/vendite/funzioni/fn_rendi_commessa_emittibile),
il ponte della push, dopo aver approvato le righe dell'invio.

---

{% include-markdown "signature-core.md" %}
