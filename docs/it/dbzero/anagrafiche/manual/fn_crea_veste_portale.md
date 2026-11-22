## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_crea_veste_portale`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali) — la riga che la funzione scrive
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_accendi_veste](/dbzero/anagrafiche/funzioni/fn_accendi_veste) — accende la veste nata spenta
> * [anagrafiche.fn_crea_operatore_v2](/dbzero/anagrafiche/funzioni/fn_crea_operatore_v2) — la madre della veste OPERATORE, che qui si rifiuta
> * [script.fn_scrivi_riga_da_jsonb](/dbzero/script/funzioni/fn_scrivi_riga_da_jsonb) — lo scrittore generico che la funzione usa
> * [anagrafiche.trgfn_identita_digitali_guard_coerenza](/dbzero/anagrafiche/funzioni/trgfn_identita_digitali_guard_coerenza) — la veste dev'essere coerente col ruolo
> * [anagrafiche.trgfn_identita_digitali_sync_auth_user_active](/dbzero/anagrafiche/funzioni/trgfn_identita_digitali_sync_auth_user_active) — la credenziale segue le vesti
>
> Guide:
>
> * [Risorse umane e accessi](/guide/risorse-umane-e-accessi) — la veste e la credenziale

---

### 🎯 Scopo Principale

`anagrafiche.fn_crea_veste_portale` dà a una credenziale una veste esterna su un ruolo: l'accesso al portale
clienti, al portale fornitori o allo shop, spenta o accesa. Restituisce l'id della veste.

È la sede unica della creazione di una veste esterna: la usano il backend (l'invito al portale, l'attivazione dello
shop) e il provisioning dei dati di sviluppo. Nessun'altra funzione del database scrive una veste esterna a mano.

---

### ⛔ Solo le tre vesti esterne

Le vesti ammesse sono `CLIENTE_PORTALE`, `FORNITORE_PORTALE` e `SHOP_CUSTOMER`. La veste OPERATORE nasce dalle sue
madri (`anagrafiche.fn_crea_operatore_v2` per una persona, `script.fn_crea_utente_tecnico` per un utente tecnico),
che portano anche il rapporto e il perimetro; ogni altra veste si rifiuta con `E_SCRIPT_CHIAMATA_NON_VALIDA`.

---

### ⭐ Accesa o spenta si dice sempre

Nessun argomento ha un default, e lo stato meno degli altri: quello della colonna (accesa) sarebbe sbagliato per
un invito, che crea la veste spenta e la accende quando la persona accetta. Lo shop la crea accesa. Un argomento
mancante si rifiuta con lo stesso codice di una veste non ammessa.

La veste nasce valida dal giorno operativo, senza scadenza: le date non sono fra gli argomenti, e le mette il
default della tabella.

---

### Il resto lo dicono i controlli della tabella

La funzione scrive con `script.fn_scrivi_riga_da_jsonb`, e la riga passa dai trigger di
`anagrafiche.identita_digitali`: che la veste sia coerente col ruolo (il portale clienti su un ruolo cliente), che
la credenziale sia di una persona e non un utente tecnico, che le vesti **accese** siano uniche per credenziale e
per ruolo. Una veste accesa, se è utilizzabile, accende anche la credenziale (vedi la scheda del trigger di
sincronizzazione).

Il permesso di invitare e il flusso dell'invito (il messaggio, il token, il reinvio) non sono qui: li gestisce il
backend.

---

### Codici errore

| Codice | Quando |
| --- | --- |
| `E_SCRIPT_CHIAMATA_NON_VALIDA` | un argomento mancante, o una veste che non è una delle tre esterne |

Più quelli dei trigger della tabella.

---

### Test

* `db/pgtap/anagrafiche/test-fn-crea-veste-portale-v1.sql` — la forma (INVOKER); una veste del portale clienti
  spenta, una dello shop accesa sullo stesso ruolo, una del portale fornitori; il rifiuto della veste OPERATORE e
  dello stato mancante; il portale clienti su un ruolo fornitore fermato dal guard di coerenza; che la funzione
  scriva con lo scrittore generico e che nessuna funzione del database scriva una veste esterna a mano.
* Nessun test prova la credenziale o il ruolo mancanti, né che la veste accesa accenda la credenziale.

---

### Note di migrazione

* 2026-10-18 — nasce come sede unica: prende il posto della scrittura del backend per la veste del portale e degli
  inserimenti a mano nei test.

---

{% include-markdown "signature-core.md" %}
