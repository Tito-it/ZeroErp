## 📘 Documentazione Concettuale – Vista `vendite.vw_dash_competenza_mensile`

> 👀 **Vedi anche**
>
[vw_dash_competenza_attivita](vw_dash_competenza_attivita.md)
> [vw_dash_competenza_errori](vw_dash_competenza_errori.md)
> [config.stati_doc_fiscale](/dbzero/config/tabelle/stati_doc_fiscale)

---
### 🎯 Scopo Principale
(latest review 06-07-2026)
Aggregata mensile della **Lente 1 Competenza** in **formato lungo**: una riga
per `competenza_mese × stadio × stato_fattura_codice_interno`. Gli stati
fattura sono **dati** (`config.stati_doc_fiscale`), non colonne: il formato
lungo regge il breakdown per stato (blocco 3a del design) senza rincorrere il
vocabolario; il **BE pivota**.

---

### Semantica

| Colonna | Regola |
|---------|--------|
| `stato_fattura_codice_interno` | Valorizzato solo per lo stadio `FATTURATA` (NULL per gli altri stadi e per le rare fatture senza stato) |
| `n_attivita`, `valore_tot` | Conteggio e somma `prezzo_snapshot × quantita` del gruppo |
| `valore_fatturato_tot` | Somma `imponibile_riga` (riconciliazione col fatturato reale) |
| `n_in_ritardo`, `valore_in_ritardo` | Recuperi tardivi del gruppo (`emessa_in_ritardo`) |

Eredita dal dettaglio perimetro computabile e scope emittente fail-closed.

---

### Esempio d'uso

```sql
-- Funnel del mese (il BE genera i mesi mancanti con generate_series).
SELECT stadio, stato_fattura_codice_interno, n_attivita, valore_tot
FROM vendite.vw_dash_competenza_mensile
WHERE competenza_mese = DATE '2026-05-01'
ORDER BY stadio, stato_fattura_codice_interno NULLS FIRST;
```

---

### Note operative

* Contratto **stabile per tutti i 4 blocchi** del design DL-8 (funnel,
  breakdown stato, ritardi; gli errori hanno la loro vista dedicata).
* Materializzabile in futuro (snapshot notturno) **senza cambiare il
  contratto** verso il BE.
* ⚠️ Fail-closed: senza GUC operatore restituisce 0 righe (vedi dettaglio).
* Test: `db/pgtap/vendite/test-vw-dash-competenza-v1.sql`.

---

{% include-markdown "signature-core.md" %}
