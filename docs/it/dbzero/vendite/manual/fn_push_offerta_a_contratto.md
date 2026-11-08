## 📘 Documentazione Concettuale – Funzione `vendite.fn_push_offerta_a_contratto`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.offerte_commerciali](/dbzero/vendite/tabelle/offerte_commerciali) — l'offerta accettata, il documento d'origine
> * [vendite.offerte_commerciali_eccezioni](/dbzero/vendite/tabelle/offerte_commerciali_eccezioni) — le eccezioni, che diventano righe del contratto
> * [vendite.offerte_commerciali_eccezioni_componenti](/dbzero/vendite/tabelle/offerte_commerciali_eccezioni_componenti) — i componenti delle eccezioni
> * [vendite.offerte_commerciali_utilities](/dbzero/vendite/tabelle/offerte_commerciali_utilities) — le utility negoziate
> * [vendite.contratti](/dbzero/vendite/tabelle/contratti) — il contratto generato, con la provenienza dall'offerta
> * [vendite.contratti_righe](/dbzero/vendite/tabelle/contratti_righe) — le righe, con la provenienza dall'eccezione
> * [vendite.contratti_righe_componenti](/dbzero/vendite/tabelle/contratti_righe_componenti) — i componenti copiati
> * [vendite.contratti_utilities](/dbzero/vendite/tabelle/contratti_utilities) — le utility del contratto
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — il catalogo dei tipi di documento d'origine
> * [pratiche.pratiche_sorgenti](/dbzero/pratiche/tabelle/pratiche_sorgenti) — l'aggancio facoltativo alla pratica
>
> Approfondimento funzioni:
>
> * [vendite.fn_offerta_documenti_vivi](/dbzero/vendite/funzioni/fn_offerta_documenti_vivi) — i documenti vivi generati da un'offerta, sede unica del controllo
> * [script.fn_sorgente_provenienza](/dbzero/script/funzioni/fn_sorgente_provenienza) — la provenienza da scrivere, con la chiave del tipo
> * [vendite.fn_genera_ordine_da_offerta](/dbzero/vendite/funzioni/fn_genera_ordine_da_offerta) — il verbo gemello, che genera l'ordine
> * [vendite.fn_contratto_sovrapposto](/dbzero/vendite/funzioni/fn_contratto_sovrapposto) — il rilevamento della sovrapposizione
> * [vendite.fn_chiudi_contratto_per_successione](/dbzero/vendite/funzioni/fn_chiudi_contratto_per_successione) — la chiusura per successione
> * [vendite.trgfn_contratti_snapshot_precontrattuali](/dbzero/vendite/funzioni/trgfn_contratti_snapshot_precontrattuali) — il trigger che crea le utility dai precontrattuali
> * [vendite.fn_crea_revisione_offerta](/dbzero/vendite/funzioni/fn_crea_revisione_offerta) — la revisione dell'offerta
> * [script.fn_available_actions_offerta](/dbzero/script/funzioni/fn_available_actions_offerta) — le azioni disponibili sull'offerta
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza

---

### 🎯 Scopo Principale

`vendite.fn_push_offerta_a_contratto` genera un **contratto in bozza** (DRAFT) da un'offerta commerciale **accettata**, copiando eccezioni, componenti e utility, e scrive sul contratto e sulle sue righe la provenienza dall'offerta.

Il push è **idempotente per costruzione**: una seconda invocazione sulla stessa offerta,
finché il contratto generato è vivo, fallisce con un errore semantico senza creare duplicati.

È anche **consumatore del meccanismo generico di successione dei contratti**: se per la
stessa combinazione (billing account, istanza utility, utility, ambito, periodo) esiste già un
contratto attivo sovrapposto, il push non lascia trapelare l'errore grezzo del vincolo di
esclusione, ma lo gestisce in modo esplicito (vedi «Successione su sovrapposizione»). La logica
di rilevamento e chiusura vive nelle funzioni di dominio `fn_contratto_sovrapposto` e
`fn_chiudi_contratto_per_successione`; il push aggiunge solo lock, instradamento e rete di
sicurezza.

---

### Un'offerta genera al più un documento vivo

