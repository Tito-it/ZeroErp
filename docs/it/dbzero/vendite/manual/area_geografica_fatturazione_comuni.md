## 📘 Documentazione Concettuale – Tabella `vendite.area_geografica_fatturazione_comuni`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.area_geografica_fatturazione](/dbzero/vendite/tabelle/area_geografica_fatturazione)  
> • [config.comuni](/dbzero/config/tabelle/comuni)  
>
🎯 Scopo Principale

(latest review 30-01-2026)  
La tabella **`vendite.area_geografica_fatturazione_comuni`** mappa i comuni alle
aree geografiche di fatturazione.

---

### Regole principali

* Ogni coppia (`area_geografica_id`, `comune_id`) è unica.
* `attivo` consente di gestire associazioni temporaneamente sospese.

---

### Esempio

```sql
INSERT INTO vendite.area_geografica_fatturazione_comuni (area_geografica_id, comune_id)
VALUES (1, 1001);
```

---

{% include-markdown "signature-core.md" %}
