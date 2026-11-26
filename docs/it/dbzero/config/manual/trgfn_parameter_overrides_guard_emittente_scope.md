## 📘 Documentazione Concettuale – Funzione `config.trgfn_parameter_overrides_guard_emittente_scope()`

> **Ultimo aggiornamento**: 25 novembre 2026

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> [config.parameter_overrides](/dbzero/config/tabelle/parameter_overrides)
> [config.user_emittenti_fiscali](/dbzero/config/tabelle/user_emittenti_fiscali) — il perimetro dell'operatore
>
Approfondimento funzioni:
> [script.fn_check_user_emittente_scope](/dbzero/script/funzioni/fn_check_user_emittente_scope) — la regola di scope, sede unica
> [script.trgfn_guard_emittente_scope](/dbzero/script/funzioni/trgfn_guard_emittente_scope) — il guard delle tabelle per azienda con la RLS
> [script.fn_utente_di_sessione](/dbzero/script/funzioni/fn_utente_di_sessione) — chi agisce
>
Guide:
> [Configurazione e gestione parametri](/guide/configurazione-e-gestione-parametri) — i riferimenti degli ambiti
> [Architettura dei permessi](/guide/architettura-permessi-e-autorizzazioni) — §7.2, il guard di scope

### 🎯 Scopo Principale

Un override **per emittente** appartiene a quell'azienda: lo crea, lo modifica e lo cancella solo chi
la ha nel suo perimetro, secondo `script.fn_check_user_emittente_scope`. Chi ha scelto un'azienda
lavora solo su quella, anche se è super admin. Il rifiuto è `E_SCOPE_EMITTENTE`.

La applica il trigger `trg_parameter_overrides_a10_guard_emittente_scope_ins_upd_dlt`
(`BEFORE INSERT OR UPDATE OR DELETE`, per riga).

### Le scelte

* **Non il building block `script.trgfn_guard_emittente_scope`.** La tabella non ha la row level
  security, ed è giusto così: è configurazione letta da tutti. Il building block lavora accanto a
  una policy, che toglie di mezzo le righe delle altre aziende: per questo salta l'`UPDATE` quando
  l'emittente non cambia, non guarda il `DELETE` e, senza utente, chiede a `row_security_active()`.
  Qui nessuna policy fa quella parte, e il guard la fa da sé.
* **La riga di prima e quella di dopo.** In `INSERT` si giudica la riga nuova, in `DELETE` quella
  che si cancella, in `UPDATE` tutte e due, anche quando l'emittente non cambia: il valore
  dell'override di un'altra azienda non si cambia. Spostare un override su un'altra azienda chiede
  il perimetro su tutte e due; la colonna non è bloccata, perché l'override non ha figli e lo
  storico registra la versione.
* **Nessun padrone, nessun controllo.** Gli override per utente, gruppo, categoria cliente e
  funzione hanno l'emittente vuoto e passano.
* **Senza utente in sessione**, su una riga con padrone, passa solo la sessione che la row level
  security non filtrerebbe se ci fosse: superuser, `BYPASSRLS` o il proprietario della tabella
  (anche per appartenenza al ruolo), fuori da una funzione `SECURITY DEFINER`. Il criterio è scritto
  per esteso perché `row_security_active()` su questa tabella non risponde. Chi altrimenti:
  `E_SCOPE_SENZA_UTENTE`.
* **In «tutti gli emittenti» il super admin passa**, per il bypass di
  `fn_check_user_emittente_scope`, come sulle altre tabelle per azienda. Che «tutti» sia sola
  lettura lo garantisce oggi l'applicazione.
* **Fase `a10`**, dopo `a05` (il parametro si personalizza?), `a07` (la forma del valore) e il
  dispatcher FK-surrogata: su una scrittura che quelli rifiutano parla la loro frase, e la scrittura
  è rifiutata comunque. Sul `DELETE` parla solo questo guard.

### Storia

* 2026-11-25 — nasce (`20261124-13`), brief-db-emittente-del-super-admin §3.1 (R-DB-1). Fino a quel
  giorno un override per emittente entrava senza un controllo sull'azienda di chi scriveva, e il
  backend li scriveva tutti sul gestore globale.

{% include-markdown "signature-core.md" %}
