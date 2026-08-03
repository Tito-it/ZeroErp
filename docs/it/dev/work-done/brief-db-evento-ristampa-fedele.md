# Brief BE → DB — un valore nel CHECK `evento_tipo` per la ristampa fedele

> **Chi scrive:** BE/FE (`dev/backend-tid`), 2026-08-03.
> **A chi:** team DB (`dev/db-tid`).
> **Cos'è:** **una riga** — aggiungere `RISTAMPA_FEDELE` al set chiuso di
> `chk_documenti_generati_eventi_evento_tipo`. È l'unico prerequisito DB del
> cantiere ristampa fedele, che per il resto è tutto applicativo come il vostro
> brief prevedeva (§4: «lato DB non c'è niente da costruire»).
> **Correlati:** [brief-ristampa-fedele-documenti.md](brief-ristampa-fedele-documenti.md)

---

## 1. Perché serve

Il vostro §8.3 lasciava aperta la domanda «la ristampa fedele lascia traccia?».
**Tid ha deciso di sì** (2026-08-03). L'evento è l'**unica scrittura** del
percorso 3 — non c'è alcuna riga nuova in `documenti_generati`, nessun
progressivo consumato, nessuno stato sorgente toccato (§5.1.4 rispettato).

Il set oggi è chiuso a quattro valori (`20260603-04`):

```
GENERATO, SCARICATO, STORAGE_ORPHAN, ALLEGATO_AGGIUNTO
```

`RISTAMPA_FEDELE` va aggiunto come quinto. **Non riusiamo `GENERATO`**: sarebbe
esattamente la confusione che il vostro brief smonta — una ristampa non è
un'emissione, e un audit che le mescola non permette più di distinguerle
guardando la timeline.

## 2. La modifica

Stessa forma di `20260603-04` (DROP + ADD del CHECK, `runOnChange: false`,
numerazione successiva):

```sql
ALTER TABLE documenti.documenti_generati_eventi
    DROP CONSTRAINT IF EXISTS chk_documenti_generati_eventi_evento_tipo;

ALTER TABLE documenti.documenti_generati_eventi
    ADD CONSTRAINT chk_documenti_generati_eventi_evento_tipo
    CHECK (evento_tipo IN (
        'GENERATO',
        'SCARICATO',
        'STORAGE_ORPHAN',
        'ALLEGATO_AGGIUNTO',
        'RISTAMPA_FEDELE'
    ));
```

Da aggiornare anche il `COMMENT ON COLUMN`, che elenca il set.

## 3. Cosa NON serve toccare

- **`esito`**: la ristampa usa `WARN` quando il PDF è fedele nel contenuto ma
  non nei byte (decisione §8.2 — «soluzione 1»). `WARN` è **già** nel CHECK
  `chk_documenti_generati_eventi_esito` (`OK`/`KO`/`WARN`) e significa
  esattamente questo. Nessun valore nuovo.
- **Nient'altro.** Le letture del percorso 3 (snapshot congelato + versione
  pinnata anche OBSOLETA) girano su tabelle e colonne esistenti; gli invarianti
  che le proteggono sono quelli che avete elencato in §4 e sono già presidiati.

## 4. Cosa succede finché non c'è

Il cantiere è **già completo e funzionante** senza questa migration: l'INSERT
dell'evento è best-effort in una transazione separata — stesso pattern del
`SCARICATO` del download — quindi il CHECK lo rifiuta, il servizio logga
`documenti.ristampa_fedele.evento_fallito` e **il PDF esce comunque**. Negare
la ristampa per un log mancante sarebbe peggio del log mancante.

⚠️ Questo però è anche il motivo per cui la migration non va rimandata a lungo:
un rosso che si vede solo nei log è un rosso che si smette di guardare. Con il
CHECK esteso, la traccia c'è e la definizione di «fatto» del vostro §6 si chiude
del tutto.

## 5. Verifica dopo l'apply

Una ristampa fedele da UI (azione «Ristampa fedele» sulla lista documenti di un
preventivo) deve produrre una riga:

```sql
SELECT evento_tipo, esito, detail->>'pdf_hash_match', detail->>'template_versione_id'
  FROM documenti.documenti_generati_eventi
 WHERE evento_tipo = 'RISTAMPA_FEDELE'
 ORDER BY id DESC LIMIT 5;
```

Sul caso di prova del vostro §6.4 — l'**offerta di maggio**, doc 22, template v1
— l'esito atteso è `OK` se il renderer riproduce gli stessi byte, `WARN` con
`pdf_hash_match=false` se il motore nel frattempo è cambiato. **Entrambi sono
successi**: la differenza di byte è dichiarata, non nascosta.
