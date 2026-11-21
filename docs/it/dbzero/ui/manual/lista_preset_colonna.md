## 📘 Documentazione Concettuale – Tabella `ui.lista_preset_colonna`

> **Ultimo aggiornamento**: 21 novembre 2026
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
> * [ui.trgfn_preset_riga_contenitore](/dbzero/ui/funzioni/trgfn_preset_riga_contenitore) — scrive la lista della riga, dal preset
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

### ⭐ La colonna è della lista del preset

`lista_id` è la lista del preset, e la scrive il database
([trgfn_preset_riga_contenitore](/dbzero/ui/funzioni/trgfn_preset_riga_contenitore)): chi scrive la
riga non la passa, e un valore passato è sostituito. La leggono due vincoli composti:

* la riga appartiene a un preset di quella lista;
* la colonna nominata è una colonna di quella lista.

Una colonna di un'altra lista è quindi rifiutata alla scrittura, e il vincolo vale anche dall'altro
lato: la lista di una colonna che un preset nomina non cambia. Accanto restano le FK semplici verso
il preset e verso la colonna, che dicono l'esistenza; quelle composte dicono il legame.

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
* `db/pgtap/ui/test-ui-legami-preset-v1.sql` — la lista della riga scritta dal database, un valore
  passato sostituito, una colonna di un'altra lista rifiutata, la lista di una colonna nominata che
  non cambia.

---

### Note di migrazione

* 2026-11-01 — le righe spostano la data del preset, con un trigger condiviso con i widget dei
  preset di dashboard.
* 2026-11-08 — le due FK entrano fra le eccezioni ATTIVO come righe di composizione.
* 2026-11-20 — la composizione si giudica a fine transazione, sull'impronta: la sostituzione in
  blocco di una composizione uguale non sposta più la data.
* 2026-11-21 — nasce `lista_id`, scritta dal database, con i due vincoli composti verso il preset e
  la colonna della stessa lista. Le righe che citavano una colonna di un'altra lista sono state tolte;
  prima il resolver le abbinava per codice, e con un codice uguale prendeva ordine e larghezza di una
  colonna diversa.

---

{% include-markdown "signature-core.md" %}
