## 📘 Documentazione Concettuale – Tabella `pratiche.template_flussi`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.workflow_definizioni](/dbzero/pratiche/tabelle/workflow_definizioni) — l'edizione di workflow a cui appartiene lo step
> * [pratiche.tipi_prestazione](/dbzero/pratiche/tabelle/tipi_prestazione) — il tipo di pratica
> * [pratiche.flussi](/dbzero/pratiche/tabelle/flussi) — le istanze dello step nelle pratiche
> * [pratiche.handler_flussi](/dbzero/pratiche/tabelle/handler_flussi) · [pratiche.template_flussi_handler_eventi](/dbzero/pratiche/tabelle/template_flussi_handler_eventi) — gli automatismi lato server
> * [pratiche.azioni_ui](/dbzero/pratiche/tabelle/azioni_ui) — l'attività interattiva offerta dallo step
> * [pratiche.template_flussi_prerequisiti](/dbzero/pratiche/tabelle/template_flussi_prerequisiti) · [pratiche.template_flussi_canali](/dbzero/pratiche/tabelle/template_flussi_canali) · [pratiche.competenze_flussi](/dbzero/pratiche/tabelle/competenze_flussi) · [pratiche.formule_tempo](/dbzero/pratiche/tabelle/formule_tempo) · [pratiche.regole_generazione](/dbzero/pratiche/tabelle/regole_generazione) — i figli dello step
> * [pratiche.template_flussi_avanzamento_proiezione](/dbzero/pratiche/tabelle/template_flussi_avanzamento_proiezione) — con quale verdetto lo step avanza per proiezione
> * [config.esiti_flussi_pratiche](/dbzero/config/tabelle/esiti_flussi_pratiche) — il vocabolario di `esito_default`
>
> Approfondimento funzioni:
>
> * [pratiche.trgfn_template_flussi_default_definizione](/dbzero/pratiche/funzioni/trgfn_template_flussi_default_definizione) — aggancia lo step al preset del tipo
> * [pratiche.trgfn_template_flussi_guard_modalita_esito](/dbzero/pratiche/funzioni/trgfn_template_flussi_guard_modalita_esito) — le regole dell'asse esito
> * [pratiche.trgfn_template_flussi_guard_immutabile](/dbzero/pratiche/funzioni/trgfn_template_flussi_guard_immutabile) · [pratiche.trgfn_template_flussi_figli_guard_immutabile](/dbzero/pratiche/funzioni/trgfn_template_flussi_figli_guard_immutabile) — la struttura di un'edizione emessa non si tocca
> * [pratiche.fn_check_ripetibilita_flusso](/dbzero/pratiche/funzioni/fn_check_ripetibilita_flusso) — la ripetibilità
> * [pratiche.fn_check_chiusura_pratica](/dbzero/pratiche/funzioni/fn_check_chiusura_pratica) — gli obbligatori che bloccano la chiusura
> * [pratiche.trgfn_flussi_autochiusura_pratica](/dbzero/pratiche/funzioni/trgfn_flussi_autochiusura_pratica) — la chiusura guidata dal workflow
> * [pratiche.fn_reconcile_sorgente](/dbzero/pratiche/funzioni/fn_reconcile_sorgente) — l'avanzamento su esito proiettato

---

### 🎯 Scopo Principale

La tabella `pratiche.template_flussi` descrive gli step di workflow di un'edizione: per ciascuno
l'ordine, l'obbligatorietà, la direzione, la ripetibilità, come ottiene l'esito, e gli automatismi o le
attività interattive che offre. I flussi di una pratica nascono da questi template.

---

### Lo step appartiene a un'edizione

Ogni template appartiene a un'edizione di workflow (`definizione_id`): l'insieme dei template di
un'edizione è la definizione. La chiave esterna verso l'edizione è composita col tipo di prestazione,
quindi lo step e la sua edizione hanno lo stesso tipo per costruzione. Senza un valore esplicito,
l'inserimento si aggancia al preset del tipo.

* Il `codice` è unico dentro l'edizione, ed è il contratto stabile con cui i building block del dominio
  riconoscono lo step: edizioni diverse dello stesso tipo hanno gli stessi codici. Si scrive in
  maiuscolo.
* Al più un template per edizione chiude la pratica.

⛔ **La struttura di un'edizione emessa non si tocca.** Se l'edizione è di un emittente ed è pubblicata
o ritirata, template e figli non si inseriscono né si modificano (resta modificabile la sola
`descrizione`); la cancellazione è vietata solo su un'edizione pubblicata, perché una ritirata resta
cancellabile per pulizia. Il preset e le bozze restano liberi.

---

### Le colonne che reggono il comportamento

