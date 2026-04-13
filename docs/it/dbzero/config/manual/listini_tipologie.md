## 📘 Documentazione Concettuale – Tabella `config.listini_tipologie`

> 👀 **Vedi anche**
>
Tabelle:
>
[vendite.listini](/dbzero/vendite/tabelle/listini)
> [config.listini_tipologie_utilities](/dbzero/config/manual/listini_tipologie_utilities)

---
### 🎯 Scopo Principale

Classifica le tipologie di voce di listino. Ogni tipologia ha esattamente un **flag semantico booleano** attivo, usato dalla pipeline di fatturazione per determinare la natura della voce senza string matching.

---

### Campi chiave (semantica)

| Colonna | Note |
| --- | --- |
| `codice` | Identificativo univoco (CONSUMO, QUOTA_FISSA, IMPOSTA, ONERE_SISTEMA, PRODOTTI, SERVIZI) |
| `descrizione` | Etichetta leggibile per UI |
| `e_consumo` | Voce di consumo misurabile (mc, kWh, mc acqua) |
| `e_quota_fissa` | Canone o quota periodica indipendente dal consumo |
| `e_imposta` | Imposta, accisa, componente fiscale |
| `e_onere` | Onere di sistema (es. componenti Arera) |
| `e_prodotto` | Articolo fisico, ricambio, materiale |
| `e_servizio` | Prestazione, intervento tecnico, assistenza |
| `ordinamento` | Ordinamento per display in UI |

---

### Vincoli

* **`chk_listini_tipologie_flag_esclusivi`**: esattamente uno tra i 6 flag booleani deve essere `true`. Impedisce tipologie ambigue (es. contemporaneamente consumo e servizio).

---

### Perche` flag booleani e non una colonna tipo_semantico

La pipeline di fatturazione interroga direttamente il flag (`WHERE lt.e_consumo = true`) senza string matching. Il set di flag e` stabile (6 categorie fiscali/operative ben definite). Se servisse una settima categoria, si aggiunge una colonna booleana + si aggiorna il constraint — operazione rara e controllata.

---

### Seed

| codice | descrizione | flag attivo | ordinamento |
| --- | --- | --- | --- |
| CONSUMO | Consumi | `e_consumo` | 10 |
| QUOTA_FISSA | Quote fisse | `e_quota_fissa` | 20 |
| IMPOSTA | Imposte e accise | `e_imposta` | 30 |
| ONERE_SISTEMA | Oneri di sistema | `e_onere` | 40 |
| PRODOTTI | Prodotti e ricambi | `e_prodotto` | 50 |
| SERVIZI | Servizi e assistenza | `e_servizio` | 60 |

---

{% include-markdown "signature-core.md" %}
