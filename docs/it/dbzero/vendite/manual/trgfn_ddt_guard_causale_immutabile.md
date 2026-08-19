## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_ddt_guard_causale_immutabile`

> 👀 **Vedi anche**
>
**Il gate che presidia il momento dell'emissione:**
>
• [vendite.trgfn_ddt_guard_causale_emissione](/dbzero/vendite/funzioni/trgfn_ddt_guard_causale_emissione)
> • [script.fn_check_ddt_emittibile](/dbzero/script/funzioni/fn_check_ddt_emittibile)
>
**Dove vive la dichiarazione d'intento:**
>
• [config.causali_trasporto](/dbzero/config/tabelle/causali_trasporto)

### 🎯 Scopo Principale

(creata 2026-08-19 — brief-ddt-righe-senza-prezzo §9 slice B, decisione D-4)

**Una volta che il DDT è uscito dalla bozza, la causale di trasporto non si
cambia più.** In bozza si cambia liberamente.

La ragione prima non è informatica: **la causale è stampata sul documento di
trasporto**. Cambiarla dopo l'emissione vorrebbe dire che il foglio consegnato al
vettore e la riga in archivio dicono cose diverse.

### Il buco che chiude

Il gate all'emissione guarda **solo la transizione verso EMESSO**: esce in testa
se lo stato nuovo non è quello. Quindi un `UPDATE` che portava
`causale_trasporto_id` da CONTO_VISIONE a VENDITA su un DDT **già spedito** non
ripassava da nessun controllo. Da lì:

1. la riga senza prezzo diventava eleggibile per il lister di fatturazione, il
   cui unico discriminatore è `causali_trasporto.fatturabile`;
2. il push la portava fino a `fn_upsert_commessa_attivita`, che la respingeva con
   «prezzo_snapshot obbligatorio».

Nessuna corruzione — l'ultima cintura tiene — ma l'errore arrivava **tardi, in
batch, e senza nominare la causa**: chi lo leggeva cercava un difetto nel push.

> ⚠️ Quella porta era già chiusa **in Python** (`ddt_service` ammette modifiche
> di testata solo in bozza). Questo guard non ripara un difetto osservabile:
> sposta un invariante dove il progetto ha deciso che stia. La domanda non è «è
> successo?», è «può succedere?» — e la risposta dipendeva da una costante in un
> file.

### ⚠️ Due dettagli che un guard scritto in fretta sbaglia

**Si legge lo stato VECCHIO, non il nuovo.** L'`UPDATE` che porta DRAFT → EMESSO
scegliendo contestualmente la causale è l'operazione legittima per eccellenza —
l'operatore sceglie la causale ed emette. Guardando `NEW` la si boccerebbe, e il
guard sarebbe verde su tutti gli altri casi rompendo l'unico che conta.

**La clausola `WHEN` filtra sul valore, non sulla menzione.** `UPDATE OF colonna`
scatta anche quando le si riassegna lo **stesso** valore — cioè a ogni
salvataggio di testata che rimanda indietro tutti i campi del form. Senza la
`WHEN`, riemettere la stessa causale su un DDT spedito verrebbe bloccato: un
errore su un'operazione che non cambia niente.

### Regole

- Codice sollevato: **`E_DDT_CAUSALE_IMMUTABILE`** (932, classe
  `CONFLITTO_STATO`). Il messaggio nomina il DDT; la soluzione dice l'unica cosa
  che l'operatore può fare — annullare il documento e rifarlo.
- Uso: `BEFORE UPDATE OF causale_trasporto_id FOR EACH ROW
  WHEN (NEW.causale_trasporto_id IS DISTINCT FROM OLD.causale_trasporto_id)`.
- Fase `a10` come tutti i guard di questa tabella.

### Note

Prima di introdurlo sono stati eseguiti col trigger attivo i **26 file pgTAP**
che impostano `causale_trasporto_id`: nessuno si rompe. Tutti la impostano
mentre il DDT è in bozza, prima di avanzare lo stato — che è anche l'ordine in
cui lavora l'applicazione.
