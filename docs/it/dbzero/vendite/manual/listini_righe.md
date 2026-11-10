## 📘 Documentazione Concettuale – Tabella `vendite.listini_righe`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.listini_versioni](/dbzero/vendite/tabelle/listini_versioni)  
> • [catalogo.articoli](/dbzero/catalogo/tabelle/articoli)  
> • [catalogo.unita_misura](/dbzero/catalogo/tabelle/unita_misura)  
>
> **Ultimo aggiornamento**: 10 novembre 2026

### 🎯 Scopo Principale
La tabella `vendite.listini_righe` contiene i prezzi elementari per articolo/UOM,
eventualmente specializzati per contesto (BA, utility, emittente fiscale).

Rappresenta il livello usato dal resolver prezzi per selezionare il match piu`
specifico rispetto al contesto operativo.

---

### Regole principali

* FK obbligatorie su `listino_versione_id`, `articolo_id`, `uom_id`;
* dimensioni opzionali:
  * `billing_account_id`
  * `utility_id`
  * `emittente_soggetto_ruolo_id`
* `prezzo >= 0`;
* precisione prezzo operativa v1: `numeric(22,10)` nel percorso listino -> commessa -> attivita_fatturabili;
* una sola riga attiva per la stessa combinazione dimensionale
  (`uq_listini_righe_key_attiva` con coalesce delle dimensioni opzionali);
* ⭐ **articolo, unità di misura e versione sono l'identità della riga** (rev 2026-10-15,
  decisione di Tid): dopo l'inserimento non cambiano. Lo tiene il blocco di colonna
  (`dbops.automation_lock_columns`, codice `E_LISTINO_RIGA_IDENTITA_IMMUTABILE`); per cambiarli
  si elimina la riga e se ne crea una nuova. Il backend lo faceva già (non li accetta in
  modifica), il database no. È l'altro lato della regola che
  [vendite.trgfn_attivita_guard_listino_riga](/dbzero/vendite/manual/trgfn_attivita_guard_listino_riga)
  tiene sulle righe di commessa e sulle attività fatturabili che citano la riga: se la riga di
  listino cambiasse articolo, chi la cita resterebbe incoerente.
* **`periodicita`** (FK su `config.periodicita`, nullable): su una quota fissa è il ritmo con cui
  ogni contratto del listino la paga; altrove la proposta all'adesione. Un **kit** non ha una riga
  qui: la sua periodicità sta in [vendite.listini_kit](/dbzero/vendite/manual/listini_kit), e la
  sede che le legge tutte e due è
  [vendite.fn_listino_periodicita_articolo](/dbzero/vendite/manual/fn_listino_periodicita_articolo).
* ⭐ **Una quota fissa a canone non resta senza periodicità fuori dalla bozza** (rev 2026-10-31,
  decisione di Tid): toglierla su una versione attiva è rifiutato da
  [vendite.trgfn_listini_righe_guard_periodicita_quota_fissa](/dbzero/vendite/funzioni/trgfn_listini_righe_guard_periodicita_quota_fissa)
  (`E_LISTINO_QUOTA_FISSA_PERIODICITA_FERMA`, sul campo). Cambiarla con un'altra resta una
  rettifica, come il prezzo. È l'altra metà del controllo all'attivazione
  ([script.fn_check_versione_listino_attivabile](/dbzero/script/manual/fn_check_versione_listino_attivabile),
  motivo 3): senza, la quota la perdeva dopo.
* ⭐ **L'unità di un prezzo si converte per tutto il periodo della versione** (rev 2026-11-10,
  decisione di Tid): in ogni giorno da `valido_dal` a `valido_al` della versione (senza fine se
  vuota), l'unità della riga deve avere un fattore per l'articolo, cioè la base, una mappatura o una
  conversione generale in vigore quel giorno. Lo controlla
  [vendite.trgfn_listini_righe_guard_uom_periodo](/dbzero/vendite/funzioni/trgfn_listini_righe_guard_uom_periodo)
  su un prezzo nuovo e su uno riacceso (`E_LISTINO_UOM_NON_CONVERTIBILE`, sul campo `uom_id`, col
  primo giorno scoperto). La regola si rompe anche da altri due lati, e lì è presidiata: il periodo
  della versione che si allunga
  ([vendite.trgfn_listini_versioni_guard_uom_periodo](/dbzero/vendite/funzioni/trgfn_listini_versioni_guard_uom_periodo))
  e il catalogo che cambia sotto una versione attiva
  ([catalogo.trgfn_uom_guard_listini_attivi](/dbzero/catalogo/funzioni/trgfn_uom_guard_listini_attivi)).
  Una bozza rotta dal catalogo non si attiva
  ([script.fn_check_versione_listino_attivabile](/dbzero/script/manual/fn_check_versione_listino_attivabile),
  motivo 4).

---

### Utilizzo previsto

* pricing puntuale per contesto utility/commercio;
* supporto fallback da combinazioni specifiche a combinazioni generiche;
* mantenimento precisione alta a monte; riduzione a 6 decimali demandata al layer `fatture_righe`;
* base tecnica per policy anti-ambiguita` del resolver.

---

{% include-markdown "signature-core.md" %}
