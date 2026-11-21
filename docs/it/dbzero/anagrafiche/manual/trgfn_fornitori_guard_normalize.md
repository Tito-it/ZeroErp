## 📘 Documentazione Concettuale – Trigger Function `anagrafiche.trgfn_fornitori_guard_normalize`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
[anagrafiche.fornitori](/dbzero/anagrafiche/tabelle/fornitori)

---
### 🎯 Scopo Principale
(rev 2026-11-21)

La trigger function **`anagrafiche.trgfn_fornitori_guard_normalize()`** tiene
coerente la **ritenuta d'acconto** del fornitore prima di ogni salvataggio.

---

### Regole applicate

* Trigger **BEFORE INSERT OR UPDATE** su `anagrafiche.fornitori`.
* Con la ritenuta (`ritenuta_acconto = true`) serve un'aliquota maggiore di
  zero: altrimenti il salvataggio è rifiutato con
  `E_FORNITORI_RITENUTA_ALIQUOTA_OBBLIGATORIA`, sul campo `ritenuta_aliquota`.
* Senza ritenuta l'aliquota si azzera: un valore rimasto da prima non resta
  appeso.

---

### Effetto operativo

Un fornitore non può avere la ritenuta senza aliquota, né un'aliquota senza
ritenuta.

---

### ⚠️ Nota funzionale

Fino al 2026-11-21 il trigger normalizzava anche il canale FE e la PEC del
fornitore. Quei campi sono usciti dalla tabella: l'instradamento della
fatturazione elettronica è del soggetto (`anagrafiche.dati_societari`), che ha
i suoi controlli. Il codice del fornitore lo genera un altro trigger.

---

{% include-markdown "signature-core.md" %}
