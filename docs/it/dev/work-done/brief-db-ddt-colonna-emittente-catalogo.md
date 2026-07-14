# Brief DB — Lista DDT: colonna "Emittente" a catalogo

> **Stato: ✅ CHIUSO (2026-07-12)** — seed applicato dal team DB (verificato su
> DB di test: `ui.lista_colonna` id 147, i18n key `vendite.ddt.col_emittente`).
>
> **Tipo**: brief al team DB · **Target**: `dev/db-tid` · **Data**: 2026-07-12 · **Owner**: Tid
> **Contesto**: parità di catalogo con le altre 4 liste documento. La colonna
> Emittente esiste in `ui.lista_colonna` per contratti/preventivi/offerte/ordini
> (opt-in: NON è in alcun preset, si attiva solo dalla personalizzazione — utile
> al solo admin globale/multi-emittente). La lista DDT è l'unica senza: non è
> attivabile nemmeno volendo.

## Richiesta

1 riga di seed in `ui.lista_colonna` per la lista `vendite.ddt`
(`lista_definizione` id 8), speculare alla riga omologa di `vendite.ordini`
(colonna id 122):

| Campo | Valore |
| --- | --- |
| codice | `emittente_fiscale_codice` |
| etichetta / estesa | Emittente / Codice dell'emittente fiscale |
| campo_sorgente | `emittente_fiscale_codice` (già esposto da `vw_ddt_lista`) |
| gruppo | Emittente |
| etichetta_i18n_key | `vendite.ddt.col_emittente` (chiavi FE it/en già predisposte) |
| altri attributi | come la riga ordini (informazione/string, filtrabile/ordinabile/esportabile, non ricercabile_full, non sensibile) |

## Vincoli

- **NON** aggiungerla ad alcun preset (`lista_preset_colonna`): resta opt-in,
  come sulle altre 4 liste.
- Nessun'altra azione: vista, BE e i18n FE sono già a posto.
