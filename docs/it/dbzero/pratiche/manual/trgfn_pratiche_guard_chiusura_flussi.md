## 📘 Documentazione Trigger Function – `pratiche.trgfn_pratiche_guard_chiusura_flussi`

> 👀 **Vedi anche**
>
Funzioni collegate:
>
[pratiche.fn_check_chiusura_pratica](fn_check_chiusura_pratica.md)
> [pratiche.fn_pratica_flussi_aperti](fn_pratica_flussi_aperti.md)
> [pratiche.trgfn_pratiche_guard_transizione](trgfn_pratiche_guard_transizione.md)

---
### 🎯 Scopo Principale
Guard di **chiusura pratica**: blocca la transizione a `CHIUSA` quando la pratica ha
**ancora lavoro da fare**. Due condizioni, entrambe verificate:

* **(a)** template `obbligatorio = true` non completati e **ancora percorribili**
  (`fn_check_chiusura_pratica`, decisione D4). Il **ramo morto** di un bivio
  (prerequisito esito-aware non piu' soddisfacibile) **non blocca**.
* **(b)** flussi **istanziati** in stato **non terminale**
  ([fn_pratica_flussi_aperti](fn_pratica_flussi_aperti.md), clausola **D1**): anche uno
  step **opzionale** avviato e lasciato aperto impedisce la chiusura.

E' lo **stesso predicato** dell'auto-chiusura (`fn_check_pratica_chiudibile`): chiusura
manuale e automatica non divergono.

---

### Trigger associato

| Trigger | Timing | Evento | Tabella |
|---|---|---|---|
| `trg_pratiche_a10_guard_chiusura_flussi_upd` | BEFORE | UPDATE OF `stato_id` | `pratiche.pratiche` |

Fase `_a10_`. Convive con `trg_pratiche_a10_guard_transizione_upd` (matrice transizioni):
questo guard valida il *contenuto* della pratica, quello la *legalita'* della transizione.
Fra i due `_a10_` scatta **prima** (ordine alfabetico) → l'errore di contenuto prevale.

---

### Regole

1. Scatta solo alla **transizione** di stato verso `CHIUSA` (`ANNULLATA` resta libera —
   si annulla anche una pratica a meta').
2. Clausola (a): `fn_check_chiusura_pratica(NEW.id)` con righe `bloccante = true` →
   errore con l'elenco dei codici template.
3. Clausola (b): `fn_pratica_flussi_aperti(NEW.id)` non vuota → errore con l'elenco dei
   flussi aperti (codice + stato).

---

### ⚠️ Errori sollevati

| Codice errore | Condizione |
|---------------|------------|
| `PRATICHE_CHIUSURA_FLUSSI_OBBLIGATORI_MANCANTI` (485) | Transizione a CHIUSA con obbligatori non completati ancora percorribili. Placeholder: codici template bloccanti |
| `PRATICHE_CHIUSURA_FLUSSI_APERTI` (501) | Transizione a CHIUSA con flussi istanziati non terminali. Placeholder: elenco flussi aperti (codice/stato) |

---

### Note operative

* I tipi prestazione **senza** obbligatori e **senza** flussi aperti non sono
  interessati (guard no-op).
* **Via d'uscita** per la clausola (b): portare i flussi opzionali rimasti aperti ad
  `ANNULLATO` (transizione `DA_ESEGUIRE/IN_CORSO → ANNULLATO`), poi ripetere la chiusura.
* La catena PREVENTIVI (bivio: step obbligatori-su-ramo) chiude solo a giro completo del
  ramo attivo; il ramo morto non vincola — comportamento voluto.
* Test: `db/pgtap/pratiche/test-chiusura-nessun-lavoro-pendente.sql` (chiusura manuale
  bloccata con flusso opzionale aperto; sbloccata dopo annullamento).
