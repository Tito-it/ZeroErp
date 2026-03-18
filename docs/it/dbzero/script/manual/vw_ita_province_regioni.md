## 📚 Documentazione Vista: `script.vw_ita_province_regioni`

> 👀 **Vedi anche:**
>
Approfondimento tabelle:      
>
[config.province](/dbzero/config/tabelle/province)
> [config.regioni](/dbzero/config/tabelle/regioni)
> [config.stati](/dbzero/config/tabelle/stati)

---
### 🎯 Scopo Principale
La vista `script.vw_ita_province_regioni` fornisce una **mappatura completa** tra province italiane, eventuali province accisa associate, regioni e stato di appartenenza, includendo i codici ISTAT e altre informazioni estratte dal campo JSON `extra_country`.

---

### Struttura

| Colonna                      | Fonte / Calcolo                                      | Descrizione                      |
| ---------------------------- | ---------------------------------------------------- | -------------------------------- |
| `id_provincia`               | `config.province.id`                                 | ID provincia                     |
| `ita_codice_istat_provincia` | `LPAD(extra_country['codice_istat'], 3, '0')`        | Codice ISTAT provincia (3 cifre) |
| `ita_nome_provincia`         | `config.province.descrizione`                        | Nome provincia                   |
| `ita_sigla_provincia`        | `config.province.sigla`                              | Sigla provincia                  |
| `id_provincia_accisa`        | `config.province.id` (join su `provincia_accisa_id`) | ID provincia accisa associata    |
| `ita_provincia_accisa`       | `config.province.descrizione` (accisa)               | Nome provincia accisa            |
| `ita_sigla_accisa`           | `config.province.sigla` (accisa)                     | Sigla provincia accisa           |
| `id_regione`                 | `config.regioni.id`                                  | ID regione                       |
| `ita_codice_istat_regione`   | `LPAD(extra_country['codice_istat'], 2, '0')`        | Codice ISTAT regione (2 cifre)   |
| `ita_nome_regione`           | `config.regioni.descrizione`                         | Nome regione                     |
| `ita_mezzogiorno`            | `(extra_country['mezzogiorno'])::char(1)`            | Indicatore Mezzogiorno (S/N)     |
| `id_stato`                   | `config.stati.id`                                    | ID stato                         |
| `ita_sigla_stato`            | `config.stati.sigla_stato`                           | Sigla stato                      |
| `ita_nome_stato`             | `config.stati.descrizione`                           | Nome stato                       |
| `ita_codice_istat_stato`     | `extra_country['codice_istat']`                      | Codice ISTAT stato               |
| `ita_codice_catastale_stato` | `extra_country['codice_catastale']`                  | Codice catastale stato           |

---

### Dettagli tecnici

* La vista unisce quattro entità:

  1. `config.province` (provincia principale)
  2. `config.province` (eventuale provincia accisa, join su `provincia_accisa_id` in `extra_country`)
  3. `config.regioni` (join su `regione_id`)
  4. `config.stati` (join su `stato_id`)
* I campi `codice_istat` sono formattati con `LPAD` per garantire lunghezze fisse (2 cifre per regioni, 3 per province).
* L’indicatore Mezzogiorno è estratto come singolo carattere (`char(1)`).

---

### Esempio di utilizzo

```sql
-- Elenco di province e relative regioni e stato
SELECT ita_nome_provincia, ita_sigla_provincia,
       ita_nome_regione, ita_mezzogiorno,
       ita_nome_stato
FROM script.vw_ita_province_regioni
ORDER BY ita_nome_regione, ita_nome_provincia;
```

**Output di esempio:**

```
 ita_nome_provincia | ita_sigla_provincia | ita_nome_regione | ita_mezzogiorno | ita_nome_stato
--------------------+---------------------+------------------+-----------------+----------------
 Ancona             | AN                  | Marche           | N               | Italia
 Bari               | BA                  | Puglia           | S               | Italia
```

---

### Note operative

* Utile per **reportistica nazionale** e analisi territoriali.
* La presenza della provincia accisa permette di gestire casi fiscali/doganali particolari.
* Per aggiornare i valori, modificare le relative righe in `config.province`, `config.regioni` e `config.stati`.

---

{% include-markdown "signature-core.md" %}
