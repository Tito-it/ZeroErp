## 📘 Documentazione Concettuale – Tabella `dbops.soggetti_di_prova`

### 🎯 Scopo
(18-10-2026 — brief `brief-db-processi-accensione-per-ambiente`, R-4, 2b-3)

**L'etichetta dei soggetti di prova**: le aziende emittenti, i clienti, il
fornitore e le persone che il provisioning dei dati di sviluppo crea. Una riga
per soggetto, con la sua chiave (per esempio `DEV-EMITTENTE-A`).

Si etichettano le **radici**, non ogni riga: contratti, conti di fatturazione
e documenti si ritrovano dal soggetto a cui sono legati.

Stesse regole delle credenziali di prova: la scrive solo il provisioning, non
si toglie, in produzione non nasce.

### Test

`db/pgtap/dbops/test-etichette-di-prova-v1.sql`.

---

{% include-markdown "signature-core.md" %}
