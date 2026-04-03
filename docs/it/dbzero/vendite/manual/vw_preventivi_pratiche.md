## 📘 Documentazione Concettuale – Vista `vendite.vw_preventivi_pratiche`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[vendite.preventivi](/dbzero/vendite/tabelle/preventivi)
> [pratiche.pratiche_sorgenti](/dbzero/pratiche/tabelle/pratiche_sorgenti)
> [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche)
> [config.sorgenti](/dbzero/config/tabelle/sorgenti)
> [config.stati_pratiche](/dbzero/config/tabelle/stati_pratiche)

---
### 🎯 Scopo Principale
(latest review 03-04-2026)
`vendite.vw_preventivi_pratiche` espone le **pratiche collegate a ciascun preventivo vendita**
tramite la tabella ponte `pratiche.pratiche_sorgenti` con `sorgente_tipo = 'PREVENTIVO'`.

---

### JOIN principali

| Tabella | Ruolo |
|---------|-------|
| `config.sorgenti` | Filtro per codice 'PREVENTIVO' |
| `pratiche.pratiche_sorgenti` | Ponte sorgente_uid = preventivo.uid |
| `pratiche.pratiche` | Dati pratica |
| `config.stati_pratiche` | Codice e descrizione stato pratica |
| `pratiche.tipi_prestazione` | Tipo prestazione della pratica |

---

### 📑 Campi chiave esposti

* **Preventivo**: preventivo_id, preventivo_uid, preventivo_numero
* **Collegamento**: sorgente_id, ruolo_link, sorgente_riga, sorgente_meta
* **Pratica**: pratica_id, pratica_codice, pratica_descrizione
* **Stato**: stato_codice, stato_descrizione
* **Tipo**: tipo_prestazione_codice, tipo_prestazione_descrizione
* **Date**: data_apertura, data_scadenza

---

### Esempio d'uso

```sql
-- Pratiche collegate a un preventivo (sezione integrazione frontend)
SELECT pratica_codice, pratica_descrizione, stato_codice, stato_descrizione,
       tipo_prestazione_descrizione, data_apertura, ruolo_link
FROM vendite.vw_preventivi_pratiche
WHERE preventivo_id = 42;
```

---

{% include-markdown "signature-core.md" %}
