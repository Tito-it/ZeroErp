## 📘 Documentazione Concettuale – Tabella `anagrafiche.psp`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)  
> • [pagamenti.enti_incasso](/dbzero/pagamenti/tabelle/enti_incasso)  
>
**Approfondimento funzioni:**
>
• [anagrafiche.trgfn_psp_guard_ruolo_psp](/dbzero/anagrafiche/funzioni/trgfn_psp_guard_ruolo_psp)  
>
### 🎯 Scopo Principale
(latest review 13-02-2026)  
`anagrafiche.psp` rappresenta l’anagrafica dei **Payment Service Provider**
presenti nel sistema.

Ogni PSP e` modellato come ruolo su `anagrafiche.soggetti_ruoli` (codice interno `PSP`),
cosi` da mantenere coerenza con il modello ruoli gia` usato per clienti, gestori,
reseller, emittenti e banche.

---

### Ruolo nel processo

* identifica gli operatori di pagamento esterni (gateway/processor);
* abilita il mapping dei canali in `pagamenti.enti_incasso`;
* evita duplicazione di anagrafica canale/provenienza flusso.

---

### Regole principali

* `codice` univoco e non vuoto.
* `soggetto_ruolo_id` univoco (relazione 1:1 con il ruolo PSP).
* `uid` univoco per idempotenza tecnica.
* Trigger guard verifica che `soggetto_ruolo_id` sia coerente col ruolo `PSP`.

---

### Esempio d’uso

```sql
SELECT p.id, p.codice, p.descrizione, p.attivo
FROM anagrafiche.psp p
WHERE p.attivo IS TRUE
ORDER BY p.codice;
```

---

{% include-markdown "signature-core.md" %}
