## 📘 Documentazione Concettuale – Vista `dbops.vw_radici_di_prova_in_produzione`

### 🎯 Scopo
(18-10-2026 — brief `brief-db-processi-accensione-per-ambiente`, R-4, 2b-3)

**Presidio: dati di prova in un database di produzione.** Elenca gli
utenti e i soggetti di prova quando l'installazione è dichiarata di
produzione. **Deve restare vuota.**

Di norma non può riempirsi: in produzione le etichette non nascono e
l'ambiente non cambia. È l'ultima rete per ciò che i controlli non vedono, per
esempio una copia di un database di sviluppo ripristinata su un server di
produzione.

### Test

`db/pgtap/dbops/test-etichette-di-prova-v1.sql`.

---

{% include-markdown "signature-core.md" %}
