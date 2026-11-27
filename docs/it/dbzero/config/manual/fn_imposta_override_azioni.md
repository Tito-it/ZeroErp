## 📘 Documentazione Concettuale – Funzione `config.fn_imposta_override_azioni`

> **Ultimo aggiornamento**: 27 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.user_override_azioni](/dbzero/config/tabelle/user_override_azioni) — le eccezioni che scrive
>
> Approfondimento funzioni:
>
> * [config.fn_applica_imposta_override](/dbzero/config/funzioni/fn_applica_imposta_override) — la primitiva che le scrive, senza permesso
> * [script.fn_guard_super_admin](/dbzero/script/funzioni/fn_guard_super_admin) — il permesso in prima riga
>
> Guide:
>
> * [Architettura permessi e autorizzazioni](/guide/architettura-permessi-e-autorizzazioni) — §4.8 chi scrive gli override, §7.4 le primitive che l'app non esegue

---

### 🎯 Scopo Principale

**Impostare le eccezioni di un utente sulle azioni di processo.** L'elenco dato **sostituisce** tutte le eccezioni
di quel tipo dell'utente; un elenco vuoto le toglie. Ritorna quante ne scrive. È la strada della
schermata di amministrazione dei permessi.

---

### ⛔ Chi la esegue

Solo il **SUPER_ADMIN**: è il primo controllo del verbo, lo stesso della schermata di
amministrazione. Un operatore, o una chiamata senza utente, riceve `E_PERMESSO_NEGATO` e niente si
scrive.

Un'eccezione dà a una persona un potere che il suo profilo non le dà: per questo la tabella è in
sola lettura per l'applicazione, e il verbo è `SECURITY DEFINER`. Le scrive la primitiva
[`fn_applica_imposta_override`](/dbzero/config/funzioni/fn_applica_imposta_override), che
l'applicazione non esegue.

---

### Regole

* Ogni eccezione porta l'azione, se è concessa o negata, il motivo e, se serve, il periodo di validità.
* **Il motivo è obbligatorio**, anche per l'eccezione che toglie: assente, vuoto o di soli spazi,
  `E_OVERRIDE_MOTIVO_OBBLIGATORIO` sul campo `motivo`, e le eccezioni di prima restano. Si scrive senza
  spazi in testa e in coda. Togliere un'eccezione dall'elenco non lo chiede. La regola sta nella primitiva [`config.fn_applica_imposta_override`](/dbzero/config/funzioni/fn_applica_imposta_override).
* Una chiave assente prende il valore di partenza della colonna (senza data di inizio vale da oggi);
  una chiave scritta vuota scrive vuoto (inizio vuoto = senza inizio).
* Una chiave che la tabella non ammette: `E_CAMPO_NON_AMMESSO`. Utente mancante, elenco o elemento
  malformati: `E_SCRIPT_CHIAMATA_NON_VALIDA`.
* Due eccezioni sulla stessa azione le rifiuta `uq_user_override_azioni_user_azione`; un'azione che non esiste `fk_user_override_azioni_azione`.
* Le date: `valido_al` non prima di `valido_dal`.

Non aggiorna la cache dei permessi del backend: lo fa il backend dopo la chiamata.

---

### Test

`db/pgtap/config/test-override-motivo-obbligatorio-v1.sql` (il motivo), `db/pgtap/config/test-porta-override-permessi-v1.sql`.

---

### Note di migrazione

* 2026-11-27 — nasce, al posto del `DELETE` e degli `INSERT` diretti del backend (brief-db-porte-aperte-dalla-sola-guc, giro 10-quater).

---

{% include-markdown "signature-core.md" %}
