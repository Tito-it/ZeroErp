## 📚 Documentazione Vista: `script.vw_stati_estesi`

> 👀 **Vedi anche:**
>
> Approfondimento tabelle:      
>
> * [config.stati](/dbzero/config/tabelle/stati)

---

### 🎯 Scopo Principale

La vista `script.vw_stati_estesi` fornisce un accesso **arricchito** ai dati della tabella `config.stati`, estraendo e presentando in colonne dedicate alcune informazioni aggiuntive memorizzate nel campo JSON `extra_country`.

---

### 🧩 Struttura

| Colonna             | Fonte                               | Descrizione                         |
| ------------------- | ----------------------------------- | ----------------------------------- |
| `id`                | `config.stati.id`                   | Identificativo stato                |
| `descrizione`       | `config.stati.descrizione`          | Nome esteso dello stato             |
| `sigla_stato`       | `config.stati.sigla_stato`          | Sigla nazionale dello stato         |
| `codice_iso2`       | `config.stati.codice_iso2`          | Codice ISO a 2 lettere              |
| `codice_iso3`       | `config.stati.codice_iso3`          | Codice ISO a 3 lettere              |
| `codice_telefonico` | `config.stati.codice_telefonico`    | Prefisso telefonico internazionale  |
| `continente`        | `config.stati.continente`           | Continente di appartenenza          |
| `codice_istat`      | `extra_country['codice_istat']`     | Codice ISTAT dello stato            |
| `codice_catastale`  | `extra_country['codice_catastale']` | Codice catastale (dove applicabile) |
| `stato_utilizzo`    | `extra_country['stato_utilizzo']`   | Stato di utilizzo (flag operativo)  |

---

### 🔧 Dettagli tecnici

* Il campo `extra_country` è di tipo JSON/JSONB nella tabella sorgente.
* La vista usa l'operatore `->>` per estrarre i valori come testo.
* I valori estratti non sono tipizzati (ritornano `text`).

---

### 🔍 Esempio di utilizzo

```sql
-- Elenco di tutti gli stati con codice ISTAT e stato utilizzo
SELECT descrizione, codice_iso2, codice_istat, stato_utilizzo
FROM script.vw_stati_estesi
ORDER BY descrizione;
```

**Output di esempio:**

```
 descrizione   | codice_iso2 | codice_istat | stato_utilizzo
---------------+-------------+--------------+---------------
 Italia        | IT          | 100          | attivo
 Francia       | FR          | 200          | attivo
 Stati Uniti   | US          |              | non_attivo
```

---

### 📌 Note operative

* La vista semplifica l’accesso ai dati “estesi” evitando di dover scrivere manualmente le estrazioni JSON.
* Utile per reportistica e query di configurazione che richiedono metadati standardizzati sugli stati.
* Per aggiornare i valori derivati (`codice_istat`, `codice_catastale`, `stato_utilizzo`) è necessario modificare il campo `extra_country` nella tabella `config.stati`.

---

{% include-markdown "signature-core.md" %}
