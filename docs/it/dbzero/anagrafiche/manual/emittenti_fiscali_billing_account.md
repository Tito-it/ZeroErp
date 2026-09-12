## 📘 Documentazione Concettuale – Tabella `anagrafiche.emittenti_fiscali_billing_account`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**    
>
• [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)    
> • [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)    
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)    
>
### 🎯 Scopo Principale
(latest review 08-04-2026)
La tabella `anagrafiche.emittenti_fiscali_billing_account` definisce l’associazione tra **billing account**
e **emittente fiscale** (ruolo), garantendo che ogni documento abbia un emittente coerente e deterministico.

Il modello prevede un **emittente di default globale** che, dopo il refactor del 2026-04-08, agisce come
**rete di sicurezza** per i casi residui (seed/bootstrap, scenari "0 emittenti"), mentre il caso normale
prevede che ogni BA venga **auto‑collegato** all'emittente dell'operatore che lo crea, tramite il trigger
[`trgfn_billing_account_link_ef`](/dbzero/anagrafiche/funzioni/trgfn_billing_account_link_ef) sulla tabella
`billing_account`. Vedi [refactor operatore ↔ emittente](/dev/work-done/refactor-operatore-emittenti).

---

### Regole principali

* **Unicita` per billing account**: una sola riga per `billing_account_id`.
* **Default globale**:
  * `is_default = true` ammesso **una sola volta**.
  * la riga di default ha `billing_account_id` **NULL**.
* **Coerenza** (la regola vive in
  [`script.fn_get_ba_emittente_sr_id`](/dbzero/script/manual/fn_get_ba_emittente_sr_id),
  e da nessun'altra parte):
  * se esiste una riga specifica per BA, essa prevale su tutto.
  * in assenza di mapping, **in sessione**, il BA è dell'**operatore che sta
    agendo** (dal 2026-09-13, D13): è l'istante fra l'`INSERT` del BA e il
    trigger `z90` che scrive il legame, e la riserva dice in anticipo ciò che il
    trigger sta per scrivere — senza, l'`INSERT … RETURNING` di un operatore di
    un emittente non di default moriva sotto la RLS.
  * in assenza di mapping e **senza sessione** (batch, manutenzione), si usa il
    default.

---

### ⛔ Quando questo legame si può ancora cambiare

> Aggiunto il 2026-08-26 — cantiere «un billing account può cambiare emittente?».

Questa riga sembra un'associazione qualunque, e per molto tempo è stata trattata
così. **Non lo è.**

Una fattura **congela** chi l'ha emessa e non lo cambia mai. Spostare il cliente
su un altro emittente quindi non riscrive i documenti già emessi: **li lascia
orfani**. Da quel momento chi li ha emessi continua a vedere i documenti e
smette di vedere il cliente a cui si riferiscono — e non compare nessun errore,
perché nessun dato è sbagliato: è il perimetro che si è spezzato.

⇒ **La regola non è «non si può», è «fino a quando»:**

| Il cliente ha… | Cambiare emittente |
| --- | --- |
| nessuna fattura e nessuna commessa | ✅ **si può** — è la finestra di correzione |
| almeno una fattura o una commessa | ⛔ **respinto**, con il conteggio nel messaggio |

⭐ La finestra esiste perché serve davvero: il legame **nasce da solo** con
l'emittente dell'operatore che sta creando il cliente, quindi un cliente può
*nascere sbagliato*. Se fosse immutabile, quell'errore non si correggerebbe più.

⚠️ **E il movimento non è un `UPDATE`**: si fa cancellando l'aggancio e
ricreandolo. Il primo passo, da solo, è già uno spostamento — il cliente ricade
sull'emittente generale — ed è presidiato anche quello.

**E se il cliente è passato davvero all'altro emittente?** Non si sposta: si apre
presso il nuovo emittente una **fornitura nuova**. I documenti già emessi restano
con chi li ha emessi.

Presidio:
[`anagrafiche.trgfn_efba_guard_storia_emittente`](/dbzero/anagrafiche/manual/trgfn_efba_guard_storia_emittente)
· conteggio:
[`fn_get_storia_emittente_ba`](/dbzero/anagrafiche/manual/fn_get_storia_emittente_ba)
· raggio N:
[`fn_guard_ba_gestore_globale_storia`](/dbzero/anagrafiche/manual/fn_guard_ba_gestore_globale_storia)

---

### Collocazione nel processo di fatturazione

1. Durante la generazione delle fatture, l’emittente fiscale viene risolto tramite questa tabella.
2. Se non esiste un mapping specifico per il BA, vale la riserva: l'emittente di chi agisce se c'è una sessione, altrimenti il default globale.
3. Questo garantisce coerenza e riduce la configurazione manuale quando l’emittente e` unico.

---

### Best practice operative

* Inserire sempre un **emittente di default** appena si abilita il modulo fatturazione (rete di sicurezza per BA non auto‑collegati).
* Dopo il refactor 2026-04-08, i mapping specifici per BA vengono **creati automaticamente** alla creazione del BA dal trigger di auto‑link, basandosi sull'emittente dell'operatore corrente. Non serve più popolarli manualmente.
* ⚠️ **Verificare l'emittente su cui si sta lavorando PRIMA di creare un cliente**: il legame nasce da lì, e dopo il primo lavoro non si sposta più (vedi la sezione sopra).
* L'admin globale **non può** creare BA quando esistono emittenti fiscali attivi (vincolo a livello DB tramite [`trgfn_billing_account_guard_admin_globale`](/dbzero/anagrafiche/funzioni/trgfn_billing_account_guard_admin_globale)). Per creare un BA, occorre operare come operatore o admin di emittente.

---

{% include-markdown "signature-core.md" %}
