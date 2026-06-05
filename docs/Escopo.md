# Escopo — OrbitFire (GS 2026.1)

> **Documento congelado.** Alteracoes somente com autorizacao explicita do autor do projeto.
> Em caso de duvida sobre o que entregar, consulte este arquivo antes de implementar.

---

## 1. Produto

**Nome:** OrbitFire

**Resumo:** POC que prevê **risco de incendio para o dia seguinte** no **Centro-Oeste do Brasil** (GO, MT, MS, DF), cruzando dados de satelite NASA FIRMS com clima local e priorizando regioes para alocacao de brigadas.

**Pergunta da GS respondida:** Como a IA e as tecnologias digitais transformam a economia espacial em impacto positivo na Terra — usando deteccoes orbitais para **acao preventiva** contra incendios, antes do fogo se espalhar.

---

## 2. Regiao de cobertura


| Item            | Valor                                              |
| --------------- | -------------------------------------------------- |
| Macroregiao     | Centro-Oeste (Brasil)                              |
| UFs             | GO, MT, MS, DF                                     |
| Bbox aproximado | lat -24,1 a -12,0 / lon -61,6 a -45,0              |
| Grade           | Celulas geograficas configuraveis (graus decimais) |


---

## 3. Entrega final (o que a banca deve ver)

### 3.1 Funcionalidades obrigatorias


| #   | Entrega                       | Descricao                                                        |
| --- | ----------------------------- | ---------------------------------------------------------------- |
| E1  | Pipeline de ingestao FIRMS    | Focos VIIRS/MODIS via API NASA (ou seed offline)                 |
| E2  | Pipeline de clima             | Temperatura, precipitacao, vento por dia/regiao                  |
| E3  | Grade e persistencia          | Celulas do Centro-Oeste em SQLite                                |
| E4  | Features e labels             | Variaveis preditivas; label = incendio na celula no dia seguinte |
| E5  | Modelo preditivo              | LightGBM treinado e serializado                                  |
| E6  | Risk score                    | Score 0–100 com faixas baixo / medio / alto / critico            |
| E7  | Priorizador de brigadas (M10) | Ranking Top-N com justificativa operacional                      |
| E8  | API REST                      | FastAPI: mapa de risco, ranking, focos ativos, health            |
| E9  | Dashboard                     | Streamlit com mapa interativo, KPIs, filtros e export CSV        |
| E10 | Modo demo offline             | `OFFLINE_MODE` com dados seed para apresentacao sem internet     |
| E11 | Testes automatizados          | pytest cobrindo modulos criticos (ETL, dominio, API)             |
| E12 | Documentacao                  | README na raiz (derivado deste escopo), instrucoes de execucao   |


### 3.2 Fora do escopo (evolucao futura — nao implementar sem autorizacao)


| Item                                                      | Motivo                                 |
| --------------------------------------------------------- | -------------------------------------- |
| ESP32 / sensores locais (M12)                             | Evolucao futura acordada               |
| Resumo cognitivo / LLM (M11)                              | Fora do MVP                            |
| Segmentacao de cicatriz de queimada (visao computacional) | Fora do MVP                            |
| Simulador de propagacao de fogo                           | Fora do MVP                            |
| Deploy AWS Lambda em producao                             | Opcional; nao obrigatorio para entrega |


---

## 4. Stack tecnica acordada


| Camada           | Tecnologia                   |
| ---------------- | ---------------------------- |
| Linguagem        | Python 3.10+                 |
| ML               | LightGBM                     |
| API              | FastAPI + Uvicorn            |
| Dashboard        | Streamlit + Folium ou PyDeck |
| Banco            | SQLite                       |
| Dados espaciais  | NASA FIRMS API               |
| Dados climaticos | Open-Meteo ou Meteostat      |
| Testes           | pytest                       |
| Config           | `.env` + `src/config.py`     |


---

## 5. Modulos do sistema (MVP)


| Modulo | Nome                    | No MVP?      |
| ------ | ----------------------- | ------------ |
| M1     | Ingestao FIRMS          | Sim          |
| M2     | Ingestao clima          | Sim          |
| M3     | Grade geografica        | Sim          |
| M4     | Features e labels       | Sim          |
| M5     | Motor IA (LightGBM)     | Sim          |
| M6     | Risk score              | Sim          |
| M7     | API FastAPI             | Sim          |
| M8     | Dashboard Streamlit     | Sim          |
| M9     | Demo offline            | Sim          |
| M10    | Priorizador de brigadas | Sim          |
| M11    | Resumo cognitivo        | Nao          |
| M12    | ESP32                   | Nao (futuro) |


---

## 6. Criterios de aceite da entrega

- Demo roda com um comando documentado (API + dashboard ou script unico)
- Mapa exibe risco preditivo para o Centro-Oeste
- Ranking de brigadas (M10) visivel na API e no dashboard
- Modo offline funcional para apresentacao em sala
- Testes pytest passam localmente
- README explica problema, solucao, arquitetura e limitacoes da POC
- Nenhuma feature fora da secao 3.2 implementada sem atualizar este escopo

---

## 7. Publico-alvo da solucao

- Gestores de defesa civil e coordenadores de brigada florestal no Centro-Oeste
- Cooperativas agricolas em busca de alerta preventivo
- Banca FIAP (demonstracao clara do valor da economia espacial aplicada)

---

## 8. Referencias

- Edital: `docs/Titulo.md`
- Acompanhamento de sprints: `docs/Implementacao.md`
- Regras de alteracao: somente o autor do projeto autoriza mudanca neste arquivo

