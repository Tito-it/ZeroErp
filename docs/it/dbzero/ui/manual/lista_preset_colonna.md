## 📘 Documentazione Concettuale – Tabella `ui.lista_preset_colonna`

> **Ultimo aggiornamento**: 20 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.lista_preset](/dbzero/ui/tabelle/lista_preset) — il preset di cui la riga è una parte
> * [ui.lista_colonna](/dbzero/ui/tabelle/lista_colonna) — la colonna del catalogo citata
> * [dbops.automazione_attivo_eccezioni](/dbzero/dbops/tabelle/automazione_attivo_eccezioni) — perché la riga non blocca lo spegnimento
>
> Approfondimento funzioni:
>
> * [ui.trgfn_preset_riga_tocca_preset](/dbzero/ui/funzioni/trgfn_preset_riga_tocca_preset) — ogni cambio di riga sposta la data del contenuto del preset
> * [ui.fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config) — legge le righe del preset di base
>
> Guide:
>
> * [Configurazione liste](/guide/configurazione-liste) — la composizione di un preset

---

### 🎯 Scopo Principale

`ui.lista_preset_colonna` è la composizione di un preset di lista: una riga per ogni colonna del
catalogo che il preset include, con la sua posizione, la larghezza, se si vede subito e se è
fissata a sinistra.

---

### Che cosa dice una riga

* `ordine` è la posizione della colonna nel preset.
* `larghezza` vuota vuol dire «la larghezza di default del catalogo».
* `visibile` falso mette la colonna nel **pool**: c'è fra quelle che l'utente può accendere, ma la
  lista non la mostra di partenza.
* `fissata` vero la tiene ferma quando la lista scorre in orizzontale.

La chiave è (preset, colonna): una colonna compare al più una volta per preset.

---

### Che cosa ne fa la cascata

Il resolver prende le righe del preset di base che citano colonne **accese** del catalogo, in
ordine. Poi le normalizza come ogni altra configurazione: una colonna identificatore o azione si
vede sempre, un identificatore è sempre fissato, una colonna bloccata per l'utente sparisce. Una
colonna accesa del catalogo che il preset non cita entra in coda, nascosta, e conta fra le colonne
nuove.

---

### ⭐ Una parte, non un figlio

La riga non ha `attivo` né audit: è una parte del preset. Per questo le due FK sono in eccezione
alla regola ATTIVO: spegnere il preset o la colonna del catalogo non si ferma qui, e quale parte
mostrare lo decide il resolver. Cancellare il preset cancella le righe; una colonna del catalogo
citata da un preset non si cancella (FK senza azione).

Una composizione cambiata sposta la chiave `colonne` della data del contenuto del preset. Lo
giudica a fine transazione un trigger differito
([trgfn_preset_riga_tocca_preset](/dbzero/ui/funzioni/trgfn_preset_riga_tocca_preset)),
sull'impronta della composizione: il servizio di amministrazione salva la composizione cancellando
tutte le righe e reinserendole, e una composizione salvata uguale non sposta niente.

---

### ⚠️ Che cosa oggi non copre

* **La colonna di un'altra lista.** Nessun vincolo chiede che la colonna appartenga alla stessa
  lista del preset. Una riga che cita la colonna di un'altra lista entra; il resolver la abbina per
  codice alle colonne della lista del preset, e se un codice uguale c'è prende ordine e larghezza
  di una colonna diversa, altrimenti la scarta in silenzio.

---

### Codici errore

Nessuno proprio. Le violazioni di chiave e di FK arrivano come errori di vincolo; il servizio di
amministrazione le traduce in `E_UI_PRESET_VALIDAZIONE`.

---

### Test

* `db/pgtap/ui/test-fn-resolve-lista-config-cascata-per-chiave-v1.sql` — riga riscritta uguale,
  cambiata, aggiunta e tolta: la chiave `colonne` della data del contenuto; coi vincoli differiti,
  DELETE + INSERT delle stesse righe non sposta niente.
* `db/pgtap/ui/test-seed-primo-impianto-ui-installazione-v1.sql` — la composizione di un preset di
  seed riscritta uguale non lo personalizza.
* `db/pgtap/ui/test-fn-resolve-lista-config.sql` — le colonne del preset nella cascata.
* `db/pgtap/ui/test-liste-preset-default-v1.sql` — il preset di default di ogni lista del seed ha
  le sue colonne.
* `db/pgtap/ui/test-ui-nell-ambito-v1.sql` — le due FK in eccezione ATTIVO.

---

### Note di migrazione

* 2026-11-01 — le righe spostano la data del preset, con un trigger condiviso con i widget dei
  preset di dashboard.
* 2026-11-08 — le due FK entrano fra le eccezioni ATTIVO come righe di composizione.
* 2026-11-20 — la composizione si giudica a fine transazione, sull'impronta: la sostituzione in
  blocco di una composizione uguale non sposta più la data.

---

{% include-markdown "signature-core.md" %}
