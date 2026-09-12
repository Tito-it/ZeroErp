## 📘 Documentazione Concettuale – View `dbops.vw_processi_dominio_senza_emittente`

> 👀 **Vedi anche**
>
Approfondimenti tabelle:
>
[dbops.processi](/dbzero/dbops/manual/processi)
>
[dbops.processi_bersagli](/dbzero/dbops/manual/processi_bersagli)

---
### 🎯 Scopo Principale
(latest review 04-09-2026)

Elenca le tabelle toccate da un processo di **dominio** per cui **non si sa
arrivare all'emittente**.

> ⚠️ **Deve restare vuota.** Ogni riga è la stessa domanda: *questa riga di chi
> è, e perché nessuno lo ha scritto?*

---

### ⭐ Cattura DUE guasti diversi, e il secondo è il pericoloso

| | Che cosa manca |
| --- | --- |
| **percorso assente** | nessuno ha dichiarato come si risale all'emittente |
| **percorso rotto** | il percorso è dichiarato, ma la colonna **non esiste più** |

⚠️ **Il secondo è peggio del primo**, e va detto perché non è intuitivo: un
percorso assente si vede a occhio nudo leggendo la tabella; un percorso verso
una colonna cancellata **sembra a posto**. Chi legge il censimento vede un
campo pieno e passa oltre.

⇒ La vista non si accontenta del campo compilato: va a chiedere a
`information_schema` se quella colonna esiste davvero. È la differenza fra un
presidio e un modulo da compilare.

---

### Che cosa succede se la si ignora

Il processo gira, la row level security non ha niente su cui filtrare, e il
lavoro **tocca righe di aziende diverse** senza che nessun errore lo dica. Non
è un guasto rumoroso: è una fattura emessa per l'azienda sbagliata, o un
documento che non viene emesso affatto.

---

### Come si svuota

Una riga in [processi_bersagli](/dbzero/dbops/manual/processi_bersagli) con la
via e la colonna giuste — oppure, se il percorso davvero non c'è, **la colonna
va aggiunta alla tabella di dominio**: è il caso di `config.email_outbox`, che
questo cantiere ha fatto emergere e che non progetta.

---

### Esempio d'uso

```sql
SELECT * FROM dbops.vw_processi_dominio_senza_emittente;
```

Origine: `docs/it/dev/work-done/brief-db-processi-automatici-identita-e-perimetro.md` §8.

---

{% include-markdown "signature-core.md" %}
