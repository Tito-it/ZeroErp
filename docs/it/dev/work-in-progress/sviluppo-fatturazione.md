# Sviluppo fatturazione — Note operative

> Documento di lavoro in continua evoluzione. Raccoglie promemoria, decisioni aperte e analisi parziali sul modulo fatturazione di ZeroErp. Si integra con [gestione-commesse-v2.md](../work-done/gestione-commesse-v2.md) (motore commesse → attivita_fatturabili) e con la guida operativa [fatturazione.md](../../guide/fatturazione.md) (quando esistera).

---

## Promemoria aperti

### PROMO-1 — Preview fatturazione contratto (UI mancante)

**Data**: 2026-05-19
**Stato**: aperto, non ancora pianificato.

Oggi non esiste un punto nella UI dove l'operatore possa vedere, per un contratto ATTIVO, una preview del tipo:

> "Questo contratto, sulla competenza di un dato mese, fatturera' le seguenti righe per un totale di X euro."

Il dato esiste nel motore (`fn_list_contratti_da_pushare` produce un payload per riga × mese), ma non c'e' componente FE che lo presenti.

**Implicazione per altri lavori in corso**:

- L'analisi opzione B su `vendite.contratti_righe` (esporre `fonte_quantita_attesa` in UI, decidere se mostrare/nascondere `quantita` sul drawer riga) sarebbe semplificata dalla presenza di una preview fatturazione: oggi il drawer riga e' l'unico punto in cui l'utente vede la `quantita`, e quindi la domanda "mostrarla o no" pesa di piu'.
- Con una preview fatturazione disponibile, il drawer riga potrebbe limitarsi a esporre le "regole" senza dover comunicare il "totale periodico".

**Quando affrontarlo**: da decidere. Probabilmente dopo aver chiuso il modulo motore commesse (vedi [gestione-commesse-v2.md](../work-done/gestione-commesse-v2.md) — `HandlerContratti` ancora scheletro vuoto).
