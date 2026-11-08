## 📘 Documentazione Concettuale – Tabella `config.esiti_flussi_pratiche`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[pratiche.flussi](/dbzero/pratiche/tabelle/flussi)
> [pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi)
> [pratiche.template_flussi_prerequisiti](/dbzero/pratiche/tabelle/template_flussi_prerequisiti)

---
### 🎯 Scopo Principale
Vocabolario **data-driven** degli **esiti** dei flussi operativi (il "verdetto" con cui
un flusso si chiude, es. `POSITIVO`). Sostituisce l'enum che prima era **cablato** in
piu' CHECK (`chk_flussi_esito`, ecc.): il motore fornisce il **meccanismo** (la tabella),
i domini seedano i **valori**. Cosi' un dominio puo' aggiungere un esito senza toccare il
codice del motore — decisivo per il **bivio-per-esito** (instradamento merce/servizi
dello SMISTAMENTO) senza portare semantica di dominio in un CHECK di motore (layering).

---

### Ruolo nel processo

* Referenziata **via `codice_interno`** (chiave naturale immutabile) da:
  `pratiche.flussi.esito`, `pratiche.template_flussi.esito_default`,
  `pratiche.template_flussi_prerequisiti.esito_richiesto`,
  `pratiche.template_flussi_handler_eventi.esito_richiesto` (FK).
* I prerequisiti **esito-aware** confrontano l'esito registrato sul flusso predecessore
  con `esito_richiesto`: e' il meccanismo che rende un ramo **percorribile** o **morto**.
* Indipendente dal vocabolario di `pratiche.regole_generazione` (`esito_richiesto` con
  valore `QUALSIASI`), che governa la generazione cross-pratica ed e' separato.

---

### Valori previsti (seed)

| codice_interno | Origine | `is_verdetto` | Descrizione |
|----------------|---------|---------------|-------------|
| `POSITIVO` | motore (strutturale) | ✅ | Esito positivo |
| `NEGATIVO` | motore (strutturale) | ✅ | Esito negativo |
| `PARZIALE` | motore (strutturale) | ✅ | Esito parziale |
| `NON_APPLICABILE` | motore (strutturale) | ✅ | Esito non applicabile |
| `MERCE_PRESENTE` | dominio (vendite) | ❌ | Ramo merce dello SMISTAMENTO (ordine→commessa dovuto) |
| `SOLO_SERVIZI` | dominio (vendite) | ❌ | Ramo soli servizi (commessa diretta; ramo ordine morto) |

**`is_verdetto`** (2026-07-01, brief `brief-db-proiezione-stato-dominio` decisione B):
discrimina i **verdetti** (chiusure valutative) dagli esiti di **instradamento** di
dominio (rami di un bivio). Solo i verdetti sono ammessi come proiezione `esito` sulle
`config.stati_doc_*` (guard `config.trgfn_stati_doc_guard_esito_verdetto`,
`E_STATO_DOC_ESITO_NON_VERDETTO`) e — in prospettiva (fase GUIDA) — come condizione di
avanzamento milestone. Default `false` = fail-closed: un nuovo esito non e` un verdetto
finche' chi lo seeda non lo dichiara.

I 4 esiti **strutturali** sono bootstrappati con lo schema (necessari alla FK sul DB vivo);
gli esiti di **dominio** sono seedati dai domini in `80_data`. Fonte gestita: il CSV
`config/esiti_flussi_pratiche.csv` (loadUpdateData).

---

### Convenzioni

* Pattern config standard: `codice`, `codice_interno` locked, `attivo`, `meta`, audit.
* Trigger standard applicati automaticamente dai runner del framework di automazione (`dbops.fn_run_automations_<tipo>`).
* Vocabolario **estendibile per configurazione**: nuovi esiti = nuove righe (nessun DDL,
  nessun codice di motore).

---

{% include-markdown "signature-core.md" %}
