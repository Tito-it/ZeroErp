## 📘 Documentazione Concettuale – Vista `anagrafiche.vw_dati_societari`

> 👀 **Vedi anche**
>
Approfondimenti tabelle:
>
[anagrafiche.dati_societari](/dbzero/anagrafiche/tabelle/dati_societari)  
> [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)  
> [config.forme_giuridiche](/dbzero/config/tabelle/forme_giuridiche)  
> [config.province](/dbzero/config/tabelle/province)  

---
### 🎯 Scopo Principale
(latest review 23-12-25)
La vista **`anagrafiche.vw_dati_societari`** offre una lettura unificata dei dati societari con:

* **tutti gli identificativi tecnici** necessari per rilettura/trace delle tabelle di origine,
* **decodifiche descrittive** di forma giuridica e provincia di iscrizione REA,
* i dati anagrafici sintetici del soggetto (ragione sociale completa e id fiscale univoco).

È pensata come **layer stabile di consultazione** per UI, report e servizi.

---

### Struttura logica della vista

La vista parte da `anagrafiche.dati_societari` e aggiunge:

* join a `anagrafiche.soggetti` per `ragione_sociale_completa` e `id_fiscale_univoco_cf_piva`;
* join a `config.forme_giuridiche` per la descrizione della forma;
* join a `config.province` per la descrizione della provincia REA.

---

### 📑 Campi esposti (principali)

| Colonna                             | Tipo      | Descrizione                                         |
| ----------------------------------- | --------- | --------------------------------------------------- |
| `dati_societari_id`                 | `bigint`  | Identificativo tecnico dei dati societari.          |
| `soggetto_id`                       | `uuid`    | Identificativo del soggetto.                        |
| `ragione_sociale_completa`          | `text`    | Ragione sociale completa del soggetto.              |
| `id_fiscale_univoco_cf_piva`        | `text`    | Identificativo fiscale univoco (CF/P.IVA).          |
| `forma_giuridica_id`                | `bigint`  | Identificativo della forma giuridica.               |
| `forma_giuridica_codice`            | `text`    | Codice della forma giuridica.                       |
| `forma_giuridica_descrizione`       | `text`    | Descrizione forma giuridica.                        |
| `provincia_iscrizione_rea_id`       | `integer` | Provincia di iscrizione REA (ID).                   |
| `provincia_iscrizione_rea_sigla`    | `text`    | Sigla provincia REA.                                |
| `provincia_iscrizione_rea_descrizione` | `text` | Descrizione provincia REA.                          |

(Sono esposti anche i campi amministrativi e di audit di `dati_societari`.)

---

### Modalità d’uso tipiche

```sql
SELECT *
FROM anagrafiche.vw_dati_societari
WHERE soggetto_id = :soggetto_id;
```

---

### Best practice e raccomandazioni

* Usare questa vista per letture applicative e reportistica.
* Per modifiche, operare sempre sulle tabelle base.

---

{% include-markdown "signature-core.md" %}
