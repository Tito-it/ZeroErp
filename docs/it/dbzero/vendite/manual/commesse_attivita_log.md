## 📘 Documentazione Concettuale – Tabella `vendite.commesse_attivita_log`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)  
>
### 🎯 Scopo Principale
La tabella `vendite.commesse_attivita_log` registra eventi tecnici e dominio sulle righe
`commesse_attivita` per audit e troubleshooting.

---

### Regole principali

* ogni log punta a una riga commessa esistente;
* `evento` obbligatorio;
* payload `dettaglio` in `jsonb` per traccia strutturata.

---

### Utilizzo previsto

* traccia eventi push/pull e riallineamenti prezzo;
* supporto analisi incident e backfill;
* audit minimo persistente indipendente dal layer applicativo.

---

{% include-markdown "signature-core.md" %}
