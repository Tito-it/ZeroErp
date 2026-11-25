# Brief DB — l'emittente del super admin: il guard sugli override dei parametri e il profilo senza gestore globale

> **⏭️ Chi riparte — aggiornato al 2026-11-25**
>
> **Riparte: il team DB**, con R-DB-1 e R-DB-2. Il BE è già allineato a tutte e due: non chiede
> niente in cambio e non deve cambiare per primo (§3). Nessuna decisione aperta di Tid, salvo la
> forma di R-DB-2 se il team DB non condivide la raccomandazione (§4.3).
>
> | # | Chi | Che cosa | Dove | Aspetta |
> | --- | --- | --- | --- | --- |
> | 1 | team BE/FE | ✅ La regola unica nel BE: override, assistente AI, gate L2, valuta, cascata (2026-11-25) | §2 | — |
> | 2 | team DB | R-DB-1: `script.trgfn_guard_emittente_scope('fiscale', 'emittente_fiscale_id')` su `config.parameter_overrides`, con il pgTAP | §3 | — |
> | 3 | team DB | R-DB-2: il blocco `emittente` di `script.fn_get_user_profile` senza il ripiego sul gestore globale | §4 | — |
> | 4 | team BE/FE | Dopo R-DB-2: la prova di `/me/` per l'operatore senza emittente (§4.4) | §4.4 | 3 |
>
> **Chi scrive:** sessione BE/FE (`dev/backend-tid`), 2026-11-25. **A chi:** team DB e Tid.
> **Origine:** E1-6 di [brief-be-fe-BB-audit](brief-be-fe-BB-audit.md) (§6.2). L'approfondimento
> completo, con i riferimenti, è in §6.1 di quel brief; qui c'è solo ciò che serve al DB.
> ⚠️ Il lavoro BE descritto in §2 sta su `dev/backend-tid` ed **è ancora da committare** alla data
> di questo brief.

## 1. La regola, decisa da Tid il 2026-11-25

L'emittente su cui si legge o si scrive un valore operativo (parametro, soglia, valuta, emittente
di una scrittura) è:

1. quello **del documento**, quando c'è un documento;
2. altrimenti quello **di chi agisce**, cioè `script.fn_resolve_emittente_for_user`: l'emittente
   attivo se valido per l'utente, poi la riga di `config.user_emittenti_fiscali`.

In «tutti gli emittenti» la risposta è NULL: la lettura salta il livello emittente, come fa già
`script.fn_get_parameter_di_sessione`, e la scrittura si rifiuta con `E_EMITTENTE_NON_RISOLTO`,
come fa già `script.trgfn_default_emittente_fiscale`.

Il **gestore globale** non è un ripiego operativo per chi agisce. Il gestore globale è la riga di
`anagrafiche.emittenti_fiscali_billing_account` con `billing_account_id IS NULL` e `is_default`.

Le guide lo dicono già: la scelta dell'emittente restringe e non allarga mai, «tutti» è sola
lettura, e nessun default dell'installazione si usa per attribuire qualcosa. Il ripiego sul gestore
globale stava solo in due commenti di codice e in `fn_get_user_profile`.

## 2. Cosa ha già fatto il BE (2026-11-25)

Il DB deve sapere cosa il BE emette **oggi**, sul ramo:

* **Override dei parametri per emittente**: si scrivono e si cancellano sull'emittente di chi
  agisce, con il BB `emittente_per_scrivere`. In «tutti» il BE risponde 400
  `E_EMITTENTE_NON_RISOLTO` e non scrive. Fino al 2026-11-25 si scrivevano **sempre sul gestore
  globale**, anche con un altro emittente scelto. Il DB non poteva accorgersene: R-DB-1 nasce
  da qui.
* **Cascata dei parametri lato BE**: l'emittente è quello di chi agisce (BB `contesto_cascata`),
  quindi coincide con `fn_get_parameter_di_sessione`.
