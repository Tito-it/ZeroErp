## 📘 Documentazione Concettuale – Funzione `anagrafiche.trgfn_psp_guard_ruolo_psp`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [anagrafiche.psp](/dbzero/anagrafiche/tabelle/psp)  
> • [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)  
>
**Approfondimento funzioni:**
>
• [script.fn_guard_soggetto_ruolo](/dbzero/script/funzioni/fn_guard_soggetto_ruolo)  
>
### 🎯 Scopo Principale
(latest review 13-02-2026)  
La funzione **`anagrafiche.trgfn_psp_guard_ruolo_psp()`** valida che
`NEW.soggetto_ruolo_id` punti a un ruolo con `codice_interno = 'PSP'`.

---

### Regole principali

* eseguita in trigger `BEFORE INSERT OR UPDATE` su `anagrafiche.psp`;
* delega i controlli a `script.fn_guard_soggetto_ruolo(...)`;
* in caso di incoerenza solleva errore applicativo tramite funzione guard centralizzata.

---

### Esempio d’uso

```sql
-- Invocata automaticamente dal trigger su anagrafiche.psp
INSERT INTO anagrafiche.psp (soggetto_ruolo_id, codice, descrizione)
VALUES (123, 'NEXI', 'Nexi PSP');
```

---

{% include-markdown "signature-core.md" %}
