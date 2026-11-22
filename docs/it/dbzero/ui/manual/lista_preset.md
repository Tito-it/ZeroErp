## 📘 Documentazione Concettuale – Tabella `ui.lista_preset`

> **Ultimo aggiornamento**: 21 novembre 2026
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
> * [ui.fn_preset_di_base](/dbzero/ui/funzioni/fn_preset_di_base) — sceglie il preset di base
> * [ui.fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config) — legge le chiavi del preset di base
> * [ui.trgfn_preset_contenuto_aggiornato](/dbzero/ui/funzioni/trgfn_preset_contenuto_aggiornato) — la data del contenuto, dalla testata
> * [ui.trgfn_preset_riga_tocca_preset](/dbzero/ui/funzioni/trgfn_preset_riga_tocca_preset) — la data del contenuto, dalle colonne
> * [ui.trgfn_ui_lista_preset_guard_pagina_dimensione](/dbzero/ui/funzioni/trgfn_ui_lista_preset_guard_pagina_dimensione) — la misura fuori catalogo rifiutata
> * [ui.trgfn_ui_lista_preset_guard_ordinamento](/dbzero/ui/funzioni/trgfn_ui_lista_preset_guard_ordinamento) — la forma dell'ordinamento di partenza
> * [ui.fn_ordinamento_lista](/dbzero/ui/funzioni/fn_ordinamento_lista) — l'ordinamento di partenza risolto per l'utente
> * [dbops.trgfn_child_requires_active_parent](/dbzero/dbops/funzioni/trgfn_child_requires_active_parent) — un preset nasce solo su una lista accesa
>
> Guide:
>
> * [Configurazione liste](/guide/configurazione-liste) — preset, preferenze e cascata viste dall'amministratore

---

### 🎯 Scopo Principale

`ui.lista_preset` contiene le configurazioni predefinite di una lista: quali colonne mostrare
(nelle righe di `lista_preset_colonna`), l'ordinamento di partenza e le righe per pagina. Un preset
vale per tutti (sistema), per un'azienda (emittente fiscale) o per un profilo di accesso (ruolo).

---

### Tre ambiti, un riferimento per ambito

`ambito` dice a chi vale il preset, e il vincolo `chk_ui_lista_preset_ambito_refs` tiene coerente
il riferimento: un preset di sistema non ha né profilo né azienda, uno di ruolo ha solo il
profilo, uno di emittente solo l'azienda.

⛔ **Il posto di un preset non cambia.** La lista, l'ambito, il profilo e l'azienda sono fermati da
un lucchetto di colonna del framework (`E_UI_PRESET_POSTO_IMMUTABILE`): dicono a chi vale il preset, e
le preferenze che lo hanno come base e le righe della sua composizione ci contano. Riscriverli uguali
passa, come fa il seed a ogni giro. Un preset nel posto sbagliato si spegne, e se ne crea uno nuovo
nel posto giusto.

L'unicità `uq_ui_lista_preset_id_lista`, sulla coppia (preset, lista), è la chiave che leggono i
vincoli composti della composizione e della preferenza: una riga di composizione appartiene a un
preset della sua lista, e il preset di base di una preferenza è un preset della lista della
preferenza.

---

### Un preset acceso per posto: vale se è acceso

Un **posto** è la combinazione (lista, ambito, profilo, azienda). L'indice unico parziale
`uq_ui_lista_preset_posto` ammette **un solo** preset acceso per posto, e tratta il profilo e
l'azienda vuoti come un valore della chiave: due preset di sistema accesi della stessa lista sono
rifiutati. Il preset acceso è quello che vale; i preset spenti non entrano mai nella cascata, e
non occupano il posto.

Una **bozza** si prepara spenta, accanto al preset in uso. Per sostituire il preset di un posto si
spegne il vecchio **prima** di accendere il nuovo: l'indice non si differisce a fine transazione, e
accendere la bozza con il vecchio ancora acceso è rifiutato.

Nessuna regola chiede che una lista abbia un preset di sistema: senza, la lista ripiega sul
catalogo delle colonne.

---

### Che cosa dà un preset alla cascata

