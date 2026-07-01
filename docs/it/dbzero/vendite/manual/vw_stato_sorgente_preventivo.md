## 📘 Documentazione Concettuale – Vista `vendite.vw_stato_sorgente_preventivo`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[vendite.preventivi](/dbzero/vendite/tabelle/preventivi)
> [config.stati_doc_preventivi](/dbzero/config/tabelle/stati_doc_preventivi)
> [config.sorgenti](/dbzero/config/tabelle/sorgenti)
> [script.vw_stato_sorgente](/dbzero/script/views/vw_stato_sorgente)

---
### 🎯 Scopo Principale
(latest review 01-07-2026)
`vendite.vw_stato_sorgente_preventivo` è il **resolver del dominio PREVENTIVI** per la
proiezione dello stato di dominio (brief-db-proiezione-stato-dominio, deliverable D2):
espone il **descrittore normalizzato** dello stato **vivo** di ogni preventivo — stato
nativo + mapping `fase`/`esito`/`terminale` dichiarato su `config.stati_doc_preventivi` —
con chiave `(sorgente_tipo_id, sorgente_uid)` coerente con `pratiche.pratiche_sorgenti`.

È **read-time**: nessun mirror, il documento resta l'unica verità.

---

### JOIN principali

| Tabella | Ruolo |
|---------|-------|
| `config.sorgenti` | Aggancia il `sorgente_tipo_id` filtrando per `codice_interno='PREVENTIVO'` (mai id letterale) |
| `vendite.preventivi` | Documento sorgente; `sorgente_uid = (uid)::text` (coerente con `key_selector='uid'`) |
| `config.stati_doc_preventivi` | Stato nativo + mapping proiezione (`fase`/`esito`/`terminale`) |

---

### 📑 Campi chiave esposti

* **Chiave**: sorgente_tipo_id, sorgente_uid
* **Stato nativo (logica)**: stato_codice_interno (immutabile)
* **Stato nativo (display)**: stato_codice, stato_descrizione
* **Proiezione normalizzata**: fase (`APERTO`/`IN_CORSO`/`IN_ATTESA`/`CHIUSO`), esito
  (verdetto `POSITIVO`/`NEGATIVO`/… o NULL), terminale

Alias **fedeli** alla sorgente (linee-guida-sql §6c): `codice_interno` per la logica,
`codice`/`descrizione` per il display.

---

### Esempio d'uso

```sql
-- Descrittore dello stato vivo di un preventivo, per uid.
SELECT stato_codice, stato_descrizione, fase, esito, terminale
FROM vendite.vw_stato_sorgente_preventivo
WHERE sorgente_uid = '018f...::uuid'::text;
```

---

### Note operative

* **Al più una riga per (tipo, uid)** — garantito da `preventivi.uid` UNIQUE. È il
  contratto che ogni resolver di dominio deve rispettare.
* Il motore pratiche **non interroga questa vista direttamente**: passa da
  `script.vw_stato_sorgente` (layering `pratiche → script → dominio`).
* ⚠️ **Lag dello stato memorizzato**: la vista fotografa lo stato **scritto** sul
  documento. La transizione `EMESSO → SCADUTO` è **asincrona** (job notturno,
  linee-guida-sql §7c): un preventivo scaduto per data ma non ancora flippato proietta
  `IN_ATTESA` fino al giro del job. Il resolver **non ricalcola** la scadenza: sarebbe
  logica di dominio duplicata.
* Test: `db/pgtap/pratiche/test-proiezione-stato-sorgente.sql`.

---

{% include-markdown "signature-core.md" %}
