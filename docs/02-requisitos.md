# 2. Especificação de Requisitos

Este documento cataloga os requisitos técnicos, operacionais e de negócio que orientam o desenvolvimento e as validações arquiteturais do sistema Cardápio Online.

---

## Sumário

- [2.1 Requisitos Funcionais](#21-requisitos-funcionais)
- [2.2 Requisitos Não Funcionais](#22-requisitos-não-funcionais)
- [2.3 Matriz de Rastreabilidade](#23-matriz-de-rastreabilidade)

---

## 2.1 Requisitos Funcionais

### RF01 — Gestão de Identidade e Acesso (Cadastro)

| Propriedade | Especificação |
| --- | --- |
| **Identificador** | RF01 |
| **Descrição** | A plataforma deve suportar o registro de duas entidades de usuários distintas: `customer` (cliente final) e `owner` (gestor do restaurante). O processo de onboarding deve suportar registro via credenciais tradicionais e via Single Sign-On (Google OAuth 2.0). |
| **Regras de Negócio** | O endereço de e-mail deve ter restrição de unicidade na base de dados. Senhas devem possuir entropia mínima (8 caracteres, incluindo caracteres alfanuméricos e especiais). A autenticação via OAuth deve resolver o perfil automaticamente. |
| **Criticidade** | Máxima |

### RF02 — Autenticação de Sessão

| Propriedade | Especificação |
| --- | --- |
| **Identificador** | RF02 |
| **Descrição** | O sistema deve autenticar usuários e gerenciar o ciclo de vida das sessões através da emissão de JSON Web Tokens (JWT) stateless. |
| **Regras de Negócio** | O *Access Token* deve expirar em 24 horas. O *Refresh Token* deve possuir validade de 7 dias. Mecanismos de rate limiting e account lockout devem ser aplicados após 5 falhas sucessivas (cooldown de 15 minutos). |
| **Criticidade** | Máxima |

### RF03 — Provisionamento de Restaurantes (Tenants)

| Propriedade | Especificação |
| --- | --- |
| **Identificador** | RF03 |
| **Descrição** | Usuários com a role `owner` devem ter a capacidade de provisionar e gerenciar metadados de seus estabelecimentos (nome da marca, descrição, dados de contato, horário de operação e identidade visual). |
| **Regras de Negócio** | A identidade visual (imagem de capa) é mandatória e deve ser hospedada em Object Storage (S3). Um restaurante é provisionado com status padrão de `inactive` até a sua aprovação final. |
| **Criticidade** | Máxima |

### RF04 — Gestão de Catálogo e Produtos

| Propriedade | Especificação |
| --- | --- |
| **Identificador** | RF04 |
| **Descrição** | A plataforma deve permitir o Cadastro (CRUD) de produtos vinculados a um tenant específico, suportando metadados de vendas e imagens associadas. |
| **Regras de Negócio** | Produtos devem ser categorizados rigidamente via enumerações (`appetizer`, `main`, `dessert`, `drink`, `combo`). O atributo de precificação não pode ser negativo ou zero. Imagens de produto têm restrições de MIME type (jpg/png/webp) e tamanho máximo de 5MB. |
| **Criticidade** | Máxima |

### RF05 — Visualização e Descoberta de Cardápios

| Propriedade | Especificação |
| --- | --- |
| **Identificador** | RF05 |
| **Descrição** | A plataforma deve prover uma interface pública para navegação assíncrona dos cardápios disponíveis, sem exigência de autenticação prévia. |
| **Regras de Negócio** | Implementação mandatória de paginação cursor-based ou offset-based (12 itens por ciclo). Filtros multicritério (categoria, nome). Apenas itens com flag `available` de restaurantes em status `active` devem ser retornados nas consultas públicas. |
| **Criticidade** | Alta |

### RF06 — Motor de Carrinho de Compras

| Propriedade | Especificação |
| --- | --- |
| **Identificador** | RF06 |
| **Descrição** | Usuários com sessão ativa podem compor ordens de serviço mediante adição e alteração de produtos no carrinho de compras. |
| **Regras de Negócio** | Persistência híbrida do estado (localStorage client-side com sincronização remota). Restrição estrita de contexto: um carrinho não pode conter produtos oriundos de tenants diferentes de forma simultânea. Quantidade limitante operacional por item: 99 unidades. |
| **Criticidade** | Máxima |

### RF07 — Orquestração de Checkout e Pedidos

| Propriedade | Especificação |
| --- | --- |
| **Identificador** | RF07 |
| **Descrição** | O sistema deve processar a transição do estado do carrinho para um Pedido oficial (`Order`), submetendo as variáveis de entrega e restrições alimentares. |
| **Regras de Negócio** | Requisição fortemente tipada e com autorização exigida. A aplicação deve realizar um snapshot contábil (congelamento) do preço unitário de cada item no momento da criação do pedido para garantir integridade fiscal histórica. Transmissão imediata via WebSocket para o terminal do restaurante. |
| **Criticidade** | Máxima |

### RF08 — Gerenciamento Operacional de Pedidos

| Propriedade | Especificação |
| --- | --- |
| **Identificador** | RF08 |
| **Descrição** | O tenant deve possuir uma interface administrativa para visualização, gestão e transição de estado da fila de pedidos de forma síncrona. |
| **Regras de Negócio** | A arquitetura deve forçar a progressão do status linearmente (`pending` -> `preparing` -> `ready` -> `delivered`). Emissão de logs de auditoria e notificações real-time aos clientes mediante a mudança de estado de qualquer transação. |
| **Criticidade** | Máxima |

---

## 2.2 Requisitos Não Funcionais

### RNF01 — Escalabilidade Arquitetural
* **Volume Alvo:** A arquitetura deve ser desenhada para suportar 500+ tenants e processar volumes superiores a 10.000 pedidos diários.
* **Performance da API:** O percentil P95 do tempo de resposta da API deve ser estritamente inferior a 200ms.
* **Comunicação Assíncrona:** A infraestrutura de WebSockets deve sustentar 1.000 conexões ativas simultâneas sem degradação do channel layer.
* **Storage:** Utilização de instâncias escaláveis horizontalmente com cache de sessão.

### RNF02 — Padrões de Segurança e Compliance
* **Criptografia:** Senhas protegidas via algoritmo `bcrypt` com custo computacional mínimo configurado para 12.
* **Tokens:** Algoritmo RS256 adotado como padrão para as assinaturas dos JSON Web Tokens.
* **Protocolos:** O uso de HTTPS (TLS 1.3) é mandatório para todas as comunicações intra e extra rede.
* **Defesas Ativas:** Atuação de middlewares de Rate Limiting (100 requisições/minuto por IP), whitelist estrita de CORS, validações de sanitização de inputs contra NoSQL Injection e XSS. Header constraints (`X-Frame-Options`, `X-Content-Type-Options`).
* **Compliance de Acesso:** Verificações obrigatórias de *Ownership* ao nível do Service Layer em qualquer operação de mutação (Write Operations).

### RNF03 — Alta Disponibilidade (High Availability)
* **SLA de Uptime:** Alvo de estabilidade em 99.5% (máximo de 3.65 horas de inoperabilidade mensal).
* **SLO Tático:** Recovery Time Objective (RTO) estipulado em 15 minutos; Recovery Point Objective (RPO) em 1 hora.
* **Resiliência do Cluster:** Banco de dados operando em arquitetura Replica Set distribuída (mínimo de 3 nós geográficos).

### RNF04 — Desempenho e Front-end
* **Core Web Vitals:** First Contentful Paint (FCP) inferior a 1.5s; Largest Contentful Paint (LCP) inferior a 2.5s; Cumulative Layout Shift (CLS) próximo de zero (≤ 0.1).
* **Otimização de Mídia:** Conversão automática de assets fotográficos para o formato `WebP` servidos via Edge Network (CDN) utilizando Lazy Loading agressivo.

### RNF05 — Experiência de Uso (UX) e Acessibilidade
* **Mobile-First Indexing:** A estruturação da interface deve considerar resoluções mobile como primeira classe. Alvos interativos devem possuir área física mínima de clique de 44x44 pixels.
* **Ciclo de Conversão:** O processo de checkout para o cliente final deve exigir um máximo de 3 minutos em fluxos felizes (Happy Path). O tempo de onboarding de um tenant, do cadastro à exibição de 5 produtos, não deve ultrapassar 10 minutos.

---

## 2.3 Matriz de Rastreabilidade

| Referência de Requisito | Caso de Uso Vinculado | Domínio Lógico (Módulo) | Teste Funcional Correspondente |
| --- | --- | --- | --- |
| RF01 | UC01, UC02 | Módulo de Autenticação | TC01, TC02 |
| RF02 | UC01, UC02 | Módulo de Autenticação | TC03, TC04 |
| RF03 | UC05 | Módulo de Tenants | TC05 |
| RF04 | UC05 | Módulo de Catálogo | TC06 |
| RF05 | UC03, UC04 | Módulo de Descoberta | TC07 |
| RF06 | UC04 | Módulo de Transação | TC08 |
| RF07 | UC04 | Módulo Operacional | TC09, TC10 |
| RF08 | UC06 | Módulo Operacional | TC11 |
| RNF01 | N/A | Camada de Infraestrutura | TC12 (Teste de Carga) |
| RNF02 | N/A | Middleware/Security | TC13 (Análise de Vulnerabilidade) |
| RNF03 | N/A | Camada de Infraestrutura | TC14 (Simulação Failover) |
