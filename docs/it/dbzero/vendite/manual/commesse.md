## 📘 Documentazione Concettuale – Tabella `vendite.commesse`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.stati_commessa](/dbzero/vendite/tabelle/stati_commessa)  
> • [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)  
> • [vendite.commesse_sorgenti](/dbzero/vendite/tabelle/commesse_sorgenti)  
>
**Approfondimento funzioni:**
>
• [vendite.fn_get_or_create_commessa](/dbzero/vendite/funzioni/fn_get_or_create_commessa)  
> • [vendite.fn_get_commessa_stato](/dbzero/vendite/funzioni/fn_get_commessa_stato)  
>
### 🎯 Scopo Principale
(latest review 26-02-2026)  
`vendite.commesse` e` la testata di governo del ciclo operativo
`sorgente -> commessa -> commesse_attivita -> attivita_fatturabili`.

Contiene le dimensioni che identificano la commessa (BA/utility/emittente, policy, priorita`, competenza) e lo stato lifecycle tramite FK `stato_commessa_id`.

---

### Regole principali

* `codice` univoco.
* Stato gestito con FK verso `vendite.stati_commessa`:
  * colonna `stato_commessa_id` (default `1 = BOZZA`)
  * trigger che impedisce uso di stati non attivi.
* Coerenza dominio:
  * `tipo_commessa` su set ammesso
  * `policy_fatturazione` su set ammesso
  * `priorita_operativa` su set ammesso
  * range `competenza_dal/competenza_al` coerente.
* Non e` piu` presente la colonna testuale `stato_commessa`: il codice stato deriva dalla lookup.

---

### Utilizzo previsto

* punto di aggregazione business della pipeline vendite;
* contenitore delle righe emettibili (`commesse_attivita`);
* perimetro di matching/riuso per `fn_get_or_create_commessa`.

---

{% include-markdown "signature-core.md" %}

---

### 🔄 rev 2026-09-02 — la commessa dice da quale registro viene, e di che anno

Due colonne nuove: **il registro** che le ha dato il codice e **l'anno** del
contatore.

⭐ **Non sono un doppione del codice.** Il codice —
`CMM-<sigla azienda>-<anno>-<nove cifre>` — quelle due informazioni le porta già
*dentro*, ma dentro una stringa: per sapere «quali commesse ha numerato il
registro di quest'azienda nel 2026» bisognava spezzare il testo. Ora sono due
campi, e si chiedono.

⛔ **E c'era un motivo più serio della comodità.** Che sigla e anno stessero nella
stringa era una **convenzione di chi la compone**: giusta, e non verificata da
niente. Il giorno che al contatore si fosse aggiunta una dimensione — un periodo
diverso dall'anno, per dire — senza aggiornare anche la composizione, il codice
avrebbe ricominciato a ripetersi al primo cambio di periodo, e la commessa
sarebbe stata rifiutata per «codice duplicato» nel mezzo di un'elaborazione che
con la numerazione non c'entra. Adesso un controllo automatico confronta la
stringa con le due colonne.

⚠️ **L'identità non è cambiata**: unico resta il `codice`, e resta unico **da
solo**. È una regola più stretta di quella degli altri quattro documenti, che
sono unici *per registro*: il codice della commessa porta la sigla dell'azienda,
quindi non si ripete mai fra aziende diverse.

⚠️ **Le due colonne possono essere vuote**, come sui documenti fratelli: le righe
create dai test non passano dalla funzione che le riempie, e pretendere il
contrario avrebbe fatto fallire una decina di file di prova senza aggiungere
nessuna garanzia.

