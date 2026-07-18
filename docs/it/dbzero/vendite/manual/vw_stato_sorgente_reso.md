## 📘 Documentazione Concettuale – Vista `vendite.vw_stato_sorgente_reso`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[vendite.resi](/dbzero/vendite/tabelle/resi)
> [config.stati_doc_reso](/dbzero/config/tabelle/stati_doc_reso)
> [config.sorgenti](/dbzero/config/tabelle/sorgenti)
> [script.vw_stato_sorgente](/dbzero/script/views/vw_stato_sorgente)
>
Ramo gemello della stessa slice:
>
[vw_stato_sorgente_ddt](vw_stato_sorgente_ddt.md)
> Brief autorevole: `docs/it/dev/work-in-progress/brief-db-fatturazione-ddt-resi.md` §4a

---
### 🎯 Scopo Principale
(latest review 2026-07-18)

`vendite.vw_stato_sorgente_reso` è il **resolver del dominio RESO** per la proiezione dello
stato di dominio: traduce lo stato nativo del reso nel vocabolario comune
(`fase` / `esito` / `terminale`).

Scritto **insieme al ramo DDT**, nella stessa slice: i due erano nella stessa condizione
(sorgente registrata, catalogo con `fase`, nessun ramo) e trattarli insieme evita di lasciare
una coda da ricordare alla prossima slice.

È **read-time**: nessun mirror, il documento resta l'unica verità.

---

### 🔑 La chiave è `id`, non l'uid

`sorgente_uid = resi.id::text`, perché `config.sorgenti.key_selector` vale **`id`** per
`RESO_VENDITA`. Vale la stessa trappola del ramo DDT: la colonna `resi.sorgente_uid` (uuid) è
un *altro* meccanismo — punta al DDT di origine — e usarla qui produrrebbe una proiezione
sempre vuota, senza errore. Mappa: `config/manual/sorgenti.md` §Convenzione chiave sorgente.

---

### `esito` e `terminale` sono DERIVATI

`config.stati_doc_reso` dichiara `fase` e `is_abortito`, non `esito`/`terminale`. Regola
meccanica, identica al ramo DDT:

| Stato | `fase` | `esito` | `terminale` |
|---|---|---|---|
| `DRAFT` | APERTO | *(nessuno)* | ❌ |
| `CONFERMATO` | **CHIUSO** | `POSITIVO` | ✅ |
| `ANNULLATO` | CHIUSO + `is_abortito` | `NEGATIVO` | ✅ |

> **Nota storica (2026-07-18)**: fino a questa slice `CONFERMATO` era mappato su `IN_CORSO`, e
> quindi un reso confermato risultava *«non concluso»* per sempre. È stato **corretto nel
> catalogo**, non nella vista: per come funziona il motore, un reso confermato **è** concluso —
> la ri-consegna genera un *altro* documento, non prosegue questo. Il caso emerse proprio
> scrivendo questa vista, che rispecchiava fedelmente un dato sbagliato a monte.

⚠️ **`terminale` = conclusione commerciale, non lucchetto.** La matrice delle transizioni
ammette ancora `CONFERMATO → ANNULLATO` (guardato: vietato se esistono ri-consegne), che resta
la strada per lo storno.

---

### 📑 Campi chiave esposti

* **Chiave**: `sorgente_tipo_id`, `sorgente_uid` (= `resi.id::text`)
* **Stato nativo (logica)**: `stato_codice_interno` (immutabile)
* **Stato nativo (display)**: `stato_codice`, `stato_descrizione`
* **Proiezione normalizzata**: `fase`, `esito`, `terminale`

---

### Esempio d'uso

```sql
-- Descrittore dello stato vivo di un reso, per id (key_selector='id').
SELECT stato_codice, stato_descrizione, fase, esito, terminale
FROM vendite.vw_stato_sorgente_reso
WHERE sorgente_uid = (987)::text;
```

---

### Note operative

* **Al più una riga per (tipo, uid)** — garantito da `resi.id` PK.
* I consumatori passano da `script.vw_stato_sorgente` (layering), non da qui.
* ⚠️ Il reso è un documento di **flusso inverso** (`config.sorgenti.RESO_VENDITA` è
  `REVERSE_FLOW`): proietta il suo stato come tutti, ma **non entra** nel funnel
  pre-commessa della dashboard fatturazione — compare solo nel backlog.
* Nessun `security_invoker`: la famiglia `vw_stato_sorgente_*` non lo usa (verificato sul
  vivo) — questo ramo segue i gemelli.
* Test: `db/pgtap/vendite/test-vw-stato-sorgente-ddt-reso-v1.sql`.

---

{% include-markdown "signature-core.md" %}