[fn_preset_di_base](/dbzero/ui/funzioni/fn_preset_di_base) sceglie un solo **preset di base** per
l'utente: un preset acceso con almeno una colonna attiva, il ruolo (solo con la veste), poi
l'azienda (solo se accesa), poi il sistema. [fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config)
ne prende, chiave per chiave, ciò che la preferenza dell'utente non sceglie: colonne e righe per
pagina.

* Le colonne sono quelle accese del catalogo citate dalle righe del preset.
* `ordinamento_default` è l'ordinamento con cui la lista parte, e la preferenza non lo
  personalizza: il clic sull'intestazione di una colonna vale per la sessione. È un elenco di
  colonne, citate per **codice**, ciascuna con la sua direzione; la forma la giudica alla scrittura
  [trgfn_ui_lista_preset_guard_ordinamento](/dbzero/ui/funzioni/trgfn_ui_lista_preset_guard_ordinamento),
  che rifiuta anche il campo sorgente al posto del codice. Vuoto vuol dire che il preset non dice da
  che colonna partire. Per l'utente lo risolve
  [fn_ordinamento_lista](/dbzero/ui/funzioni/fn_ordinamento_lista), che toglie le colonne spente, non
  ordinabili o bloccate per lui.
* I filtri di partenza non sono del preset: li decide l'interfaccia di ogni lista.
* `pagina_dimensione` è una misura del catalogo
  [misure_pagina](/dbzero/ui/tabelle/misure_pagina) (FK e guard). Vuota vale lo standard: il
  default del catalogo per l'uso della lista (`COMPATTA` o `PAGINA`, dichiarato da
  [lista_definizione](/dbzero/ui/tabelle/lista_definizione)). La colonna non ha un default
  proprio: un preset che nasce senza indicarla segue il catalogo.

---

### ⭐ `contenuto_aggiornato_il`: la data del contenuto, per chiave, non dell'audit

