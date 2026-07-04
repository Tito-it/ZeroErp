## 📘 Documentazione Concettuale – Vista `vendite.vw_stato_sorgente_ordine`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[vendite.ordini](/dbzero/vendite/tabelle/ordini)
> [config.stati_doc_ordini](/dbzero/config/tabelle/stati_doc_ordini)
> [config.sorgenti](/dbzero/config/tabelle/sorgenti)
> [script.vw_stato_sorgente](/dbzero/script/views/vw_stato_sorgente)

---
### 🎯 Scopo Principale
(latest review 2026-07-02)
`vendite.vw_stato_sorgente_ordine` è il **resolver del dominio ORDINE (di vendita)** per la
proiezione dello stato di dominio (brief-db-proiezione-stato-dominio, deliverable D2):
espone il **descrittore normalizzato** dello stato **vivo** di ogni ordine di vendita —
stato nativo + mapping `fase`/`esito`/`terminale` dichiarato su `config.stati_doc_ordini`
— con chiave `(sorgente_tipo_id, sorgente_uid)` coerente con `pratiche.pratiche_sorgenti`.

È **read-time**: nessun mirror, il documento resta l'unica verità.

---

### JOIN principali

| Tabella | Ruolo |
|---------|-------|
| `config.sorgenti` | Aggancia il `sorgente_tipo_id` filtrando per `codice_interno='ORDINE_VENDITA'` (mai id letterale) |
| `vendite.ordini` | Documento sorgente; `sorgente_uid = (id)::text` (coerente con `key_selector='id'`, diverso da offerta/preventivo che usano `uid`) |
| `config.stati_doc_ordini` | Stato nativo + mapping proiezione (`fase`/`esito`/`terminale`) |

---

### 📑 Campi chiave esposti

* **Chiave**: sorgente_tipo_id, sorgente_uid
* **Stato nativo (logica)**: stato_codice_interno (immutabile)
* **Stato nativo (display)**: stato_codice, stato_descrizione
* **Proiezione normalizzata**: fase, esito (verdetto o NULL), terminale

Alias **fedeli** alla sorgente (linee-guida-sql §6c).

---

### Esempio d'uso

```sql
-- Descrittore dello stato vivo di un ordine di vendita, per id (key_selector='id').
SELECT stato_codice, stato_descrizione, fase, esito, terminale
FROM vendite.vw_stato_sorgente_ordine
WHERE sorgente_uid = (12345)::text;
```

---

### Note operative

* **Al più una riga per (tipo, uid)** — garantito da `ordini.id` PK.
* ⚠️ **Legge solo `vendite.ordini`** (sorgente `ORDINE_VENDITA`). La tabella stati
  `config.stati_doc_ordini` è condivisa con `acquisti.ordini`, ma la mappa `fase`/`esito`/
  `terminale` è **centrata sul ciclo di vendita** (vedi manuale di `stati_doc_ordini`).
* Il motore pratiche **non interroga questa vista direttamente**: passa da
  `script.vw_stato_sorgente` (layering `pratiche → script → dominio`).
* Test: `db/pgtap/pratiche/test-proiezione-stato-sorgente.sql`.

---

{% include-markdown "signature-core.md" %}
