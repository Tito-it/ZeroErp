## 📘 Documentazione Concettuale – Procedura: `maintenance.proc_sync_storico_set_storicizza`

> 👀 **Vedi anche:**
>
Approfondimento tabelle:
>
[config.storico_set_storicizza](/dbzero/config/tabelle/storico_set_storicizza)
>
Approfondimento funzioni:
>
[maintenance.proc_apply_storicizza_defaults](/dbzero/maintenance/manual/proc_apply_storicizza_defaults)

---
### 🎯 Scopo Principale
(latest review 05-09-2026)

Tiene `config.storico_set_storicizza` allineato alla sua **derivazione**: le
tabelle ordinarie che hanno la colonna `storicizza` con `DEFAULT true`.

Una sincronizzazione ha **due metà**: aggiunge ciò che la derivazione produce, e
**toglie** ciò che non ha più un referente.

---

### ⛔ Fino al 5 settembre 2026 ne aveva una sola

La procedura sapeva solo **aggiungere** (`INSERT … ON CONFLICT DO NOTHING`). Il
set si popolava da solo e **non si potava da solo**: ogni tabella ritirata
lasciava dietro di sé una riga che puntava a niente.

⭐ **Non è rimasto un difetto teorico.** Tre righe morte hanno fatto fallire
`apply_storicizza_weekly` **ogni settimana per sei mesi**, e nessuno se n'è
accorto — il job muore, e il verbale del fallimento muore con lui.

---

### ⛔ Si pota una cosa sola, e la distinzione è il cuore

Una riga può smettere di essere prodotta dalla derivazione per **tre** motivi, e
solo il primo giustifica la potatura:

| Caso | Che cosa succede | Perché |
| --- | --- | --- |
| il nome **non risolve** a nessun oggetto, riga derivata | ✅ si pota | non può essere vera in nessun senso |
| il nome non risolve, riga **manuale** | ⛔ non si tocca | è una **decisione** di una persona: se perde il bersaglio va detto a qualcuno, non cancellato di nascosto |
| la tabella **c'è** ma ha perso il `DEFAULT` | ⛔ non si pota | è il caso **transitorio** che `apply_storicizza_weekly` ripara |

> ⚠️ Il terzo è quello che si sbaglierebbe più facilmente. Il `DEFAULT` lo rimette
> proprio l'altra metà del meccanismo, che gira su un'altra schedulazione: potare
> lì vorrebbe dire **spegnere la storicizzazione di una tabella viva** perché un
> giro non è ancora passato. Le due metà si combatterebbero.

---

### ⚠️ Il nome si scrive schema-qualificato, ed è una correzione

La forma precedente salvava `attrelid::regclass::text`, che **omette lo schema**
se quello schema è nel `search_path` di chi lancia il job.

⛔ Una chiave che cambia con il `search_path` del chiamante è una chiave che un
giorno non ritrova la propria riga — e la potatura, che risolve il nome, sarebbe
la prima a inciampare.

---

### Che cosa NON fa

* Non tocca lo schema delle tabelle: mette a posto solo la **configurazione**.
  Il `DEFAULT` lo applica [`proc_apply_storicizza_defaults`](/dbzero/maintenance/manual/proc_apply_storicizza_defaults).
* Non segnala niente a nessuno: scrive un riepilogo (`N aggiunte, M potate`) nel
  log del server, perché chi la chiama è un job pgAgent e non ha dove leggere un
  valore di ritorno.

---

### Esempio di utilizzo

```sql
CALL maintenance.proc_sync_storico_set_storicizza();
```

Idempotente: chiamarla due volte di fila non cambia niente.

---

### Verifica

`db/pgtap/maintenance/test-storicizza-set-potatura.sql` — i tre casi della
tabella qui sopra, costruiti uno per uno.

---

{% include-markdown "signature-core.md" %}
