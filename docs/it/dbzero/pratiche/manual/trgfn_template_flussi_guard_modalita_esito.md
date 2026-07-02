## 📘 Documentazione Trigger Function – `pratiche.trgfn_template_flussi_guard_modalita_esito`

> 👀 **Vedi anche**
>
Funzioni collegate:
>
[pratiche.trgfn_flussi_guard_esito_classe](trgfn_flussi_guard_esito_classe.md)
>
Tabelle:
>
[pratiche.template_flussi](template_flussi.md)
> [config.esiti_flussi_pratiche](../../config/manual/esiti_flussi_pratiche.md)

---
### 🎯 Scopo Principale

Guard **config-time** delle invarianti di coerenza dell'asse esito del template-step
(`modalita_esito` / `esito_default` / `direzione`). I CHECK di dominio (insiemi di valori
ammessi) vivono come constraint sulla tabella; qui vive la **coerenza tra i campi**, con
errore parlante — sono errori di disegno del template mostrati nel drawer di
amministrazione.

---

### Trigger associato

| Trigger | Timing | Evento | Tabella |
|---|---|---|---|
| `trg_template_flussi_a10_guard_modalita_esito_ins_upd` | BEFORE | INSERT, UPDATE OF `modalita_esito`, `esito_default`, `direzione` | `pratiche.template_flussi` |

Fase `_a10_` (guard/block). Scritture rare (configurazione template) → costo a runtime
trascurabile.

---

### Regole (invarianti)

| Inv | Regola | Errore |
|---|---|---|
| **Inv1** | `modalita_esito IN (AUTOMATICO, CONTESTUALE)` ⇒ `esito_default` **obbligatorio** (un automatismo deve sapere quale esito scrivere) | `TEMPLATE_FLUSSO_ESITO_DEFAULT_OBBLIGATORIO` (494) |
| **Inv2** | `modalita_esito = AUTOMATICO` ⇒ `direzione = INTERNA` (un esito automatico su ENTRATA/USCITA fabbricherebbe la risposta di una controparte esterna) | `TEMPLATE_FLUSSO_AUTOMATICO_SOLO_INTERNA` (495) |
| **Inv3** | `modalita_esito = DOMINIO` ⇒ `esito_default` **vietato** (l'esito lo calcola a runtime il building block di dominio; un default mascherebbe errori) | `TEMPLATE_FLUSSO_DOMINIO_ESITO_DEFAULT_VIETATO` (505) |
| **Inv4** | `modalita_esito IN (AUTOMATICO, CONTESTUALE)` ⇒ `esito_default` deve essere un **verdetto** (`is_verdetto = true`): gli esiti di ramo sono calcolati dal dominio, mai applicabili come default | `TEMPLATE_FLUSSO_ESITO_DEFAULT_NON_VERDETTO` (506) |

Semantica dei quattro valori di `modalita_esito`:

* **MANUALE** (default) — avvio, poi form esito manuale (comportamento classico);
* **AUTOMATICO** — avvia+completa con `esito_default` senza scelta umana (solo INTERNA, Inv2);
* **CONTESTUALE** — avvia+completa con `esito_default` pre-selezionato e confermato
  dall'operatore in un'unica azione;
* **DOMINIO** — l'esito è **calcolato da un building block di dominio** (es.
  `vendite.completa_smistamento` → `MERCE_PRESENTE`/`SOLO_SERVIZI`); nessuna scelta
  operatore; al completamento sono ammessi solo esiti di ramo `is_verdetto = false`
  (guard runtime [trgfn_flussi_guard_esito_classe](trgfn_flussi_guard_esito_classe.md), 504).

> **DOMINIO ≠ bivio.** Gli step "bivio su verdetto" (l'operatore sceglie
> POSITIVO/NEGATIVO e i prerequisiti esito-aware ramificano) **non** sono DOMINIO:
> restano MANUALE/CONTESTUALE. DOMINIO marca solo gli step il cui esito è calcolato.

---

### Note operative

* **Perché Inv4 esiste**: dal `20260702` (migration `20260701-02`) `esito_default` è FK a
  `config.esiti_flussi_pratiche(codice_interno)` **senza** vincolo di classe (il vecchio
  CHECK sui 4 verdetti è stato rimosso); senza Inv4 un default di ramo esploderebbe solo
  a runtime sul guard 504 — meglio fail-fast a config-time.
* **Storia**: Inv1/Inv2 introdotte con `20260617-02`
  (brief-db-esito-configurabile-flussi); Inv1 riformulata (da `<> MANUALE` a
  `IN (AUTOMATICO, CONTESTUALE)`) + Inv3/Inv4 con `20260702-16`
  (brief-db-step-dominio-e-definizioni-versionate, Parte 1).
* Errori via `script.fn_log_and_raise_error(...)`, codici registrati in
  `config.messaggi_errore`.
* Test: `db/pgtap/pratiche/test-esito-configurabile-template-flussi.sql`
  (casi 2–8 Inv1/Inv2 e CHECK; casi 10–12 riformulazione Inv1, Inv3, Inv4).
