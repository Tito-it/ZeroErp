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
🎯 Scopo Principale

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
