## 📘 Documentazione Concettuale – Funzione `script.fn_guard_livello()`

> 👀 **Vedi anche**
>
> **La regola che applica:** [script.fn_resolve_livello_oggetto](/dbzero/script/funzioni/fn_resolve_livello_oggetto) — la stessa del backend
>
> **L'area dell'oggetto:** [script.fn_area_di_oggetto](/dbzero/script/funzioni/fn_area_di_oggetto)
>
> **I gemelli:** [script.fn_guard_azione](/dbzero/script/funzioni/fn_guard_azione) (azione di processo) · [script.fn_guard_super_admin](/dbzero/script/funzioni/fn_guard_super_admin)
>
> **Chi la chiama:** [config.fn_pannello_scrivi](/dbzero/config/funzioni/fn_pannello_scrivi)

---

### 🎯 Scopo Principale
(scritta il 25-09-2026)

È il guard con cui un verbo di scrittura chiede che **chi agisce abbia almeno un
certo livello su un oggetto**. Si chiama nella prima riga del verbo: se il
livello non basta, il verbo si ferma prima di toccare qualunque cosa.

È la forma per le operazioni semplici (crea, modifica). Le operazioni di
processo (emetti, annulla, registra) chiedono invece un'azione, con
`fn_guard_azione`.

Il verbo dichiara **l'oggetto**, non l'area: l'area la ricava
`fn_area_di_oggetto`. La regola la decide `fn_resolve_livello_oggetto`, la stessa
che usa il backend: un override dell'utente sull'oggetto vale anche qui.

---

### Cosa risponde

| Situazione | Esito |
| --- | --- |
| il livello di chi agisce arriva al minimo | niente: il verbo prosegue |
| il livello è sotto il minimo | `E_PERMESSO_NEGATO`, lo stesso codice del backend |
| chi agisce entra da un'altra porta (portale, shop) | `E_PERMESSO_NEGATO` |
| nessun utente in sessione, oggetto o minimo mancanti | `E_PERMESSO_NEGATO` (nel dubbio, no) |

⚠️ **I livelli sono ordinati al contrario di come si leggono**: nel database
`TUTTO` viene prima di `LETTURA`, che viene prima di `BLOCCATO`. «Arrivare al
minimo» vuol dire avere un livello **uguale o precedente**. Il pgTAP controlla
tutti e due i versi, perché un confronto scritto a occhio concederebbe tutto a
chi è bloccato.

```sql
PERFORM script.fn_guard_livello(
    NULLIF(current_setting('app.current_user_id', true), '')::integer,
    'magazzino', 'causali', 'TUTTO');
```

Presidio: `db/pgtap/script/test-fn-guard-livello-v1.sql`.

{% include-markdown "signature-core.md" %}