* **Gate L2 dei prezzi**: l'emittente è quello della testata del documento.
* **Assistente AI**: legge e scrive sull'emittente di chi agisce, e applica il cancello della
  lista del suo endpoint gemello.
* **Ritirati**: `ParameterRepository/ParameterService.get_emittente_fiscale_id_for_user`, unica
  copia Python della query del gestore globale, e `ai_assistant/services/user_context.
  get_emittente_fiscale_id`, che leggeva il blocco `emittente` del profilo. Dal BE nessuno legge
  più il gestore globale come emittente di chi agisce.

## 3. R-DB-1 — Il guard di scope sugli override dei parametri

**Il fatto.** `config.parameter_overrides` ha i guard di forma (`ammette_override`, tipo del
valore), il padre attivo per emittente e categoria, l'audit e lo storico. **Non ha un guard di
scope sull'emittente.** Una riga con `emittente_fiscale_id` fuori dal perimetro di chi scrive
entra senza errore.

**La richiesta.** Montare `script.trgfn_guard_emittente_scope('fiscale', 'emittente_fiscale_id')`
in BEFORE INSERT e BEFORE UPDATE, come sulle dodici tabelle che lo hanno già in modalità
`'fiscale'`. Il nome e l'ordine del trigger li sceglie il team DB secondo le sue linee guida.

**Cosa ci si aspetta dal guard, e cosa no:**

* gli override per utente, gruppo, categoria e funzione hanno `emittente_fiscale_id` NULL: il
  guard li salta («nessun padrone») ed è corretto;
* un super admin con l'emittente X scelto che scrive un override su Y ≠ X si ferma:
  `fn_check_user_emittente_scope` risponde FALSE prima del bypass;
* un operatore che scrive sul proprio emittente passa;
* ⚠️ **in «tutti» il guard lascia passare** un super admin, per il bypass di
  `fn_check_user_emittente_scope`. La sola lettura di «tutti», su questa tabella, la garantisce
  oggi il BE. Vale anche per le altre dodici tabelle. Se il team DB pensa che vada chiusa a DB,
  è una domanda di modello per Tid e un brief a parte, non questo.

**Una domanda al team DB.** Le dodici tabelle non montano il guard sul DELETE. Il BE cancella un
override per emittente con il filtro sull'emittente di chi agisce, quindi oggi non può cancellare
quello di un'altra azienda. Il team DB decide se per questa tabella il DELETE va coperto, secondo
il suo standard.

**Il pgTAP**, come minimo:

1. super admin con X scelto: INSERT e UPDATE di un override su Y → l'errore del guard;
2. lo stesso super admin su X → passa;
3. operatore sul proprio emittente → passa; su un altro → l'errore;
4. override per utente (emittente NULL) → passa.

**Chi cambia per primo.** Il DB, quando vuole: il BE non scrive più fuori dall'emittente scelto
(§2). Il guard solleva `E_SCOPE_EMITTENTE`, che ha già la sua classe nel registro del BE: non
serve una policy nuova.

## 4. R-DB-2 — Il profilo senza il gestore globale come emittente

### 4.1 Il fatto

Il blocco `emittente` di `script.fn_get_user_profile` è una `UNION ALL` ordinata per priorità:

* priorità 1, la riga di `config.user_emittenti_fiscali`;
* priorità 2, il gestore globale, cioè `emittenti_fiscali_billing_account` con BA NULL,
  `is_default` ed emittente attivo.

Chi non ha una riga di permesso riceve quindi il gestore globale **come se fosse il suo
emittente**. Questo vale per il super admin, con o senza un emittente scelto, e per l'operatore
non ancora configurato.

### 4.2 Chi legge il blocco oggi (verificato sul codice, 2026-11-25)

* **BE, `core/api/me_view.py` `_compute_is_admin_globale`**: legge solo
  `user_emittente_fiscale_id`, che nella riga di priorità 2 è già NULL. Con il blocco NULL il
  risultato non cambia: super admin senza riga = admin globale.
