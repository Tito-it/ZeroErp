## 📘 Documentazione Concettuale – Tabella `vendite.area_geografica_fatturazione`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.area_geografica_fatturazione_comuni](/dbzero/vendite/tabelle/area_geografica_fatturazione_comuni)  
>
🎯 Scopo Principale

(latest review 30-01-2026)  
La tabella **`vendite.area_geografica_fatturazione`** definisce aree geografiche
per raggruppare i comuni e supportare filtri di fatturazione (es. per area).

---

### Regole principali

* `codice` univoco e identificativo area.
* `attivo` governa la validità dell’area.
* I comuni sono associati tramite `vendite.area_geografica_fatturazione_comuni`.

---

### Esempio

```sql
INSERT INTO vendite.area_geografica_fatturazione (codice, descrizione)
VALUES ('AREA_NORD', 'Area Nord');
```

---

{% include-markdown "signature-core.md" %}
