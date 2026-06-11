## 📘 Documentazione Trigger Function – `pratiche.trgfn_flussi_guard_ripetibilita`

> 👀 **Vedi anche**
>
Funzioni collegate:
>
[pratiche.fn_guard_ripetibilita_flusso](fn_guard_ripetibilita_flusso.md)
> [pratiche.fn_check_ripetibilita_flusso](fn_check_ripetibilita_flusso.md)
> [pratiche.trgfn_flussi_guard_prerequisiti](trgfn_flussi_guard_prerequisiti.md)

---
### 🎯 Scopo Principale
Wrapper trigger del **guard di ripetibilita'** (D3): alla creazione di una nuova istanza di flusso applica la regola `template_flussi.ripetibilita` tramite `fn_guard_ripetibilita_flusso`.

---

### Trigger associato

| Trigger | Timing | Evento | Tabella |
|---|---|---|---|
| `trg_flussi_a10_guard_ripetibilita_ins` | BEFORE | INSERT | `pratiche.flussi` |

Fase `_a10_` (guard/block). Ordine lessicografico con gli altri guard: `..._guard_esito_completato` → `..._guard_prerequisiti_ins` → `..._guard_ripetibilita_ins`.

---

### Regole

* Solo per flussi **template-based** (`template_flusso_id NOT NULL`): i flussi manuali bypassano il controllo, come per i prerequisiti.
* Il controllo scatta **solo all'INSERT** (stesso punto dei prerequisiti): le transizioni di stato successive non sono interessate.
* Trigger separato da `trg_flussi_a10_guard_prerequisiti_ins` per separazione di responsabilita'.

---

### Note operative

* Errore sollevato: `PRATICHE_FLUSSO_NON_RIPETIBILE` (483) — vedi `fn_guard_ripetibilita_flusso`.
* Test: `db/pgtap/pratiche/test-ripetibilita-flussi.sql`.
