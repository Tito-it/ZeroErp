## 📘 Documentazione Concettuale – Vista `anagrafiche.vw_risorse_umane_dettaglio`

> 👀 **Vedi anche**
>
> Approfondimenti tabelle:
>
> * [anagrafiche.risorse_umane](/dbzero/anagrafiche/tabelle/risorse_umane)  
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)  
> * [config.qualifiche](/dbzero/config/tabelle/qualifiche)  
> * [config.unita_organizzative](/dbzero/config/tabelle/unita_organizzative)  

---

### 🎯 Scopo Principale

(latest review 07-01-26)
La vista **`anagrafiche.vw_risorse_umane_dettaglio`** fornisce una lettura
unificata delle risorse umane con:

* **tutti gli identificativi tecnici** delle tabelle coinvolte;
* **decodifiche descrittive** di qualifica e unita organizzativa;
* dati anagrafici essenziali del soggetto, inclusi
  `ragione_sociale_completa` e `id_fiscale_univoco_cf_piva`.

È pensata per **consultazione applicativa**, report e integrazioni esterne.

---

### 🧱 Struttura logica della vista

La vista parte da `anagrafiche.risorse_umane` e aggiunge:

* join a `anagrafiche.soggetti` per dati anagrafici e fiscali;
* join a `config.qualifiche` per la descrizione della qualifica;
* join a `config.unita_organizzative` per la descrizione dell’unita organizzativa.

---

### 📑 Campi esposti (principali)

| Colonna                           | Tipo      | Descrizione                                  |
| --------------------------------- | --------- | -------------------------------------------- |
| `risorsa_umana_id`                | `bigint`  | Identificativo della risorsa umana.          |
| `risorsa_umana_soggetto_id`       | `uuid`    | Soggetto di riferimento della risorsa umana. |
| `soggetto_ruolo_id`               | `bigint`  | Ruolo associato alla risorsa.                |
| `qualifica_id`                    | `integer` | Riferimento alla qualifica.                  |
| `qualifica_codice`                | `text`    | Codice della qualifica.                      |
| `qualifica_descrizione`           | `text`    | Descrizione della qualifica.                 |
| `unita_organizzativa_id`          | `integer` | Riferimento alla unita organizzativa.        |
| `unita_organizzativa_codice`      | `text`    | Codice della unita organizzativa.            |
| `unita_organizzativa_descrizione` | `text`    | Descrizione della unita organizzativa.       |
| `soggetto_id`                     | `uuid`    | Identificativo del soggetto.                 |
| `ragione_sociale_completa`        | `text`    | Ragione sociale completa del soggetto.       |
| `id_fiscale_univoco_cf_piva`      | `text`    | Identificativo fiscale univoco (CF/P.IVA).   |
| `partita_iva`                     | `text`    | Partita IVA del soggetto (se presente).      |
| `codice_fiscale`                  | `text`    | Codice fiscale del soggetto (se presente).   |
| `valido_dal`                      | `date`    | Inizio validita del rapporto.                |
| `valido_al`                       | `date`    | Fine validita del rapporto.                  |
| `risorsa_umana_attivo`            | `boolean` | Stato attivo della risorsa.                  |

(Sono esposti anche i campi amministrativi e di audit.)

---

### 🔍 Modalità d’uso tipiche

```sql
SELECT *
FROM anagrafiche.vw_risorse_umane_dettaglio
WHERE soggetto_id = :soggetto_id;
```

---

### ✅ Best practice e raccomandazioni

* Usare questa vista per letture applicative e reportistica.
* Per modifiche, operare sempre sulle tabelle base.

---

{% include-markdown "signature-core.md" %}