* **FE, `frontend/src/stores/auth.js` `emittenteCorrente`**: per l'admin globale restituisce già
  `null` (il commento spiega che lo fa proprio perché il blocco «riflette il gestore globale»).
  Per l'**operatore senza riga** oggi restituisce il gestore globale. Da lì nasce
  `emittenteScritturaId`, e i form propongono come emittente di scrittura un'azienda che non è
  sua; poi la scrittura la rifiuta il guard di scope (fail-closed). Con il blocco NULL,
  `emittenteCorrente` diventa `null` e i verbi di creazione si spengono, che è lo stato giusto.
* **BE, assistente AI**: leggeva il blocco, ma la lettura è ritirata il 2026-11-25 (§2).

Nessun altro lettore nel BE (`get_user_profile` ha un solo chiamante, `me_view`). Nel FE ci sono
solo due commenti (`pratiche/stores/pratiche.js`, `EmittenteFiscaleField.vue`) che dicono di **non**
usare quel blocco.

### 4.3 La richiesta e la raccomandazione

**Raccomandata (a):** il blocco `emittente` porta **solo** la riga di priorità 1. Senza riga di
permesso è NULL. La priorità 2 si toglie.

**Alternativa (b):** se il team DB vede un lettore che vuole il nome del gestore globale come
etichetta, lo si espone con una chiave **separata**, per esempio `gestore_globale`, mai dentro
`emittente`. La decisione di Tid ammette G «al più come etichetta», non come emittente.

Con (a) non serve nessuna chiave nuova: nessun lettore di §4.2 usa il gestore globale come
etichetta. Se il team DB sceglie (b), lo dice nel brief e la scelta passa da Tid.

### 4.4 Chi cambia per primo, e cosa fa il BE/FE dopo

**Il DB.** Il BE e il FE leggono già il blocco in modo compatibile con il NULL (§4.2). Dopo
l'apply il team BE/FE prova `/me/` con tre utenti:

* il super admin senza riga: `is_admin_globale` resta `true`;
* l'operatore configurato: il blocco resta invariato;
* l'operatore senza riga: blocco NULL, nessun emittente proposto nei form, verbi di creazione
  spenti.

È la riga 4 di «Chi riparte».

## 5. Esaminati e fuori perimetro

Non fanno parte di questa richiesta, e non vanno letti come «da allineare» per analogia:

* il terzo livello di `script.fn_get_ba_emittente_sr_id` (`is_default`) e il ripiego senza BA di
  `anagrafiche.fn_get_emittente_fiscale_id`. Rispondono a «di quale azienda è questo **billing
  account**» (o un lotto senza BA, `vendite.fn_get_or_create_lotto`), non a «chi agisce». La
  predefinita dell'installazione, lì, è il modello;
* il livello 4 della valuta (`anagrafiche.gestori`) di `vendite.fn_get_valuta_id`. Il BE vi si è
  allineato in «tutti».

## 6. Guide

* [configurazione-e-gestione-parametri](../../guide/configurazione-e-gestione-parametri.md),
  §«I riferimenti degli ambiti»: dice «con un guard: non si crea un override verso un emittente o
  una categoria **disattivati**». Con R-DB-1 il guard di scope si aggiunge, e la guida va
  aggiornata nello stesso giro.
* [architettura-permessi-e-autorizzazioni](../../guide/architettura-permessi-e-autorizzazioni.md):
  la regola «restringe, non allarga» di `fn_check_user_emittente_scope` è quella che R-DB-1
  applica. Coerente.
* La pagina manuale di `fn_get_user_profile` (`docs/it/dbzero/script/manual/`, L290-292 e L323)
  descrive la «risoluzione emittente con priorità … fallback gestore globale»: va aggiornata con
  R-DB-2.
