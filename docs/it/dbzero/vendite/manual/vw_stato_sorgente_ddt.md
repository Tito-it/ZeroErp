## 📘 Documentazione Concettuale – Vista `vendite.vw_stato_sorgente_ddt`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[vendite.ddt](/dbzero/vendite/tabelle/ddt)
> [config.stati_doc_ddt](/dbzero/config/tabelle/stati_doc_ddt)
> [config.sorgenti](/dbzero/config/tabelle/sorgenti)
> [script.vw_stato_sorgente](/dbzero/script/views/vw_stato_sorgente)
>
Ramo gemello della stessa slice:
>
[vw_stato_sorgente_reso](vw_stato_sorgente_reso.md)
> Brief autorevole: `docs/it/dev/work-in-progress/brief-db-fatturazione-ddt-resi.md` §4a

---
### 🎯 Scopo Principale
(latest review 2026-07-18)

`vendite.vw_stato_sorgente_ddt` è il **resolver del dominio DDT** per la proiezione dello stato
di dominio: traduce lo stato nativo del documento nel vocabolario comune
(`fase` / `esito` / `terminale`) con cui tutti i tipi di documento vengono confrontati.

Mancava soltanto perché il DDT è uno sviluppo recente — non per una scelta contraria. Con
questo ramo e con quello dei resi, il traduttore copre **tutti i tipi documento registrati**.

È **read-time**: nessun mirror, il documento resta l'unica verità.

---

### 🔑 La chiave è `id`, non l'uid

`sorgente_uid = ddt.id::text`, perché `config.sorgenti.key_selector` vale **`id`** per
`DDT_VENDITA` (solo `PREVENTIVO` e `OFFERTA_COMMERCIALE` usano `uid`).

> ⚠️ **Trappola da conoscere**: `vendite.resi.sorgente_uid` è un **uuid** che punta al DDT di
> origine — ma quella è una *colonna tipizzata diretta*, un meccanismo diverso dalla sorgente
> polimorfa. Usare l'uid qui farebbe sì che il ramo **non agganci nulla**: nessun errore, solo
> una proiezione sempre vuota. Il pgTAP asserisce apposta che cercare per uid **non trova**.
>
> Mappa completa: `config/manual/sorgenti.md` §Convenzione chiave sorgente.

---

### `esito` e `terminale` sono DERIVATI

`config.stati_doc_ddt` non espone quelle due colonne (a differenza di `stati_doc_ordini`):
dichiara `fase` e `is_abortito`, e da lì la vista deriva meccanicamente —

| Condizione | `esito` | `terminale` |
|---|---|---|
| `is_abortito` (ANNULLATO) | `NEGATIVO` | ✅ |
| `fase = CHIUSO` e non abortito (CONSEGNATO, RESO) | `POSITIVO` | ✅ |
| altrimenti (DRAFT, EMESSO, SPEDITO) | *(nessuno)* | ❌ |

**Nessun caso speciale**: la regola vale anche per stati futuri.

> ⚠️ **Conseguenza dichiarata**: il DDT in stato `RESO` risulta **POSITIVO**. È voluto — il
> catalogo dichiara `is_abortito = false` su quello stato, perché il progetto distingue
> deliberatamente *«merce tornata»* da *«documento annullato»*, e la vista non introduce una
> terza interpretazione. Se un domani il reso totale dovesse valere `NEGATIVO`, la sede giusta è
> il **catalogo** (una colonna che lo dichiari), non un `CASE` qui.

---

### 📑 Campi chiave esposti

* **Chiave**: `sorgente_tipo_id`, `sorgente_uid` (= `ddt.id::text`)
* **Stato nativo (logica)**: `stato_codice_interno` (immutabile)
* **Stato nativo (display)**: `stato_codice`, `stato_descrizione`
* **Proiezione normalizzata**: `fase`, `esito`, `terminale`

Alias **fedeli** alla sorgente (linee-guida-sql §6c).

---

### Esempio d'uso

```sql
-- Descrittore dello stato vivo di un DDT, per id (key_selector='id').
SELECT stato_codice, stato_descrizione, fase, esito, terminale
FROM vendite.vw_stato_sorgente_ddt
WHERE sorgente_uid = (12345)::text;
```

---

### Note operative

* **Al più una riga per (tipo, uid)** — garantito da `ddt.id` PK.
* I consumatori **non interrogano questa vista direttamente**: passano da
  `script.vw_stato_sorgente` (layering `dominio → script → consumatore`).
* Nessun `security_invoker`: la famiglia `vw_stato_sorgente_*` non lo usa (verificato sul
  vivo) — questo ramo segue i gemelli. Non aggiungerlo di straforo: cambierebbe il
  comportamento RLS di una vista di sistema.
* Test: `db/pgtap/vendite/test-vw-stato-sorgente-ddt-reso-v1.sql`.

---

{% include-markdown "signature-core.md" %}
