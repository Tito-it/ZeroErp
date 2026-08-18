## 📘 Documentazione Concettuale – Funzione `vendite.fn_build_fattura_key`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)  
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
> • [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)  
> • [anagrafiche.resellers_billing_account](/dbzero/anagrafiche/tabelle/resellers_billing_account)  
> • [config.tipi_doc_fiscale](/dbzero/config/tabelle/tipi_doc_fiscale)  
>
**Approfondimento funzioni:**
>
• [vendite.fn_get_or_create_fattura_header](/dbzero/vendite/funzioni/fn_get_or_create_fattura_header)  
>
### 🎯 Scopo Principale
(latest review 29-01-2026)  
La funzione **`vendite.fn_build_fattura_key()`** costruisce la **chiave logica**
di aggregazione documento a partire da una riga di `attivita_fatturabili`.

---

### Regole principali

* La fattura viene emessa sul **BA padre** se presente, altrimenti sul BA stesso.
* L’utility e` risolta dal **billing_account**.
* L’emittente fiscale e` risolto dal mapping BA → emittente.
* Il reseller e` risolto dal mapping BA → reseller (se presente).
* Il registro e` risolto dal tipo documento fiscale.
* La chiave include: BA fattura, tipo documento, valuta, emittente, reseller, utility, registro.

---

### Output

Ritorna un **jsonb** con i campi chiave per l’aggregazione documento.

---

### Esempio

```sql
SELECT vendite.fn_build_fattura_key(12345);
```

---


---

### 🔄 rev 2026-08-18 — undici elementi, e i registri per emittente tornano raggiungibili

Brief: `brief-design-note-credito-resi` (slice **N2b** e **N3**).

#### 🔴 N2b — il difetto che rendeva irraggiungibili i sezionali intestati

`fn_get_registro_id` ha un fallback a quattro livelli su utility ed emittente. Il
suo **unico chiamante** — questa funzione — la invocava con **un argomento solo**:

```sql
v_registro_id := vendite.fn_get_registro_id(v_tipo_doc_fiscale_id);
```

Con `p_utility_id` e `p_emittente_soggetto_ruolo_id` a `NULL`, i due predicati
del `WHERE` valutano `NULL` — mai veri:

```sql
AND (r.utility_id IS NULL OR r.utility_id = NULL)                    -- mai vero
AND (r.emittente_soggetto_ruolo_id IS NULL OR r.emittente_… = NULL)  -- idem
```

⛔ Dalla pipeline erano raggiungibili **solo** i registri con utility ed emittente
entrambi `NULL`. Un registro intestato a un emittente non veniva scelto: veniva
**escluso dalla selezione**, e se fosse stato l'unico per quel tipo documento la
risposta sarebbe stata `E_CONFIG_MANCANTE` **su una configurazione corretta**.

⚠️ E il modello promette il contrario — la doc di `registri_fatturazione`:
*«la separazione dei registri evita collisioni di numerazione»* fra più aziende.

✅ Ora utility ed emittente si passano: erano già in mano tre righe più su.
**Parità misurata** il 2026-08-18: zero registri intestati oggi, quindi nessun
documento esistente cambia registro. Il difetto era latente — zero occorrenze, e
nulla lo impediva.

#### N3 — la chiave porta la NATURA e la SERIE

Da nove a **undici** elementi. È qui che la separazione fisica della nota di
credito finisce: due attività di natura diversa hanno chiavi diverse, quindi
**testate diverse**, quindi registro e numerazione diversi — senza una riga di
codice scritta per la NC.

⚠️ **Da qui in giù vanno usati tutti e undici.** Chi separa nella chiave e non
separa nel lookup **annulla le due metà** e fa tornare le attività nella stessa
fattura. Il presidio è
`db/pgtap/vendite/test-chiave-fattura-tre-specchi-v1.sql`.

⚠️ **Da questo momento un LOTTO può contenere documenti di natura diversa**: chi
lo legge non deve più assumere «sono tutte fatture», e il verbo «numera» li
numera entrambi sui rispettivi registri.

---

{% include-markdown "signature-core.md" %}
