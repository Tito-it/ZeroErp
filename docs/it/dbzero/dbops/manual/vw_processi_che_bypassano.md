## 📘 Documentazione Concettuale – View `dbops.vw_processi_che_bypassano`

> 👀 **Vedi anche**
>
Approfondimenti tabelle:
>
[dbops.processi](/dbzero/dbops/manual/processi)

---
### 🎯 Scopo Principale
(latest review 04-09-2026)

Elenca i **ruoli applicativi che saltano la row level security**, cioè quelli
che vedono e scrivono tutto senza che nessuna policy li filtri.

> ⚠️ **Deve arrivare a zero righe.** Oggi ne ha **una**:
> `zeroerp_batch_fatturazione`.

---

### Perché una vista, e non semplicemente «non dare il bypass a nessuno»

Perché il bypass **c'è già**, e toglierlo è un lavoro che vive fuori dal
database: il ruolo va ritirato nel provisioning e il backend deve smettere di
collegarsi con quello.

⇒ Finché quel lavoro non è fatto, la scelta è fra due cose:

| | |
| --- | --- |
| Non scrivere niente | il bypass resta, e **nessuno se lo ricorda** |
| Questa vista | il bypass resta, ma è **contato**, e cala sotto gli occhi |

⭐ È il primo passo del cantiere ed è indipendente da tutto il resto: non toglie
niente a nessuno, e dice da subito quanto è grande il problema.

---

### ⚠️ L'elenco dei ruoli applicativi è DICHIARATO, non dedotto dal nome

È il punto delicato di questa vista.

`pg_roles.rolbypassrls` si legge facilmente, ma dice chi bypassa — non chi
**dovrebbe** bypassare. Un superuser bypassa ed è legittimo; un demone di
scheduling pure.

⛔ Dedurre «è applicativo perché si chiama `zeroerp_*`» sarebbe un criterio
fragile: il giorno che qualcuno crea `zeroerp_readonly` la vista comincia a
mentire in un verso o nell'altro. ⇒ L'elenco dei ruoli applicativi è scritto
nella vista.

---

### ⚠️ Che cosa NON si usa qui

`information_schema.role_table_grants` **è cieco fuori dal ruolo connesso**:
mostra solo i privilegi che la sessione corrente può vedere. Una vista costruita
su quella sarebbe vuota per motivi che non hanno niente a che fare con la
sicurezza. ⇒ Si legge `pg_roles`, che è il catalogo vero.

---

### Esempio d'uso

```sql
-- Chi salta ancora la row level security?
SELECT * FROM dbops.vw_processi_che_bypassano;
```

⇒ Quando questa query non restituisce niente, il ritiro del ruolo batch è
completo e il guard di scrittura diventa efficace anche su quel processo.

Origine: `docs/it/dev/work-done/brief-db-processi-automatici-identita-e-perimetro.md` §8.

---

{% include-markdown "signature-core.md" %}
