# 9. Matriz de Garantia da Qualidade (QA)

Este documento estabelece o escopo de validações sistêmicas, cobrindo análises funcionais, defesas de segurança cibernética e verificações de performance aplicadas no Cardápio Online.

---

## Sumário

- [9.1 Estratégia e Topologia de QA](#91-estratégia-e-topologia-de-qa)
- [9.2 Validação de Fluxos Logísticos e Transacionais](#92-validação-de-fluxos-logísticos-e-transacionais)
- [9.3 Validação de Gestão de Identidades (Auth)](#93-validação-de-gestão-de-identidades-auth)
- [9.4 Escudos de Segurança Sistêmica](#94-escudos-de-segurança-sistêmica)
- [9.5 Matriz de Performance e Estresse](#95-matriz-de-performance-e-estresse)

---

## 9.1 Estratégia e Topologia de QA

O plano abarca validações multi-camadas que englobam metodologias de análise contínua automatizada visando estabilidade na entrega de novos incrementos (Continuous Integration).

| Classificação de QA | Motor/Ferramenta | Cobertura Estipulada | Gatilho de Execução |
| --- | --- | --- | --- |
| **Testes Unitários** | `pytest` + `pytest-django` | ≥ 80% (Services Layer) | A cada requisição de Pull Request |
| **Testes de Integração** | *Django Test Client* | Integração API-banco de dados | A cada requisição de Pull Request |
| **Análise End-to-End (E2E)** | `Playwright` | Trilhas de *checkout* centrais | Liberação (Release / Tag) |
| **Testes de Degradação (Carga)**| `Locust` | Identificação de gargalos latentes | Verificações Periódicas (Mensais) |
| **Testes de Vulnerabilidade** | OWASP ZAP + `bandit` | Vetores maliciosos conhecidos | *Nightly Builds* e Pré-Auditorias |

---

## 9.2 Validação de Fluxos Logísticos e Transacionais

As transações refletem a área de maior risco sistêmico da aplicação, impondo necessidade de testes restritivos ao redor de anomalias contábeis.

### TC01 — Efetivação Legal de Compra
* **Descrição:** Validação da transformação de um carrinho temporário em pedido registrado em sistema.
* **Premissa:** Cliente portador de JWT válido e cesta contendo `> 0` itens.
* **Ação:** Injeção de requisição `POST` em `/api/orders/` com descritivos logísticos da entrega.
* **Critério de Aceite:** API retorna HTTP 201 (Created), persistindo flag `pending` na base MongoDB e alocando um número transacional validado pela regra de geração interna.

### TC02 — Anulação Tática por Quebra de Estoque
* **Descrição:** Garantia de recusa da ordem caso a grade referencie itens com flag *available* nula na base do lojista no ato exato do checkout.
* **Ação:** Tentativa fraudulenta/defasada de finalizar pedido englobando um identificador de produto indisponível.
* **Critério de Aceite:** O sistema deve abortar a conciliação emitindo HTTP 400 atrelado ao detalhamento claro da inconsistência de estoque.

### TC03 — Resiliência de Snapshot Financeiro (Congelamento de Preço)
* **Descrição:** Garantia contra a alteração contábil fraudulenta sobre o preço estipulado de compra, caso o dono altere seu catálogo posteriomente à finalização do carrinho.
* **Ação:** Concretização da Ordem (Custo do item R$ 20.00). Imediata retificação administrativa do produto na base do dono (Custo majorado R$ 25.00). Leitura da Ordem confirmada pelo cliente.
* **Critério de Aceite:** A matriz histórica da Ordem reflete e mantém R$ 20.00 sem absorver alterações relativas de sub-arrays vinculados.

### TC04 — Impedimento de Transições de Estado Ilógicas
* **Descrição:** Defesa contra cliques acidentais ou burlas no painel de gerência (Kanban) que fujam da esteira linear imposta (ex: "Em andamento" pulando direto para "Finalizado").
* **Ação:** Requisição de manipulação `PATCH` da transição de estado da ordem.
* **Critério de Aceite:** Falhas que anulem o status obrigatório sequencial emitirão HTTP 400 acompanhado do bloco *status_history* indicando recusa e inconsistência sistêmica.

---

## 9.3 Validação de Gestão de Identidades (Auth)

Validações focadas em isolamento dos recursos baseados no tipo do indivíduo logado (Role-Based Access Control).

### TC05 — Expedição de Autenticação Central
* **Descrição:** Geração orgânica de autorizações sistêmicas com fornecimento de chaves cadastradas e validadas previamente.
* **Critério de Aceite:** Invocação de HTTP 200 entregando as chaves *Access_Token* e *Refresh_Token*.

### TC06 — Trancamento Temporário e Defesa Passiva (Account Lockout)
* **Descrição:** Prevenção à quebra criptográfica baseada em engenharia mecânica via Brute-Force limitando acessos falsos seguidos.
* **Ação:** Envio repetido de pacotes errôneos (5 ciclos) ao mesmo nó alvo `email`.
* **Critério de Aceite:** Retorno com paralisação temporal via HTTP 429 estipulada em penalização por intervalo predefinido de 15 minutos de inoperância.

### TC07 — Reconciliação Delegada Segura (Google SSO OAuth 2.0)
* **Descrição:** Resolução da autoridade delegada via OAuth convertida para token local.
* **Ação:** Transferência de `authorization_code` legítimo.
* **Critério de Aceite:** Perfil *Customer* padrão mapeado nativamente e inicializado sem intervenção adicional com HTTP 200.

---

## 9.4 Escudos de Segurança Sistêmica

Garantias contra injeções ou exploração de falhas arquiteturais.

### TC08 — Isolamento de Propriedade (Tenant Protection)
* **Descrição:** Proibição do Gestor Alfa de realizar leituras ou sobreposições operacionais de atributos nos estabelecimentos atrelados juridicamente ao Gestor Beta.
* **Critério de Aceite:** Resposta impositiva e seca via HTTP 403 (Forbidden).

### TC09 — Prevenção a Agentes NoSQL (Injection Defenses)
* **Descrição:** Proteção do ODM impedindo o uso de condicionais sintáticas (operadores BSON e lógicos) diretamente nos inputs primários transacionáveis.
* **Ação:** Remessa de carga (`payload`) contendo strings equivalentes a comandos (`{"$gt": ""}`) em substituição aos textos literais.
* **Critério de Aceite:** Sanidade sintática com tratamento explícito validando string contra execução, rejeitando vetores BSON não conformes sem vazamentos laterais.

---

## 9.5 Matriz de Performance e Estresse

Parâmetros estritos definidos para monitoramento sistêmico focado em escalabilidade sob estresse contínuo. Táticas balizadas em premissas de volume suportado simultaneamente.

| Simulação Operacional | Massa de Tráfego Simultânea | Período Contínuo | Limiar Tático de Alvo Aceitável (KPI) |
| --- | --- | --- | --- |
| **Operação Tradicional** | 100 Clientes | 5 min. | P95 Inferior a 200ms; Degradação zero (0% erros). |
| **Volume de Pico Excedente** | 500 Clientes | 10 min. | P95 Marginal até 500ms; Falhas restritas < 1%. |
| **Teste Destrutivo (Ruptura)**| 1.000 Clientes | 15 min. | Análise comportamental na interrupção por gargalos do WebSocket ou limites BSON / DB I/O. |

### Monitoramento Essencial Adotado

| Entidade Alvo | Instrumental | Aceitação Regulamentada |
| --- | --- | --- |
| Resposta do *Load Balancer* | Locust P50 / P95 | Requisições respondidas dentro do tempo estipulado < 200ms. |
| Integridade Relacional (Queries) | MongoDB Atlas Profiler | Tempos de busca e filtragem inferiores a < 100ms. |
| Suporte ao Event-Driven | Métrica de Portas Locais | Capacidade de segregação até as 1000 conexões ativas simuladas sem reinício ou *memory lock* do ASGI Worker. |