* **Stato ammesso**: solo un'offerta in uno stato di accettazione (`ACCETTATA`, colonna
  `accettazione` del vocabolario). Ogni altro stato produce `E_OFFERTA_PUSH_STATO_NON_AMMESSO`.
* **Contratto e ordine sono alternativi**: un'offerta genera al più **un** documento vivo, o un
  contratto o un ordine. Il push legge i documenti vivi dell'offerta da
  `vendite.fn_offerta_documenti_vivi`, la sede unica del controllo, e si ferma con
  `E_OFFERTA_CONTRATTO_GIA_GENERATO` se c'è già un contratto, con
  `E_OFFERTA_ORDINE_GIA_GENERATO` se c'è già un ordine; l'errore porta il bersaglio, il
  documento già generato.
* **Un documento annullato non consuma l'offerta**: conserva la provenienza, ma non conta fra i
  vivi; dopo l'annullo l'offerta può generare un nuovo documento.
* **La rete strutturale**: gli indici unici `uq_contratti_sorgente_offerta` (su
  `vendite.contratti`) e `uq_ordini_v_sorgente_offerta` (su `vendite.ordini`) rendono
  impossibile un secondo documento vivo dello **stesso** tipo dalla stessa offerta. Non esiste
  un vincolo strutturale incrociato fra contratti e ordini: la gara fra i due tipi la chiude il
  controllo dei verbi, non un indice. Il controllo speculare lato ordine vive nel verbo gemello
  `vendite.fn_genera_ordine_da_offerta`, ed è lo specchio, in scrittura, delle azioni
  disponibili sull'offerta (`script.fn_available_actions_offerta`).

---

### La provenienza: sul contratto e su ogni riga

* **Il contratto** dichiara di nascere dall'offerta: tipo `OFFERTA_COMMERCIALE` e la chiave
  dell'offerta, nella colonna che il tipo vuole (l'offerta si riconosce per uid). La coppia di
  colonne la dà `script.fn_sorgente_provenienza`, letta una volta per testata e righe: il push
  non la compone da sé.
* **Ogni riga del contratto** porta la stessa provenienza, e in più la riga d'origine: l'eccezione
  dell'offerta da cui è stata copiata.
* La provenienza è l'unico legame fra contratto e offerta: è lei che il controllo dei documenti
  vivi, la lineage e le liste leggono.

---

### Che cosa copia