`contenuto_aggiornato_il` dice quando è cambiato l'ultima volta ciò che il preset **mostra**, una
data per chiave: un oggetto `{chiave: data}` con `colonne` e `pagina_dimensione`, le chiavi che
una preferenza può personalizzare. Il banner «preset
aggiornato» la confronta, chiave per chiave, con lo snapshot salvato nella preferenza, e guarda
solo le chiavi che la preferenza imposta. La scrive solo il database, con la funzione condivisa con
i preset delle dashboard,
[trgfn_preset_contenuto_aggiornato](/dbzero/ui/funzioni/trgfn_preset_contenuto_aggiornato): alla
nascita della riga tutte le chiavi, poi la chiave la cui colonna cambia (`pagina_dimensione`, e
per `colonne` l'impronta della composizione). Un cambio di `ordinamento_default` non sposta niente:
non è una chiave della preferenza, e lo segue subito chi ha il preset come base. Chi la
scrive riceve `E_UI_PRESET_CONTENUTO_DERIVATO`.

`composizione_impronta` è l'impronta della composizione
([fn_preset_impronta](/dbzero/ui/funzioni/fn_preset_impronta)). La scrive a fine transazione il
trigger differito delle colonne del preset,
[trgfn_preset_riga_tocca_preset](/dbzero/ui/funzioni/trgfn_preset_riga_tocca_preset), solo quando
la composizione è davvero cambiata: il servizio di amministrazione la riscrive cancellando e
reinserendo le righe, e una riscrittura uguale non sposta niente. Un valore diverso dall'impronta di
oggi è rifiutato con lo stesso codice. Per il seed di primo impianto le due colonne sono
dell'installazione: una composizione cambiata dall'installazione personalizza il preset di seed.

Una riscrittura uguale non sposta la data: il seed riscrive ogni riga a ogni giro, e il banner si
accenderebbe a tutti. `data_update` e `user_update` restano l'audit del framework, che si sposta a
ogni scrittura. Non sono contenuto codice, descrizione, ambito e `attivo`: accendere
o spegnere un preset cambia **quale** preset sta sotto una preferenza, non che cosa dice.

---

### Che cosa blocca e che cosa no

* La lista spenta sospende i suoi preset senza toccarli: si spegne anche con preset accesi, e un
  preset si accende anche sotto una lista spenta (la FK verso la lista è in eccezione ATTIVO). Una
  lista spenta non risponde, quindi i suoi preset non entrano in nessuna cascata finché non si
  riaccende.
* Spegnere un profilo o un'azienda non si ferma sul preset (le due FK sono in eccezione): il
  preset resta, e la cascata non lo usa più, perché il profilo non è più fra quelli dell'utente e
  il preset di un'azienda spenta non si applica.
* Cancellare un preset cancella le sue colonne; le preferenze che lo avevano come base restano,
  senza base e senza snapshot.
* Le righe della composizione nominano solo colonne della lista del preset (lo dice la pagina di
  [lista_preset_colonna](/dbzero/ui/tabelle/lista_preset_colonna)).

---

### Codici errore

* `E_UI_MISURA_PAGINA_NON_AMMESSA` — `pagina_dimensione` fuori dal catalogo delle misure.
* `E_UI_PRESET_POSTO_IMMUTABILE` — si cambia la lista, l'ambito, il profilo o l'azienda di un preset.
* `E_UI_CONFIGURAZIONE_FORMA` — `ordinamento_default` senza la forma ammessa (una colonna che non è
  un codice della lista, ripetuta, una direzione fuori dominio).
* Le unicità (codice per lista, un preset acceso per posto) e il vincolo dell'ambito arrivano come
  violazione di vincolo; il servizio di amministrazione le traduce in `E_UI_PRESET_VALIDAZIONE`.

---

### Test

* `db/pgtap/ui/test-fn-resolve-lista-config.sql` — preset di sistema e di profilo nella cascata.
* `db/pgtap/ui/test-fn-resolve-lista-config-cascata-per-chiave-v1.sql` — le chiavi prese dal
  preset, la data del contenuto (riscrittura uguale, cambio di testata e di colonne).
* `db/pgtap/ui/test-fn-resolve-lista-config-preset-aggiornato-v1.sql` — il flag contro lo snapshot.
* `db/pgtap/ui/test-fn-preset-di-base-v1.sql` — la scelta del preset di base; un secondo preset
  acceso nello stesso posto rifiutato, uno spento accettato.
* `db/pgtap/ui/test-liste-preset-default-v1.sql` — ogni lista del seed ha il suo preset di sistema.
* `db/pgtap/ui/test-ui-nell-ambito-v1.sql` — audit NOT NULL, eccezioni ATTIVO, trigger del contenuto.
* `db/pgtap/ui/test-ui-misure-catalogo-e-uso-v1.sql` — un preset senza misura scrive NULL e segue
  l'uso della lista.
* `db/pgtap/ui/test-misure-pagina-v1.sql` — la misura del preset nel catalogo.
* `db/pgtap/ui/test-ui-forma-configurazione-v1.sql` — la forma dell'ordinamento, l'ordinamento
  risolto per l'utente, la data del contenuto con le sole chiavi `colonne` e `pagina_dimensione`, la
  colonna `filtri_default` che non c'è più.
* `db/pgtap/ui/test-ui-legami-preset-v1.sql` — cambiare la lista di un preset è rifiutato, riscrivere
  il posto uguale passa; il preset di base di un'altra lista rifiutato sulla preferenza; cancellato il
  preset, la preferenza resta senza base.
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
* 2026-11-20 — `is_default` si ritira, e con lui l'indice `uq_ui_lista_preset_default`, che contava
  anche i preset spenti: la cascata leggeva solo i preset di default accesi, e un preset acceso non
  di default non lo leggeva nessuno. I preset in quello stato sono stati spenti. Al suo posto
  `uq_ui_lista_preset_posto`, sui soli preset accesi.
* 2026-11-20 — `contenuto_aggiornato_il` diventa per chiave e la scrive solo il database; nasce
  `composizione_impronta`, e la composizione riscritta uguale non sposta più la data.
* 2026-11-21 — `filtri_default` si ritira: i filtri di partenza sono dell'interfaccia. Nasce il guard
  di `ordinamento_default`; gli ordinamenti scritti col campo sorgente sono stati portati al codice
  della colonna, e quelli che non dicevano una colonna sola sono stati tolti. La data del contenuto
  perde le chiavi `ordinamento` e `filtri`.
* 2026-11-21 — il posto del preset si chiude col lucchetto di colonna: prima lo rifiutava solo il
  servizio di amministrazione. Nasce l'unicità (preset, lista) per i vincoli composti della composizione
  e della preferenza.

---

{% include-markdown "signature-core.md" %}
