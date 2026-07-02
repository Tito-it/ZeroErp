## 📘 Documentazione Concettuale – Vista `vendite.vw_stato_sorgente_offerta`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[vendite.offerte_commerciali](/dbzero/vendite/tabelle/offerte_commerciali)
> [config.stati_doc_offerte](/dbzero/config/tabelle/stati_doc_offerte)
> [config.sorgenti](/dbzero/config/tabelle/sorgenti)
> [script.vw_stato_sorgente](/dbzero/script/views/vw_stato_sorgente)

---
### 🎯 Scopo Principale
(latest review 2026-07-02)
`vendite.vw_stato_sorgente_offerta` è il **resolver del dominio OFFERTA** per la
proiezione dello stato di dominio (brief-db-proiezione-stato-dominio, deliverable D2):
espone il **descrittore normalizzato** dello stato **vivo** di ogni offerta commerciale —
stato nativo + mapping `fase`/`esito`/`terminale` dichiarato su `config.stati_doc_offerte`
— con chiave `(sorgente_tipo_id, sorgente_uid)` coerente con `pratiche.pratiche_sorgenti`.

È **read-time**: nessun mirror, il documento resta l'unica verità.

---

### JOIN principali

| Tabella | Ruolo |
|---------|-------|
| `config.sorgenti` | Aggancia il `sorgente_tipo_id` filtrando per `codice_interno='OFFERTA_COMMERCIALE'` (mai id letterale) |
| `vendite.offerte_commerciali` | Documento sorgente; `sorgente_uid = (uid)::text` (coerente con `key_selector='uid'`) |
| `config.stati_doc_offerte` | Stato nativo + mapping proiezione (`fase`/`esito`/`terminale`) |

---

### 📑 Campi chiave esposti

* **Chiave**: sorgente_tipo_id, sorgente_uid
* **Stato nativo (logica)**: stato_codice_interno (immutabile)
* **Stato nativo (display)**: stato_codice, stato_descrizione
* **Proiezione normalizzata**: fase (`APERTO`/`IN_CORSO`/`IN_ATTESA`/`CHIUSO`), esito
  (verdetto `POSITIVO`/`NEGATIVO`/… o NULL), terminale

Alias **fedeli** alla sorgente (linee-guida-sql §6c).

---

### Esempio d'uso

```sql
-- Descrittore dello stato vivo di un'offerta, per uid (key_selector='uid').
SELECT stato_codice, stato_descrizione, fase, esito, terminale
FROM vendite.vw_stato_sorgente_offerta
WHERE sorgente_uid = '018f...'::text;
```

---

### Note operative

* **Al più una riga per (tipo, uid)** — garantito da `offerte_commerciali.uid` UNIQUE.
* Il motore pratiche **non interroga questa vista direttamente**: passa da
  `script.vw_stato_sorgente` (layering `pratiche → script → dominio`).
* Test: `db/pgtap/pratiche/test-proiezione-stato-sorgente.sql`.

---

{% include-markdown "signature-core.md" %}