* **Testata**: billing account, istanza utility, utility, listino e sua versione, variazione
  globale, validità (dalla validità dell'offerta), `meta`, ed emittente fiscale 1:1
  dall'offerta. Il trigger di default dell'emittente salta (il campo è già valorizzato) e il
  guard di coerenza fra billing account ed emittente lo valida.
* **Eccezioni → righe del contratto**, una per eccezione nell'ordine dell'id, ognuna coi suoi
  **componenti**. Lo stato di approvazione del prezzo e la pratica di approvazione viaggiano
  **1:1**, sulle righe e sui componenti: l'approvazione ottenuta in offerta arriva al contratto
  senza riapprovazione. La copia una eccezione alla volta tiene il legame fra eccezione e riga
  senza dover correlare due insiemi.
* **Utility**: il trigger dei precontrattuali, all'inserimento del contratto, può aver già creato
  le utility del contratto; il push le **sovrascrive** coi dati negoziati dell'offerta, che hanno
  precedenza sul precontrattuale generico.
* **Indirizzi**: quelli ammessi per il contratto.
* **Il contratto nasce in bozza**: il passaggio ad attivo avviene separatamente.
* **Aggancio alla pratica** (facoltativo): se si passa una pratica, il contratto generato entra
  fra le sorgenti della pratica come `CONTRATTO` con ruolo `COLLEGATO`. La registrazione
  dell'evento nel giornale della pratica è del livello applicativo.

---

### Successione su sovrapposizione

Dopo i controlli e prima di inserire il contratto, il push:

1. **Serializza sulla combinazione** — un lock transazionale su una chiave derivata da billing
   account, istanza utility, utility e ambito: due operatori non possono creare contratti
   sovrapposti nello stesso istante, senza bloccare l'intera tabella.
2. **Rileva** la sovrapposizione con `fn_contratto_sovrapposto`, sull'ambito `COMMODITY`.
   ⚠️ Il push non valorizza l'ambito, quindi il nuovo contratto prende il default
   `COMMODITY`: se un giorno lo valorizzasse, va allineato anche il rilevamento.
3. **Instrada**:
   * **nessuna sovrapposizione**: crea il contratto;
   * **sovrapposizione senza conferma** (`p_chiudi_contratto_esistente` falso, il default):
     solleva `E_CONTRATTO_OVERLAP_ESISTENTE` col numero del contratto in conflitto, e non crea
     niente. È il caso che il frontend usa per mostrare il conflitto e chiedere conferma;
   * **sovrapposizione con conferma**: chiude il vecchio contratto per successione (lo accorcia
     al giorno prima della nuova validità), poi crea il nuovo.
4. **Rete di sicurezza** — se il vincolo di esclusione scattasse comunque (gara sfuggita al
   lock, sovrapposizioni multiple), l'errore grezzo è ritradotto in
   `E_CONTRATTO_OVERLAP_ESISTENTE`: il client non vede mai l'errore del vincolo.

> La successione **accorcia** il contratto preesistente, non lo annulla, e non ne cambia lo
> stato: la cessazione da attivo a cessato la fa il job notturno `chiusura_scadenze_daily`.

```text
fn_push_offerta_a_contratto
  ├─ controlli: stato di accettazione, documenti vivi dell'offerta
  ├─ lock sulla combinazione → rilevamento sovrapposizione → instradamento
  │    └─ [con conferma] chiusura per successione del vecchio contratto
  ├─ contratto DRAFT con la provenienza dall'offerta
  │    ├─ default emittente (salta), guard emittente/billing account, numerazione, normalizzazione
  │    └─ dopo l'inserimento: utility dai precontrattuali
  ├─ per ogni eccezione: riga con la provenienza dall'eccezione, poi i suoi componenti
  ├─ utility dell'offerta, sopra quelle dei precontrattuali
  └─ [con pratica] aggancio del contratto alla pratica
```

---

### Codici errore

| Codice | Quando |
| --- | --- |
| `E_PARAMETRO_INVALIDO` | l'offerta non è indicata o l'id non è positivo |
| `E_OFFERTA_NON_TROVATA` | l'offerta non c'è, o è fuori perimetro |
| `E_OFFERTA_PUSH_STATO_NON_AMMESSO` | l'offerta non è in uno stato di accettazione |
| `E_OFFERTA_CONTRATTO_GIA_GENERATO` | l'offerta ha già un contratto vivo |
| `E_OFFERTA_ORDINE_GIA_GENERATO` | l'offerta ha già un ordine vivo |
| `E_CONTRATTO_OVERLAP_ESISTENTE` | c'è un contratto attivo sovrapposto e non si è chiesta la successione, oppure un conflitto residuo intercettato dalla rete di sicurezza |
| `E_CONFIG_MANCANTE` | manca lo stato DRAFT dei contratti, o un tipo atteso in `config.sorgenti` |

---

### Note di migrazione

* 2026-05-26 — la copia include i componenti delle eccezioni e l'emittente fiscale 1:1.
* 2026-05-31 — il push diventa consumatore della successione dei contratti su sovrapposizione.
* 2026-06-01 — lo stato di approvazione del prezzo viaggia 1:1 anche sulle righe.
* 2026-06-08 — mutua esclusività fra contratto e ordine generati dalla stessa offerta.
* 2026-10-11 — il controllo conta solo i documenti vivi: un annullato non consuma l'offerta.
* 2026-11-06 — ritirata la colonna `vendite.contratti.offerta_id` con la sua unicità: la
  provenienza del contratto sta in `sorgente_*` (chiave dal tipo, via
  `script.fn_sorgente_provenienza`), l'unicità è `uq_contratti_sorgente_offerta` sui soli
  contratti vivi, e le righe del contratto dichiarano l'eccezione d'origine
  (brief-db-sorgente-documento-e-riga).

---

{% include-markdown "signature-core.md" %}
