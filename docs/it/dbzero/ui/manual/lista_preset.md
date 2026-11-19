## 📘 Documentazione Concettuale – Tabella `ui.lista_preset`

> **Ultimo aggiornamento**: 18 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.lista_definizione](/dbzero/ui/tabelle/lista_definizione) — la lista a cui il preset appartiene
> * [ui.lista_preset_colonna](/dbzero/ui/tabelle/lista_preset_colonna) — le colonne del preset
> * [ui.lista_preferenza_utente](/dbzero/ui/tabelle/lista_preferenza_utente) — la preferenza che parte da un preset
> * [ui.misure_pagina](/dbzero/ui/tabelle/misure_pagina) — le misure «righe per pagina» ammesse
> * [config.profili_accesso](/dbzero/config/tabelle/profili_accesso) — il profilo di un preset di ruolo
> * [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali) — l'azienda di un preset di emittente
> * [dbops.automazione_attivo_eccezioni](/dbzero/dbops/tabelle/automazione_attivo_eccezioni) — perché profilo e azienda spenti non si fermano sul preset
>
> Approfondimento funzioni:
>
> * [ui.fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config) — sceglie il preset di base e ne legge le chiavi
> * [ui.trgfn_preset_contenuto_aggiornato](/dbzero/ui/funzioni/trgfn_preset_contenuto_aggiornato) — la data del contenuto, dalla testata
> * [ui.trgfn_preset_riga_tocca_preset](/dbzero/ui/funzioni/trgfn_preset_riga_tocca_preset) — la data del contenuto, dalle colonne
> * [ui.trgfn_ui_lista_preset_guard_pagina_dimensione](/dbzero/ui/funzioni/trgfn_ui_lista_preset_guard_pagina_dimensione) — la misura fuori catalogo rifiutata
> * [dbops.trgfn_child_requires_active_parent](/dbzero/dbops/funzioni/trgfn_child_requires_active_parent) — un preset nasce solo su una lista accesa
>
> Guide:
>
> * [Configurazione liste](/guide/configurazione-liste) — preset, preferenze e cascata viste dall'amministratore

---

### 🎯 Scopo Principale

`ui.lista_preset` contiene le configurazioni predefinite di una lista: quali colonne mostrare
(nelle righe di `lista_preset_colonna`), l'ordinamento, i filtri e le righe per pagina. Un preset
vale per tutti (sistema), per un'azienda (emittente fiscale) o per un profilo di accesso (ruolo).

---

### Tre ambiti, un riferimento per ambito

`ambito` dice a chi vale il preset, e il vincolo `chk_ui_lista_preset_ambito_refs` tiene coerente
il riferimento: un preset di sistema non ha né profilo né azienda, uno di ruolo ha solo il
profilo, uno di emittente solo l'azienda.

Il database non impedisce di cambiare dopo la nascita la lista, l'ambito, il profilo o l'azienda
di un preset: lo rifiuta solo il servizio di amministrazione.

---

### Il preset di default: al più uno per posto, spento compreso

Della cascata fanno parte solo i preset `is_default` e accesi. L'indice unico parziale
`uq_ui_lista_preset_default` ammette **un solo** preset di default per (lista, ambito, profilo,
azienda), e conta anche quelli spenti: un preset di default spento occupa il posto, e per
nominarne un altro si toglie prima il flag al vecchio. Un preset non di default non entra mai
nella cascata: resta a disposizione dell'amministrazione.

Nessuna regola chiede che una lista abbia un preset di default di sistema: senza, la lista
ripiega sul catalogo delle colonne.

---

### Che cosa dà un preset alla cascata

[fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config) sceglie un solo **preset di
base** per l'utente (ruolo, poi azienda, poi sistema: la regola esatta è nella sua pagina) e ne
prende, chiave per chiave, ciò che la preferenza dell'utente non sceglie: colonne, ordinamento,
filtri e righe per pagina.

* Le colonne sono quelle accese del catalogo citate dalle righe del preset.
* `ordinamento_default` e `filtri_default` passano così come sono scritti: il database non
  verifica che nominino colonne della lista, ordinabili o filtrabili.
* `pagina_dimensione` è una misura del catalogo
  [misure_pagina](/dbzero/ui/tabelle/misure_pagina) (FK e guard). Vuota vale il default `PAGINA`
  del catalogo, ma la colonna ha un `DEFAULT` proprio di 25: un preset che nasce senza indicarla
  ha 25 scritto, non «vuoto».

---

### ⭐ `contenuto_aggiornato_il`: la data del contenuto, non dell'audit

`contenuto_aggiornato_il` dice quando è cambiato l'ultima volta ciò che il preset **mostra**, e la
confronta il flag «preset aggiornato» con lo snapshot salvato nella preferenza. Nasce con la riga
e la spostano due trigger, sulle funzioni condivise con i preset delle dashboard:

