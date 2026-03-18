## 📘 Documentazione Concettuale – Tabella `pagamenti.vendite_contabili_lotti`
### 🎯 Scopo Principale
Tabella ponte che collega i lotti di fatturazione (`vendite.fatturazione_lotti`)
alle testate contabili vendite (`pagamenti.vendite_contabili`).

### Regole principali
* Relazione esplicita lotto ↔ contabile.
* Coppia (`lotto_id`, `contabile_id`) univoca.
* Link usato per tracciare quali contabili sono state generate da uno specifico lotto.
* Non sono ammessi link verso testate contabili con `compensazione_id` valorizzato.

### Esempio d’uso
```sql
SELECT vcl.lotto_id, vcl.contabile_id
FROM pagamenti.vendite_contabili_lotti vcl
WHERE vcl.attivo IS TRUE;
```

{% include-markdown "signature-core.md" %}
