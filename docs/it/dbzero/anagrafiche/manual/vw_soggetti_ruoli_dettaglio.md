## 📘 Documentazione Concettuale – Vista `anagrafiche.vw_soggetti_ruoli_dettaglio`

> 👀 **Vedi anche**
>
> Approfondimenti tabelle:
>
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)  
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)  
> * [config.tipi_ruoli](/dbzero/config/tabelle/tipi_ruoli)  
> * [config.titoli_cortesia](/dbzero/config/tabelle/titoli_cortesia)  

---

### 🎯 Scopo Principale

(latest review 20-02-26)
La vista **`anagrafiche.vw_soggetti_ruoli_dettaglio`** fornisce una lettura
generale dei ruoli soggetto, partendo da `soggetto_ruolo_id` e includendo:

* dati anagrafici e fiscali del soggetto;
* decodifica del tipo ruolo;
* decodifica del titolo di cortesia (se presente).

E` pensata come vista di supporto per UI, API e report che devono mostrare
in modo rapido ragione sociale e riferimenti fiscali di un ruolo.

---

### 📑 Campi chiave esposti

* `soggetto_ruolo_id`
* `soggetto_id`
* `ragione_sociale_completa`
* `id_fiscale_univoco_cf_piva`
* `partita_iva`
* `codice_fiscale`
* `data_nascita`
* `sesso`
* `titolo_cortesia_descrizione`
* `tipo_ruolo_codice_interno`

---

### 🔍 Esempi d’uso

```sql
SELECT
  soggetto_ruolo_id,
  ragione_sociale_completa,
  id_fiscale_univoco_cf_piva,
  partita_iva,
  codice_fiscale
FROM anagrafiche.vw_soggetti_ruoli_dettaglio
WHERE soggetto_ruolo_id = 123;
```

```sql
SELECT
  soggetto_ruolo_id,
  tipo_ruolo_codice_interno,
  titolo_cortesia_descrizione,
  cognome,
  nome
FROM anagrafiche.vw_soggetti_ruoli_dettaglio
WHERE soggetto_id = '00000000-0000-0000-0000-000000000000'::uuid;
```

---

{% include-markdown "signature-core.md" %}