* [trgfn_preset_contenuto_aggiornato](/dbzero/ui/funzioni/trgfn_preset_contenuto_aggiornato),
  quando cambiano `ordinamento_default`, `filtri_default` o `pagina_dimensione`;
* [trgfn_preset_riga_tocca_preset](/dbzero/ui/funzioni/trgfn_preset_riga_tocca_preset), quando
  una colonna del preset si aggiunge, si toglie o cambia.

Una riscrittura uguale non la sposta: il seed riscrive ogni riga a ogni giro, e il banner si
accenderebbe a tutti. `data_update` e `user_update` restano l'audit del framework, che si sposta a
ogni scrittura. Non sono contenuto codice, descrizione, ambito, `is_default` e `attivo`: accendere
o spegnere un preset cambia **quale** preset sta sotto una preferenza, non che cosa dice.

---

### Che cosa blocca e che cosa no

* Una lista con preset accesi non si spegne, e un preset nasce o si riaccende solo su una lista
  accesa (regola ATTIVO, controllo differito a fine transazione).
* Spegnere un profilo o un'azienda non si ferma sul preset (le due FK sono in eccezione): il
  preset resta, e la cascata non lo usa più perché il profilo non è più fra quelli dell'utente.
* Cancellare un preset cancella le sue colonne; le preferenze che lo avevano come base perdono il
  riferimento e il loro snapshot.

---

### ⚠️ Che cosa oggi non copre

* **La lista di una colonna.** Nessun vincolo chiede che le colonne di un preset appartengano
  alla lista del preset (lo dice la pagina di
  [lista_preset_colonna](/dbzero/ui/tabelle/lista_preset_colonna)).
* **Ordinamento e filtri non verificati.** `ordinamento_default` e `filtri_default` possono
  nominare colonne spente, non ordinabili, non filtrabili o bloccate per l'utente, e passano così
  al frontend. Nel seed l'ordinamento usa due convenzioni (il codice della colonna o il campo
  sorgente).
* **Il `DEFAULT` 25.** È una seconda sede del default `PAGINA` del catalogo: se il default del
  catalogo cambia, i preset nati senza misura restano a 25.
* **La data del contenuto si scrive a mano.** Un INSERT o un UPDATE dell'applicazione può
  scrivere `contenuto_aggiornato_il` a qualunque valore senza cambiare il contenuto.
* **Il ruolo dopo il primo.** Fra i preset di ruolo la cascata guarda solo quello del profilo più
  prioritario: se non ha colonne accese, passa all'azienda senza guardare i profili successivi.

---

### Codici errore

* `E_UI_MISURA_PAGINA_NON_AMMESSA` — `pagina_dimensione` fuori dal catalogo delle misure.
* Le regole ATTIVO del framework — preset su una lista spenta, lista spenta con preset accesi.
* Le unicità (codice per lista, il default per posto) e il vincolo dell'ambito arrivano come
  violazione di vincolo; il servizio di amministrazione le traduce in `E_UI_PRESET_VALIDAZIONE`.

---

### Test

* `db/pgtap/ui/test-fn-resolve-lista-config.sql` — preset di sistema e di profilo nella cascata.
* `db/pgtap/ui/test-fn-resolve-lista-config-cascata-per-chiave-v1.sql` — le chiavi prese dal
  preset, la data del contenuto (riscrittura uguale, cambio di testata e di colonne).
* `db/pgtap/ui/test-fn-resolve-lista-config-preset-aggiornato-v1.sql` — il flag contro lo snapshot.
* `db/pgtap/ui/test-liste-preset-default-v1.sql` — ogni lista del seed ha il suo preset di default.
* `db/pgtap/ui/test-ui-nell-ambito-v1.sql` — audit NOT NULL, eccezioni ATTIVO, trigger del contenuto.
* `db/pgtap/ui/test-misure-pagina-v1.sql` — la misura del preset nel catalogo.
* `db/pgtap/dbops/test-codice-maiuscolo-v1.sql`, `db/pgtap/dbops/test-user-update-not-null-v1.sql`
  — le regole trasversali sulla tabella.

---

### Note di migrazione

* 2026-09-30 — `pagina_dimensione` passa al catalogo delle misure (FK e guard).
* 2026-11-01 — la cascata diventa per chiave: il preset di base dà le chiavi che la preferenza
  non ha.
* 2026-11-08 — la data del contenuto passa da `data_update` a `contenuto_aggiornato_il`;
  `data_update` e `user_update` diventano l'audit del framework, e lo schema `ui` entra
  nell'ambito delle automazioni (le FK verso profilo e azienda in eccezione ATTIVO).

---

{% include-markdown "signature-core.md" %}
