## 📘 Documentazione Concettuale – Tabella `vendite.registri_fatturazione_progressivi`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.registri_fatturazione](/dbzero/vendite/tabelle/registri_fatturazione)  
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
>
### 🎯 Scopo Principale
(latest review 26-01-2026)
`vendite.registri_fatturazione_progressivi` memorizza i **progressivi di numerazione**
per ciascun registro, anno, mese e serie. E` la base per l’assegnazione del
numero documento in fase di emissione.

---

### Campi chiave (semantica)

* **Registro**: `registro_id`.
* **Periodo**: `anno`, `mese` (0 = annuale se non usato).
* **Serie**: `serie` (default stringa vuota).
* **Contatore**: `last_numero`.
* **Stato**: `attivo`.

---

### Note operative

* Il vincolo univoco `(registro_id, anno, mese, serie)` impedisce duplicazioni.
* La tabella e` aggiornata dal processo di numerazione (fase emissione).

---

{% include-markdown "signature-core.md" %}
