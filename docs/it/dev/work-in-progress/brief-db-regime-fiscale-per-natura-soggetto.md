# Brief DB — Il regime fiscale del soggetto segue la sua natura

> **Stato:** ⛔ assorbito il 2026-10-10 in
> [brief-db-dati-fiscali-e-societari-del-soggetto.md](brief-db-dati-fiscali-e-societari-del-soggetto.md).
> Questo file resta solo come rimando: non si lavora qui.

Il contenuto si è diviso così:

| Qui | Là |
| --- | --- |
| §3.1, §4.1 — cliente PA e split payment per dettaglio | **Parte A** (§1, decisioni A-1…A-5) |
| §3.2, §4.2 — titoli IVA per dettaglio | **Parte D** (§3bis, decisioni D-1…D-6) |
| §4.3 — le righe che già violano | §3bis.4 e C-3 |
| §5 — pgTAP | §3bis.5 |
| §6 — ricadute BE/FE | §5, voci A e D |
| §7 — decisioni aperte | A-2, D-3; il legame fra i due flag resta fuori, come qui |
| §8 — `fornitori.split_payment` | §7, da verificare, eventualmente brief suo |

Correzioni fatte nel passaggio (analisi critica, 2026-10-10):

- `cliente_pa` **non** decide l'esigibilità: la legge solo `split_payment`, e `cliente_pa` oggi non
  ha lettori;
- la regola «una persona fisica non è mai PA né in split» diventa un CHECK sulla natura base, non
  solo configurazione;
- il guard sul cambio di dettaglio deve leggere i titoli **sotto DEFINER** (la RLS per emittente
  lo accecherebbe), e il criterio è «vigente», non «attivo» (un titolo con movimenti non si
  disattiva mai);
- matrice senza righe e soggetto senza dettaglio: rifiuto, non ripiego permissivo.
