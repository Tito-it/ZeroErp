## 📘 Documentazione Concettuale – Vista `vendite.vw_stato_sorgente_contratto`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[vendite.contratti](/dbzero/vendite/tabelle/contratti)
> [config.stati_doc_contratti](/dbzero/config/tabelle/stati_doc_contratti)
> [config.sorgenti](/dbzero/config/tabelle/sorgenti)
> [script.vw_stato_sorgente](/dbzero/script/views/vw_stato_sorgente)

---
### 🎯 Scopo Principale
(latest review 2026-07-02)
`vendite.vw_stato_sorgente_contratto` è il **resolver del dominio CONTRATTO** per la
proiezione dello stato di dominio (brief-db-proiezione-stato-dominio, deliverable D2):
espone il **descrittore normalizzato** dello stato **vivo** di ogni contratto — stato
nativo + mapping `fase`/`esito`/`terminale` dichiarato su `config.stati_doc_contratti` —
con chiave `(sorgente_tipo_id, sorgente_uid)` coerente con `pratiche.pratiche_sorgenti`.

È **read-time**: nessun mirror, il documento resta l'unica verità.

---

### JOIN principali

| Tabella | Ruolo |
|---------|-------|
| `config.sorgenti` | Aggancia il `sorgente_tipo_id` filtrando per `codice_interno='CONTRATTO'` (mai id letterale) |
| `vendite.contratti` | Documento sorgente; `sorgente_uid = (id)::text` (coerente con `key_selector='id'`) |
| `config.stati_doc_contratti` | Stato nativo + mapping proiezione (`fase`/`esito`/`terminale`) |

---

### 📑 Campi chiave esposti

* **Chiave**: sorgente_tipo_id, sorgente_uid
* **Stato nativo (logica)**: stato_codice_interno (immutabile)
* **Stato nativo (display)**: stato_codice, stato_descrizione
* **Proiezione normalizzata**: fase, esito (verdetto o NULL), terminale

Alias **fedeli** alla sorgente (linee-guida-sql §6c). `terminale` è un asse distinto da
`is_abortito` (che resta invariato): `CESSATO` è terminale ma non abortito.

---

### Esempio d'uso

```sql
-- Descrittore dello stato vivo di un contratto, per id (key_selector='id').
SELECT stato_codice, stato_descrizione, fase, esito, terminale
FROM vendite.vw_stato_sorgente_contratto
WHERE sorgente_uid = (12345)::text;
```

---

### Note operative

* **Al più una riga per (tipo, uid)** — garantito da `contratti.id` PK.
* Il motore pratiche **non interroga questa vista direttamente**: passa da
  `script.vw_stato_sorgente` (layering `pratiche → script → dominio`).
* Test: `db/pgtap/pratiche/test-proiezione-stato-sorgente.sql`.

---

{% include-markdown "signature-core.md" %}
