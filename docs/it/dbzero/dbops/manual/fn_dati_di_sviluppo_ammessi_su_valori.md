## 📘 Documentazione Concettuale – Funzione `dbops.fn_dati_di_sviluppo_ammessi_su_valori()`

### 🎯 Scopo
(18-10-2026 — brief `brief-db-processi-accensione-per-ambiente`, R-4, 2b-3)

**La regola: i dati di sviluppo nascono solo in un'installazione di
sviluppo.** Riceve l'ambiente e risponde sì o no; con l'ambiente non
dichiarato non risponde (lo dice chi legge l'ambiente).

È scritta una volta e la usano il controllo sulle etichette e il provisioning
dei dati di sviluppo.

### Test

`db/pgtap/dbops/test-etichette-di-prova-v1.sql`.

---

{% include-markdown "signature-core.md" %}
