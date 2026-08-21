## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_preventivi_guard_transizione()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [vendite.preventivi](/dbzero/vendite/tabelle/preventivi)
> • [config.stati_doc_preventivi](/dbzero/config/tabelle/stati_doc_preventivi)
> • [config.transizioni_stati_preventivi](/dbzero/config/tabelle/transizioni_stati_preventivi)
>
Approfondimento funzioni:
> • [vendite.trgfn_preventivi_guard_annullamento](/dbzero/vendite/funzioni/trgfn_preventivi_guard_annullamento)
> • [vendite.fn_cambia_stato_preventivo](/dbzero/vendite/funzioni/fn_cambia_stato_preventivo)
>
Pattern correlato (domini gemelli):
> • [vendite.trgfn_ordini_guard_transizione](/dbzero/vendite/funzioni/trgfn_ordini_guard_transizione)

---
### 🎯 Scopo Principale

(rev 2026-08-21 — creata 2026-08-05, brief vie-uscita-operatore §6.2, §7.4 p.3)

**Enforcement DB-first del grafo transizioni del preventivo.** Una transizione
`OLD.stato → NEW.stato` è ammessa solo se presente e **attiva** in
`config.transizioni_stati_preventivi`.

Il grafo non è hardcodato: viene letto dalla matrice, la **stessa** che alimenta
`fn_available_actions_preventivo`. Da qui la proprietà che conta davvero — la UI non può
proporre ciò che il database rifiuta, né il contrario. Un solo dato, due consumatori.

Porta il preventivo in linea con ordine, DDT, commessa, reso, contratto e offerta, che
avevano già il loro guard di transizione.

---

### Aggancio

Trigger `trg_preventivi_a10_guard_transizione_upd` — fase `_a10_`,
`BEFORE UPDATE OF stato_doc_preventivo_id` su `vendite.preventivi`, `FOR EACH ROW`.

Intercetta **ogni** chiamante — la porta `fn_cambia_stato_preventivo`, gli handler
applicativi, un `UPDATE` diretto: nessuna strada può forzare una transizione illegale.

---

### Regole applicate

1. **No-op** se `stato_doc_preventivo_id` non è distinto dal precedente (`UPDATE` su altre
   colonne dello stesso set).
2. Risolve i `codice_interno` dei due stati, per un messaggio leggibile.
3. Regola unica: la coppia `(stato_da, stato_a)` deve esistere in
   `config.transizioni_stati_preventivi` con `attivo IS TRUE`.

---

### ⚠️ Che cosa **non** fa, per scelta

* **Non valuta l'ammissibilità dell'annullamento.** Quella ha il suo guard dedicato,
  `trgfn_preventivi_guard_annullamento`. Qui si verifica che la strada *esista*, non che sia
  *percorribile*.
* **Non impone la regola «documento senza righe»**, che vive ancora dentro la porta
  `vendite.fn_cambia_stato_preventivo`. Un `UPDATE` diretto la aggira. È
  un'**asimmetria dichiarata**, non una dimenticanza: finché resta lì, il DB-first sulle
  transizioni del preventivo è completo sul grafo e incompleto sulle precondizioni.

---

### ⚠️ Chi parla per primo: l'ordine alfabetico decide l'errore

Su `vendite.preventivi` convivono tre guard `BEFORE UPDATE` legati allo stato, e i trigger
`BEFORE ROW` scattano in **ordine alfabetico**:

1. `trg_preventivi_a10_guard_annullamento_upd`
2. `trg_preventivi_a10_guard_transizione_approvazione_upd`
3. `trg_preventivi_a10_guard_transizione_upd` ← **questo, per ultimo**

Conseguenza pratica: se si tenta di annullare un preventivo che ha già figli a valle **e** la
transizione verso `ANNULLATO` non fosse in matrice, l'errore che arriva all'utente è quello
dell'**annullabilità**, non `E_PREV_TRANSIZIONE_NON_AMMESSA`. Questo guard non viene neppure
raggiunto.

Da tenere presente scrivendo i pgTAP: un test che si aspetta il codice della transizione va
costruito su un caso che gli altri due guard lasciano passare.

---

### Codici errore

| Codice | Quando |
|--------|--------|
| `E_PREV_TRANSIZIONE_NON_AMMESSA` | Coppia `(stato_da, stato_a)` assente o non attiva in `config.transizioni_stati_preventivi` |

Sollevato via `script.fn_log_and_raise_error` con `NEW.tx_id` propagato; il context riporta
`preventivo_id`, `numero`, `stato_da` e `stato_a` in codici interni leggibili.

---

{% include-markdown "signature-core.md" %}
