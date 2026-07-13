# Brief DB — Seed lista UI `vendite.resi` (companion slice RESI)

> **Tipo**: mini-brief al team DB · **Target**: `dev/db-tid` · **Data**: 2026-07-13 · **Owner**: Tid
> **Contesto**: residuo della slice RESI ([brief-db-resi-vendita.md](brief-db-resi-vendita.md),
> tracker §10 riga 31 — unico ☐ oltre a pgTAP). Sblocca la lista FE
> (`<ListaConfigurabile codice="vendite.resi">`) del
> [brief-be-fe-resi-vendita.md](brief-be-fe-resi-vendita.md) §11.
> **Perimetro**: SOLO append ai 2 CSV `ui` esistenti (loader runOnChange) — nessun nuovo
> loader, nessun changeSet manuale, nessun oggetto DB.

---

## 1. Oggetto

Mirror del seed lista DDT (definizione id 8 + colonne 128-148), ridotto: il reso non ha
trasporto/logistica/serie e non ha valori economici in questa slice.

### 1a. Append `80_data/sql/ui/lista_definizione.csv` (1 riga, id 9)

```csv
9,vendite.resi,Resi di vendita,vendite,vw_resi_lista,t,2026-07-13 00:00:00,mctit
```

### 1b. Append `80_data/sql/ui/lista_colonna.csv` (12 righe, id 149-160, lista_id 9)

Stesso formato/valori di stile delle righe DDT (128-148); `campo_sorgente` verificato
contro `vw_resi_lista` (doc auto-gen). Proposta:

```csv
149,9,numero,Numero,Numero del reso,numero,identificatore,string,,130,10,left,Identificazione,1,t,t,t,t,f,t,2026-07-13 00:00:00,mctit,vendite.resi.col_numero
150,9,data,Data,Data del reso,data,informazione,date,date_short,110,20,center,Identificazione,1,t,t,t,f,f,t,2026-07-13 00:00:00,mctit,vendite.resi.col_data
151,9,anno,Anno,Anno del reso,anno,informazione,numeric,,80,30,center,Identificazione,1,t,t,t,f,f,t,2026-07-13 00:00:00,mctit,vendite.resi.col_anno
152,9,destinatario_denominazione,Destinatario,Ragione sociale del destinatario,destinatario_denominazione,informazione,string,,200,40,left,Destinatario,2,t,t,t,t,f,t,2026-07-13 00:00:00,mctit,vendite.resi.col_destinatario
153,9,id_fiscale,Id. Fiscale,Identificativo fiscale del destinatario,id_fiscale_univoco_cf_piva,informazione,string,,140,50,left,Destinatario,2,t,t,t,t,f,t,2026-07-13 00:00:00,mctit,vendite.resi.col_id_fiscale
154,9,ba_codice,Cd. Account,Codice del billing account,ba_codice,informazione,string,,120,60,left,Destinatario,2,t,t,t,t,f,t,2026-07-13 00:00:00,mctit,vendite.resi.col_ba_codice
155,9,stato,Stato,Stato corrente del reso,stato_descrizione,informazione,string,,130,70,center,Stato,3,t,t,t,f,f,t,2026-07-13 00:00:00,mctit,vendite.resi.col_stato
156,9,ddt_origine_numero,DDT origine,Numero del DDT di origine,ddt_origine_numero,informazione,string,,130,80,left,Origine,4,t,t,t,f,f,t,2026-07-13 00:00:00,mctit,vendite.resi.col_ddt_origine
157,9,valuta,Valuta,Codice valuta del reso,valuta_codice,informazione,string,,90,90,left,Importi,5,t,t,t,f,f,t,2026-07-13 00:00:00,mctit,vendite.resi.col_valuta
158,9,emittente_fiscale_codice,Emittente,Ragione sociale dell emittente fiscale,emittente_fiscale_descrizione,informazione,string,,120,100,left,Emittente,6,t,t,t,f,f,t,2026-07-13 00:00:00,mctit,vendite.resi.col_emittente
159,9,data_insert,Creazione,Data di inserimento del reso,data_insert,informazione,datetime,datetime_short,150,110,center,Audit,7,t,t,t,f,f,t,2026-07-13 00:00:00,mctit,vendite.resi.col_data_insert
160,9,azioni,Azioni,,,azione,string,,60,999,center,,99,f,f,f,f,f,t,2026-07-13 00:00:00,mctit,common.col_azioni
```

Note sulla proposta:

- **Esclusioni deliberate** (asimmetrie vere col DDT, non dimenticanze): niente
  trasporto/logistica/serie/ordine-origine (il reso aggancia il **DDT**, non l'ordine:
  l'ordine si raggiunge dal DDT); niente importi oltre la valuta (righe senza prezzi
  fino alla slice NC); niente `utility` (parità lista DDT, che non la espone).
- `id_fiscale`/`destinatario`/`ba_codice` `ricercabile_full=t` (parità DDT: alimentano
  la search ILIKE).
- **`azioni` inclusa da subito** (id 160, `ordine_default=999`, `gruppo_ordine=99`) —
  sul DDT è arrivata in coda (148) come fix; qui nasce col seed.
- Chiavi i18n `vendite.resi.col_*`: le aggiunge il **FE** nel blocco `vendite.resi.*`
  (brief BE+FE §14) — nessuna azione DB.

## 2. Verifiche richieste al team DB

1. `id` liberi confermati al momento dell'apply (9 / 149-160): se nel frattempo altri
   seed hanno consumato la sequenza, shiftare — i riferimenti applicativi usano il
   `codice` (`vendite.resi`), mai gli id.
2. Loader `ui` runOnChange: solo append ai 2 CSV, nessun nuovo file
   ([[feedback_messaggi_errore_no_new_loader]], stesso principio).
3. Nessun preset: colonne tutte `attivo=t`, visibilità default gestita dal runtime
   (parità DDT — la colonna Emittente resta opt-in a livello di preset utente come
   deciso per il DDT, niente di speciale da seedare).

## 3. Promemoria collegato (non parte di questo brief)

Resta aperta la riga **T** del tracker slice RESI: **pgTAP** write-side/read-side/RLS
(brief DB §6). Indipendente da questo seed.

## 4. Avanzamento

| # | Step | Stato |
|---|---|---|
| 1 | Append `lista_definizione.csv` (id 9) | ☐ |
| 2 | Append `lista_colonna.csv` (149-160) | ☐ |
| 3 | Apply + verifica runtime (`GET /api/v1/ui/liste/...` risolve `vendite.resi`) | ☐ |
