## Documentazione Concettuale -- Tabella `config.email_allegato`

> Vedi anche
>
> Approfondimento tabelle:
>
> [config.email_outbox](/dbzero/config/tabelle/email_outbox)
> [config.email_log](/dbzero/config/tabelle/email_log)

---

### 🎯 Scopo Principale

La tabella `config.email_allegato` traccia i **file allegati** alle email. I file sono salvati su filesystem (non in DB); la tabella contiene solo i metadati e il percorso relativo.

---

### Ciclo di vita

1. **Pre-invio**: l'allegato e' associato a una bozza (`email_outbox_id`). L'operatore puo' aggiungere o rimuovere allegati dal dialog "Componi email".
2. **Post-invio**: l'allegato viene copiato sul record di log (`email_log_id`) per consultazione storica. Il file fisico resta lo stesso.
3. **Solo in bozza**: un allegato si aggiunge, modifica o toglie solo finché la sua bozza è `DRAFT`. Dopo l'invio fa parte di ciò che è stato spedito, e il database rifiuta qualunque modifica. L'unica scrittura ammessa fuori dalla bozza è l'aggancio al log al momento dell'invio. Se l'invio fallisce, la bozza torna `DRAFT` e gli allegati tornano modificabili.
4. **Eliminazione della bozza**: una bozza si elimina solo in `DRAFT`, e i suoi allegati la seguono (ON DELETE CASCADE). Una mail spedita o annullata non si elimina: resta, con i suoi allegati.

---

### Chi vede un allegato

Un allegato si vede se si vede la sua email: la bozza (`email_outbox_id`) **o** il log (`email_log_id`). Dopo l'invio l'allegato è legato a entrambe. La regola dell'ambito resta quella delle due tabelle madri, e il database la applica passando da loro (policy `rls_email_allegato_ambito`). Un allegato senza nessuna delle due non lo vede nessuno, e non si può scrivere.

---

### Origine

| Valore     | Significato                                                               |
| ---------- | ------------------------------------------------------------------------- |
| `UPLOAD`   | Caricato manualmente dall'operatore (drag & drop nel dialog)              |
| `TEMPLATE` | Allegato di default del template (es. guida utente PDF, policy aziendale) |

---

### Storage

I file sono salvati su filesystem con path strutturato:

```
email_attachments/YYYY/MM/<uuid>.<ext>
```

Il campo `file_path` contiene il percorso relativo rispetto alla root dello storage configurata in `EMAIL_ATTACHMENTS_ROOT`. La dimensione e' validata lato backend (`EMAIL_ATTACHMENT_MAX_SIZE_MB`).

---

### Vincoli e regole

* CHECK: `origine IN ('UPLOAD', 'TEMPLATE')`
* CHECK: `dimensione_bytes > 0`
* FK CASCADE su `email_outbox_id` -- cancellazione bozza elimina allegati
* FK NO ACTION su `email_log_id` -- non si cancella un log che ha allegati
* Indici su `email_outbox_id` e `email_log_id` per lookup