| Colonna | Regola |
| --- | --- |
| `sequenza` | L'ordine di esecuzione nel workflow |
| `obbligatorio` | Il flusso va completato per chiudere la pratica, finché è ancora percorribile: il ramo morto di un bivio non blocca |
| `chiude_pratica` | Il «flusso di chiusura»: al suo completamento la pratica passa a `CHIUSA`. Implica `obbligatorio`, e si completa solo a percorso obbligatorio concluso |
| `direzione` | `ENTRATA` (dall'esterno al gestionale), `USCITA` (dal gestionale all'esterno), `INTERNA` (predefinita) |
| `ripetibilita` | `MAI` (una sola istanza non annullata), `SE_NON_POSITIVO` (predefinita: una nuova istanza solo se l'ultima è completata con esito diverso da positivo, e un'istanza aperta blocca), `SEMPRE` |
| `modalita_esito` | `MANUALE` (predefinita: l'operatore sceglie l'esito), `AUTOMATICO` (si avvia e si completa con `esito_default`, solo per step interni), `CONTESTUALE` (`esito_default` proposto e confermato in un'azione sola), `DOMINIO` (l'esito lo calcola un building block di dominio, e al completamento sono ammessi solo esiti di ramo, non verdetti) |
| `esito_default` | Obbligatorio per `AUTOMATICO` e `CONTESTUALE`, e dev'essere un verdetto; vietato con `DOMINIO` |
| `handler_id`, `handler_params` | L'handler che esegue lo step all'avvio, con i suoi parametri; vuoto = step manuale. Le azioni sugli altri eventi stanno in `template_flussi_handler_eventi` |
| `azione_ui_id` | L'attività interattiva che il frontend offre nello step (per esempio aprire il preventivo dentro la pratica) |
| `attende_sorgente_tipo_id` | Il tipo di documento il cui verdetto proiettato fa avanzare lo step; vuoto = lo step non avanza per proiezione |
| `obsoleto_dal` | Lo step non si offre più da quella data |

`handler_id` e `azione_ui_id` sono assi ortogonali: il primo automatizza lato server, il secondo lancia
un'attività lato client. Uno step può avere l'uno, l'altro, entrambi o nessuno.

---

### La chiusura guidata dal workflow

La pratica si chiude da sé al completamento dei flussi, non con un'azione manuale:

* se l'edizione ha un flusso di chiusura, la pratica si chiude al completamento di quello;
* altrimenti, se ha almeno un obbligatorio, si chiude quando non ne restano di bloccanti e nessun
  flusso è aperto;
* un'edizione senza obbligatori e senza flusso di chiusura non ha un percorso di chiusura automatico.

---

### L'avanzamento su esito proiettato

Uno step può dichiarare `attende_sorgente_tipo_id` e, con il collegamento in
`template_flussi_avanzamento_proiezione`, si completa da solo quando il documento proietta il verdetto
atteso. Senza quel collegamento lo step non avanza in automatico. È ammesso solo su step che non sono
`DOMINIO`, e uno step che avanza per proiezione non ha un handler di completamento.

---

### Disattivazione e dipendenze

Un template attivo vuole il tipo, l'handler, l'azione interattiva e il tipo di documento atteso attivi.
Un template non si spegne finché ha flussi o figli attivi (prerequisiti, canali, collegamenti agli
handler, competenze, formule del tempo, regole di generazione, collegamenti di proiezione). Le
modifiche sono storicizzate.

---

### Codici errore

* `E_TEMPLATE_DEFINIZIONE_CONGELATA` — modifica della struttura di un'edizione emessa.
* `E_TEMPLATE_FLUSSO_ESITO_DEFAULT_OBBLIGATORIO`, `E_TEMPLATE_FLUSSO_ESITO_DEFAULT_NON_VERDETTO`,
  `E_TEMPLATE_FLUSSO_DOMINIO_ESITO_DEFAULT_VIETATO`, `E_TEMPLATE_FLUSSO_AUTOMATICO_SOLO_INTERNA` — le
  regole dell'asse esito.

Gli errori a runtime sui flussi (ripetibilità, chiusura prematura, classe dell'esito) li sollevano i
guard su `pratiche.flussi` e `pratiche.pratiche`.

---

### Test

* `pratiche/test-esito-configurabile-template-flussi` — l'asse esito.
* `pratiche/test-ripetibilita-flussi` — la ripetibilità.
* `pratiche/test-autochiusura-pratica`, `pratiche/test-chiusura-nessun-lavoro-pendente` — la chiusura
  guidata dal workflow.
* `pratiche/test-definizione-ritirata-edit-freeze` — la struttura di un'edizione emessa.
* `pratiche/test-azioni-ui-template-flussi` — l'attività interattiva.

---

### Note di migrazione

* 2026-07-03 — con le edizioni versionate, l'unicità del codice e del flusso di chiusura passa dal
  tipo di prestazione all'edizione: un tipo può avere più edizioni con gli stessi codici.

---

{% include-markdown "signature-core.md" %}
