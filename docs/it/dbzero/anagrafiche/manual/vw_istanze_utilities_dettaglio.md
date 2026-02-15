## 📘 Documentazione Concettuale – Vista `anagrafiche.vw_istanze_utilities_dettaglio`

> 👀 **Vedi anche**
>
> Approfondimenti tabelle:
>
> * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities)  
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)  
> * [anagrafiche.pdp](/dbzero/anagrafiche/tabelle/pdp)  
> * [config.stati_pdp](/dbzero/config/tabelle/stati_pdp)  
> * [config.utilities](/dbzero/config/tabelle/utilities)  
>
> Approfondimenti viste:
>
> * [anagrafiche.vw_indirizzi_dettaglio](/dbzero/anagrafiche/views/vw_indirizzi_dettaglio)  
> * [script.vw_indirizzo_completo](/dbzero/script/views/vw_indirizzo_completo)  

---

### 🎯 Scopo Principale

(latest review 15-02-26)
La vista **`anagrafiche.vw_istanze_utilities_dettaglio`** aggrega le informazioni di un'istanza utility con:

* dati soggetto (ragione sociale, identificativo fiscale),
* dati PDP e stato PDP,
* utility associata,
* dettaglio indirizzo normalizzato e decodifiche di comune/strada.

E' pensata per **consultazione applicativa** e reportistica, riducendo il numero di join necessari.

Nota naming utility:

* la vista espone `utility_id` (allineato a `anagrafiche.pdp.utility_id`);
* le altre tabelle del dominio (`clienti`, `billing_account`) usano lo stesso naming.

---

### 🧱 Struttura logica della vista

La vista parte da `anagrafiche.istanze_utilities` e aggiunge:

* join a `anagrafiche.soggetti` per ragione sociale e identificativo fiscale;
* join a `anagrafiche.pdp`, `config.stati_pdp`, `config.utilities` per stato e utility;
* join a `anagrafiche.vw_indirizzi_dettaglio` per i campi di indirizzo dettagliato;
* join a `script.vw_indirizzo_completo` per decodifiche di comune/strada.

---

### 📑 Campi esposti (principali)

| Colonna                      | Tipo       | Descrizione                        |
| ---------------------------- | ---------- | ---------------------------------- |
| `istanza_id`                 | `bigint`   | Identificativo istanza utility.    |
| `istanza_codice`             | `text`     | Codice istanza.                    |
| `proprietario_inquilino`     | `text`     | Indicatore proprietario/inquilino. |
| `fittizia`                   | `boolean`  | Flag istanza fittizia.             |
| `soggetto_id`                | `uuid`     | Soggetto associato.                |
| `ragione_sociale_completa`   | `text`     | Ragione sociale del soggetto.      |
| `id_fiscale_univoco_cf_piva` | `text`     | Identificativo fiscale univoco.    |
| `pdp_id`                     | `bigint`   | Identificativo PDP.                |
| `pdp_codice`                 | `text`     | Codice PDP.                        |
| `stato_pdp_id`               | `integer`  | Stato PDP (ID).                    |
| `stato_pdp_codice`           | `text`     | Codice interno stato PDP.          |
| `stato_pdp_descrizione`      | `text`     | Descrizione stato PDP.             |
| `utility_id`                 | `bigint`   | Utility associata.                  |
| `utility_codice`             | `text`     | Codice utility.                    |
| `utility_descrizione`        | `text`     | Descrizione utility.               |
| `indirizzo_dettaglio_id`     | `bigint`   | Riferimento indirizzo dettaglio.   |
| `indirizzo_normalizzato`     | `text`     | Indirizzo completo normalizzato.   |
| `via_norm`                   | `text`     | Via normalizzata.                  |
| `civico`                     | `integer`  | Civico.                            |
| `estensione_civico`          | `text`     | Estensione civico.                 |
| `palazzina`                  | `text`     | Palazzina.                         |
| `scala`                      | `text`     | Scala.                             |
| `piano`                      | `text`     | Piano.                             |
| `interno`                    | `text`     | Interno.                           |
| `altro`                      | `text`     | Altro dettaglio indirizzo.         |
| `civic_geoloc`               | `geometry` | Geolocalizzazione civico.          |
| `street_geoloc`              | `geometry` | Geolocalizzazione strada.          |
| `indirizzo_comune_id`        | `integer`  | Comune indirizzo (ID).             |
| `comune_descrizione`         | `text`     | Descrizione comune.                |
| `provincia_sigla`            | `text`     | Sigla provincia.                   |
| `cap`                        | `text`     | CAP.                               |

(Sono esposti anche i campi di audit `tx_id`, `data_insert`, `user_insert`, `data_update`, `user_update`.)

---

### 🔍 Modalita' d'uso tipiche

```sql
SELECT *
FROM anagrafiche.vw_istanze_utilities_dettaglio
WHERE istanza_id = :istanza_id;
```

---

### ✅ Best practice e raccomandazioni

* Usare questa vista per letture applicative e reportistica.
* Per modifiche, operare sempre sulle tabelle base.

---

{% include-markdown "signature-core.md" %}
