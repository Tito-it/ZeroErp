## 📘 Documentazione Concettuale – Funzione `config.trgfn_stati_doc_fiscale_chiude_lotto_guard()`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**    
>
• [config.stati_doc_fiscale](/dbzero/config/tabelle/stati_doc_fiscale)    
> • [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)    
>
### 🎯 Scopo Principale
(latest review 29-03-2026)
La trigger function `config.trgfn_stati_doc_fiscale_chiude_lotto_guard()`
garantisce che il flag `chiude_lotto` in `config.stati_doc_fiscale` abbia
cardinalita` **esattamente uno**: nel catalogo deve esistere sempre e solo una
riga con `chiude_lotto = true`.

---

### Quando si attiva

* trigger `AFTER INSERT OR UPDATE OR DELETE` su `config.stati_doc_fiscale`;
* lavora a livello tabella, ricontando lo stato complessivo dopo ogni modifica.

---

### Regole operative

* conta le righe di `config.stati_doc_fiscale` con `chiude_lotto IS TRUE`;
* se il conteggio e` diverso da `1`, blocca l'operazione con errore `E_CHIUDE_LOTTO_SINGLETON`;
* in caso di coerenza, non modifica dati e termina senza effetti collaterali.

---

### Perche` e` importante

* il processo di fatturazione lotto deve sapere in modo non ambiguo quale stato documento comporta la chiusura operativa del lotto;
* evita configurazioni invalide con nessuno stato chiudente o con piu` stati concorrenti;
* mantiene coerente quanto documentato in `config.stati_doc_fiscale` sul significato del flag `chiude_lotto`.

---

{% include-markdown "signature-core.md" %}
